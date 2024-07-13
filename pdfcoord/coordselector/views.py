import io
import json
import os
import shutil
from PIL import Image
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import PDFDocument
from django.conf import settings
from django.core.cache import cache
import fitz  # PyMuPDF
from .forms import UploadPDFForm
from .tasks import process_pdf, render_pdf_to_images  # Import Celery
from .custom_storages import UploadsStorage, JSONStorage, OutputsStorage
import boto3
from .utils import get_file_from_s3, save_file_to_s3, check_file_exists_in_s3

# Ensure to import UPLOADS_LOCATION from settings
UPLOADS_LOCATION = getattr(settings, 'UPLOADS_LOCATION', 'uploads')
JSON_LOCATION = getattr(settings, 'JSON_LOCATION', 'json')
OUTPUTS_LOCATION = getattr(settings, 'OUTPUTS_LOCATION', 'outputs')

s3_client = boto3.client('s3')

uploads_storage = UploadsStorage()
json_storage = JSONStorage()
outputs_storage = OutputsStorage()


def upload_pdf_to_s3(file, bucket_name, s3_key):
    try:
        file_size = file.size
        part_size = 5 * 1024 * 1024  # 5 MB
        if file_size < part_size:
            # If file size is less than 5 MB, upload it directly
            s3_client.upload_fileobj(file, bucket_name, s3_key)
            print(f"Uploaded {s3_key} directly to S3.")
        else:
            # Multipart upload
            upload_response = s3_client.create_multipart_upload(Bucket=bucket_name, Key=s3_key)
            upload_id = upload_response['UploadId']

            parts = []
            part_number = 1
            try:
                for chunk in file.chunks():
                    part_response = s3_client.upload_part(
                        Bucket=bucket_name,
                        Key=s3_key,
                        PartNumber=part_number,
                        UploadId=upload_id,
                        Body=chunk
                    )
                    parts.append({"PartNumber": part_number, "ETag": part_response['ETag']})
                    part_number += 1

                s3_client.complete_multipart_upload(
                    Bucket=bucket_name,
                    Key=s3_key,
                    UploadId=upload_id,
                    MultipartUpload={"Parts": parts}
                )
                print(f"Uploaded file key: {s3_key} to bucket: {bucket_name}")

            except Exception as e:
                s3_client.abort_multipart_upload(Bucket=bucket_name, Key=s3_key, UploadId=upload_id)
                print(f"Upload failed: {e}")
                return False
        return True
    except Exception as e:
        print(f"Upload to S3 failed: {e}")
        return False

def home(request):
    return render(request, 'coordselector/home.html')

def upload_pdf(request):
    saved_keywords = []

    # Load saved keywords from JSON file in S3
    saved_keywords_key = f'{JSON_LOCATION}/saved_keywords.json'
    saved_keywords_content = get_file_from_s3(settings.AWS_STORAGE_BUCKET_NAME, saved_keywords_key, as_text=True)
    if saved_keywords_content:
        saved_keywords = json.loads(saved_keywords_content)

    if request.method == 'POST':
        form = UploadPDFForm(request.POST, request.FILES)
        if form.is_valid():
            pdf_file = request.FILES.get('pdf_file')
            new_keyword = form.cleaned_data.get('new_keyword')
            selected_keyword = form.cleaned_data.get('saved_keyword')
            action = form.cleaned_data.get('action')

            # Handle saving new keyword if provided
            if new_keyword:
                if new_keyword not in saved_keywords:
                    saved_keywords.append(new_keyword)
                    saved_keywords_str = json.dumps(saved_keywords, indent=4)
                    save_file_to_s3(settings.AWS_STORAGE_BUCKET_NAME, saved_keywords_key, saved_keywords_str.encode('utf-8'))

                selected_keyword = new_keyword

            # Store the selected keyword in the session
            request.session['selected_keyword'] = selected_keyword

            # Handle processing uploaded PDF
            if pdf_file and selected_keyword and action == 'upload':
                # Save the uploaded PDF to S3
                pdf_s3_key = f'{UPLOADS_LOCATION}/{pdf_file.name}'
                if upload_pdf_to_s3(pdf_file, settings.AWS_STORAGE_BUCKET_NAME, pdf_s3_key):
                    # Create and save PDFDocument
                    document = PDFDocument(file=pdf_s3_key)
                    document.save()
                    # pdf_id = document.id
                    # Render all PDF pages as images
                    render_pdf_to_images(pdf_s3_key)

                    return redirect('select_coords', pdf_id=document.id)  # Adjust as per your application
                else:
                    return JsonResponse({'status': 'error', 'message': 'Failed to upload file to S3.'})

            # Handle processing existing keyword
            elif pdf_file and action == 'process' and selected_keyword:
                keyword_final_coords_key = f'{JSON_LOCATION}/keyword_coords/{selected_keyword}_final_coords.json'
                
                if check_file_exists_in_s3(settings.AWS_STORAGE_BUCKET_NAME, keyword_final_coords_key):
                    final_coords_content = get_file_from_s3(settings.AWS_STORAGE_BUCKET_NAME, keyword_final_coords_key, as_text=True)
                    final_coords = json.loads(final_coords_content)

                    coords_per_page = save_file_to_s3(settings.AWS_STORAGE_BUCKET_NAME, f'{JSON_LOCATION}/final_coords.json', json.dumps(final_coords).encode('utf-8'))

                    # Move final_json_file_path to the 'transferred' directory
                    transfer_dir = f'{JSON_LOCATION}/transferred'
                    objects = s3_client.list_objects_v2(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Prefix=transfer_dir)
                    if 'Contents' in objects:
                        for obj in objects['Contents']:
                            s3_client.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=obj['Key'])

                    save_file_to_s3(settings.AWS_STORAGE_BUCKET_NAME, f'{transfer_dir}/final_coords.json', json.dumps(coords_per_page).encode('utf-8'))

                    # Save the uploaded PDF in the pdfs directory
                    pdf_s3_key = f'{UPLOADS_LOCATION}/{pdf_file.name}'
                    if upload_pdf_to_s3(pdf_file, settings.AWS_STORAGE_BUCKET_NAME, pdf_s3_key):
                        # Create and save PDFDocument
                        document = PDFDocument(file=pdf_s3_key)
                        document.save()
                        pdf_id = document.id

                        process_pdf(pdf_id, pdf_s3_key)

                        return render(request, 'coordselector/upload_pdf.html', {'form': form, 'saved_keywords': saved_keywords})

                    else:
                        return JsonResponse({'status': 'error', 'message': 'Failed to upload file to S3.'})
                else:
                    error_message = f'No final_coords.json found for the keyword "{selected_keyword}".'
                    return render(request, 'coordselector/upload_pdf.html', {'form': form, 'saved_keywords': saved_keywords, 'error_message': error_message})

        else:
            error_message = 'Form is not valid.'
            return render(request, 'coordselector/upload_pdf.html', {'form': form, 'saved_keywords': saved_keywords, 'error_message': error_message})

    else:
        form = UploadPDFForm()
    return render(request, 'coordselector/upload_pdf.html', {'form': form, 'saved_keywords': saved_keywords})

import hashlib

def render_pdf_to_images(pdf_key):
# def render_pdf_to_image(pdf_key, page_number):
    # Sanitize the cache key
    sanitized_pdf_key = hashlib.md5(pdf_key.encode('utf-8')).hexdigest()
    cache_key = f'pdf_images_{sanitized_pdf_key}'
    print(f'Downloading file key: {pdf_key}')  # Print the file key for debugging

    file_content = get_file_from_s3(settings.AWS_STORAGE_BUCKET_NAME, pdf_key)

    if not file_content:
        print(f"Failed to download {pdf_key} from S3.")
        return []
    #     return None

    # Open the PDF file from the downloaded content
    doc = fitz.open(stream=file_content, filetype="pdf")
    img_dir = f'{UPLOADS_LOCATION}/pdf_images'
    
    img_paths = []

    try:
        for page_number in range(len(doc)):
            img_key = f'{img_dir}/page_{page_number}.png'
            # if not check_file_exists_in_s3(settings.AWS_STORAGE_BUCKET_NAME, img_key):
            page = doc.load_page(page_number)
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            img_buffer = io.BytesIO()
            img.save(img_buffer, format="PNG")
            img_buffer.seek(0)
            save_file_to_s3(settings.AWS_STORAGE_BUCKET_NAME, img_key, img_buffer.getvalue())

            img_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{img_key}"
            img_paths.append(img_url)

    except Exception as e:
        print(f"Error rendering PDF: {e}")
        return []

    cache.set(cache_key, img_paths, timeout=3600)
    
    print(f'Rendered and uploaded {len(img_paths)} pages for {pdf_key}')
    return img_paths


def select_coords(request, pdf_id, page_number=0):
    document = get_object_or_404(PDFDocument, pk=pdf_id)
    pdf_key = document.file.name  # Get the key of the file in S3

    img_paths = render_pdf_to_images(pdf_key)
    total_pages = len(img_paths)
    # print(total_pages)
    print(f'Total pages: {total_pages}')
    print(f'Requested page number: {page_number}')


    if page_number < 0 or page_number >= total_pages:
        return JsonResponse({'status': 'error', 'message': 'Page number out of range.'})

    
    if request.method == "POST":
        data = json.loads(request.body.decode('utf-8'))
        coordinates = data.get('coordinates', [])
        start_page = data.get('start_page', 0)
        end_page = data.get('end_page', start_page)
        keyword = data.get('keyword', 'default_keyword')

        # Generate a unique key for the processedKeywords set
        key = f"{keyword}-{start_page}-{end_page}"

        # Check if this key has already been processed
        if request.session.get('processed_keywords', {}).get(key):
            return JsonResponse({'status': 'error', 'message': f'Coordinates for keyword "{keyword}" on pages {start_page}-{end_page} have already been processed.'})

        # Mark this key as processed in session to prevent duplicate submissions
        request.session.setdefault('processed_keywords', {})[key] = True

        coords_per_page = {}

        json_file_key = f'{JSON_LOCATION}/pdf_coords_{pdf_id}.json'

        json_content = get_file_from_s3(settings.AWS_STORAGE_BUCKET_NAME, json_file_key, as_text=True)
        if json_content:
            coords_per_page = json.loads(json_content)

        coords_per_page = {str(k): v for k, v in coords_per_page.items()}

        def coord_tuple(coord):
            return (coord['x0'], coord['y0'], coord['x1'], coord['y1'])

        for page in range(start_page, end_page + 1):
            page_key = str(page)
            if page_key not in coords_per_page:
                coords_per_page[page_key] = []

            # Check if there are any existing coordinates for this keyword on the page
            existing_coords = []
            for entry in coords_per_page[page_key]:
                if entry['keyword'] == keyword:
                    existing_coords.extend(coord_tuple(coord) for coord in entry['coordinates'])

            # Remove existing coordinates associated with the same keyword from new coordinates
            new_coords = [coord for coord in coordinates if coord_tuple(coord) not in existing_coords]

            if new_coords:
                coords_per_page[page_key].append({
                    "keyword": keyword,
                    "coordinates": new_coords
                })

        save_file_to_s3(settings.AWS_STORAGE_BUCKET_NAME, json_file_key, json.dumps(coords_per_page, indent=4).encode('utf-8'))

        return JsonResponse({'status': 'success'})
    
    if page_number < 0 or page_number >= len(img_paths):
        return JsonResponse({'status': 'error', 'message': 'Page number out of range.'})

    img_url = img_paths[page_number]

    previous_page = page_number - 1 if page_number > 0 else None
    next_page = page_number + 1 if page_number < total_pages - 1 else None

    context = {
        'img_url': img_url,
        'pdf_id': pdf_id,
        'current_page': page_number,
        'total_pages': total_pages,
        'previous_page': previous_page,
        'next_page': next_page,
        'csrf_token': request.META.get('CSRF_COOKIE')
    }
    return render(request, 'coordselector/select_coords.html', context)


def submit_coordinates(request, pdf_id):
    if request.method == "POST":
        document = PDFDocument.objects.get(pk=pdf_id)
        pdf_key = document.file.name 
        
        json_file_key = f'{JSON_LOCATION}/pdf_coords_{pdf_id}.json'
        final_json_file_key = f'{JSON_LOCATION}/final_coords.json'

        if not get_file_from_s3(settings.AWS_STORAGE_BUCKET_NAME, final_json_file_key):
            save_file_to_s3(settings.AWS_STORAGE_BUCKET_NAME, final_json_file_key, json.dumps({}).encode('utf-8'))

        json_content = get_file_from_s3(settings.AWS_STORAGE_BUCKET_NAME, json_file_key, as_text=True)
        if json_content:
            coords_per_page = json.loads(json_content)

            save_file_to_s3(settings.AWS_STORAGE_BUCKET_NAME, final_json_file_key, json.dumps(coords_per_page).encode('utf-8'))

            # Move final_json_file_path to the 'transferred' directory
            transfer_dir = f'{JSON_LOCATION}/transferred'
            objects = s3_client.list_objects_v2(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Prefix=transfer_dir)
            if 'Contents' in objects:
                for obj in objects['Contents']:
                    s3_client.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=obj['Key'])
            
            save_file_to_s3(settings.AWS_STORAGE_BUCKET_NAME, f'{transfer_dir}/final_coords.json', json.dumps(coords_per_page).encode('utf-8'))

            # Handle keyword-specific final_coords.json
            keyword_coords_dir = f'{JSON_LOCATION}/keyword_coords'
            selected_keyword = request.session.get('selected_keyword')
            if selected_keyword:
                keyword_final_coords_key = f'{keyword_coords_dir}/{selected_keyword}_final_coords.json'
                save_file_to_s3(settings.AWS_STORAGE_BUCKET_NAME, keyword_final_coords_key, json.dumps(coords_per_page).encode('utf-8'))

            process_pdf(pdf_id, pdf_key)

            return render(request, 'coordselector/upload_pdf.html')
        
        else:
            return JsonResponse({'status': 'error', 'message': 'No coordinates found'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

def delete_keyword(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            keyword = data.get('keyword')
            
            # Load existing keywords from the JSON file in S3
            saved_keywords_key = f'{JSON_LOCATION}/saved_keywords.json'
            saved_keywords_content = get_file_from_s3(settings.AWS_STORAGE_BUCKET_NAME, saved_keywords_key, as_text=True)
            if saved_keywords_content:
                saved_keywords = json.loads(saved_keywords_content)

                # Remove the keyword if it exists
                if keyword in saved_keywords:
                    saved_keywords.remove(keyword)
                    saved_keywords_str = json.dumps(saved_keywords, indent=4)
                    save_file_to_s3(settings.AWS_STORAGE_BUCKET_NAME, saved_keywords_key, saved_keywords_str.encode('utf-8'))

                    # Delete the corresponding JSON file in the keyword_coords directory
                    keyword_coords_key = f'{JSON_LOCATION}/keyword_coords/{keyword}_final_coords.json'
                    if check_file_exists_in_s3(settings.AWS_STORAGE_BUCKET_NAME, keyword_coords_key):
                        s3_client.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=keyword_coords_key)

                    return JsonResponse({'success': True})
                else:
                    return JsonResponse({'success': False, 'error': 'Keyword not found'})
            else:
                return JsonResponse({'success': False, 'error': 'Keywords file not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})


