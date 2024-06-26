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

def home(request):
    return render(request, 'coordselector/home.html')


def upload_pdf(request):
    saved_keywords = []

    # Load saved keywords from JSON file
    saved_keywords_path = os.path.join(settings.MEDIA_ROOT, 'saved_keywords.json')
    if os.path.exists(saved_keywords_path):
        with open(saved_keywords_path, 'r') as f:
            saved_keywords = json.load(f)

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
                    with open(os.path.join(settings.MEDIA_ROOT, 'saved_keywords.json'), 'w') as f:
                        json.dump(saved_keywords, f, indent=4)
                selected_keyword = new_keyword #
                
            # Store the selected keyword in the session
            request.session['selected_keyword'] = selected_keyword

            # Handle processing uploaded PDF
            if pdf_file and selected_keyword and action == 'upload':
                # Save the uploaded PDF in the pdfs directory
                pdfs_dir = os.path.join(settings.MEDIA_ROOT, 'pdfs')
                os.makedirs(pdfs_dir, exist_ok=True)
                pdf_save_path = os.path.join(pdfs_dir, pdf_file.name)

                # Save the PDF in chunks to handle large files
                with open(pdf_save_path, 'wb') as pdf_out:
                    for chunk in pdf_file.chunks():
                        pdf_out.write(chunk)
                
                # Create and save PDFDocument
                document = PDFDocument(file=pdf_file)
                document.save()
                
                return redirect('select_coords', pdf_id=document.id)  # Adjust as per your application

            # Handle processing existing keyword
            elif action == 'process' and selected_keyword:
                keyword_coords_dir = os.path.join(settings.MEDIA_ROOT, 'keyword_coords')
                keyword_final_coords_path = os.path.join(keyword_coords_dir, f'{selected_keyword}_final_coords.json')

                if os.path.exists(keyword_final_coords_path):
                    with open(keyword_final_coords_path, 'r') as f:
                        final_coords = json.load(f)

                    transfer_dir = os.path.join(settings.MEDIA_ROOT, 'transferred')
                    os.makedirs(transfer_dir, exist_ok=True)
                    
                    # Clear out the transferred directory before processing
                    if os.path.exists(transfer_dir):
                        for filename in os.listdir(transfer_dir):
                            file_path = os.path.join(transfer_dir, filename)
                            if os.path.isfile(file_path):
                                os.unlink(file_path)                    
                    
                    transfer_path = os.path.join(transfer_dir, f'{selected_keyword}_final_coords.json')

                    with open(transfer_path, 'w') as f:
                        json.dump(final_coords, f, indent=4)

                    # Save the uploaded PDF
                    pdf_file = request.FILES.get('pdf_file')
                    if pdf_file:
                        pdfs_dir = os.path.join(settings.MEDIA_ROOT, 'pdfs')
                        os.makedirs(pdfs_dir, exist_ok=True)
                        pdf_save_path = os.path.join(pdfs_dir, pdf_file.name)
                        with open(pdf_save_path, 'wb') as pdf_out:
                            for chunk in pdf_file.chunks():
                                pdf_out.write(chunk)

                    # Additional processing logic if needed
                else:
                    error_message = f'No final_coords.json found for the keyword "{selected_keyword}".'
                    return render(request, 'coordselector/upload_pdf.html', {'form': form, 'saved_keywords': saved_keywords, 'error_message': error_message})

        else:
            error_message = 'Form is not valid.'
            return render(request, 'coordselector/upload_pdf.html', {'form': form, 'saved_keywords': saved_keywords, 'error_message': error_message})

    else:
        form = UploadPDFForm()
    return render(request, 'coordselector/upload_pdf.html', {'form': form, 'saved_keywords': saved_keywords})

    
def render_pdf_to_images(pdf_path):
    cache_key = f'pdf_images_{os.path.basename(pdf_path)}'
    doc = fitz.open(pdf_path)
    img_dir = os.path.join(settings.MEDIA_ROOT, 'pdf_images')

    if os.path.exists(img_dir):
        shutil.rmtree(img_dir)
    os.makedirs(img_dir, exist_ok=True)

    img_paths = []

    try:
        for page_number in range(len(doc)):
            page = doc.load_page(page_number)
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            img_path = os.path.join(img_dir, f'page_{page_number}.png')
            img.save(img_path)
            img_rel_path = os.path.relpath(img_path, settings.MEDIA_ROOT)
            img_url = os.path.join(settings.MEDIA_URL, img_rel_path)
            img_paths.append(img_url)
    except Exception as e:
        print(f"Error rendering PDF: {e}")

    cache.set(cache_key, img_paths, timeout=3600)
    
    return img_paths


def select_coords(request, pdf_id, page_number=0):
    document = get_object_or_404(PDFDocument, pk=pdf_id)
    pdf_path = document.file.path
    doc = fitz.open(pdf_path)
    total_pages = len(doc)

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

        json_file_path = os.path.join(settings.MEDIA_ROOT, f'pdf_coords_{pdf_id}.json')

        if os.path.exists(json_file_path):
            with open(json_file_path, 'r') as f:
                coords_per_page = json.load(f)

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

        with open(json_file_path, 'w') as f:
            json.dump(coords_per_page, f, indent=4)

        return JsonResponse({'status': 'success'})

    img_paths = render_pdf_to_images(pdf_path)
    img_path = os.path.relpath(img_paths[page_number], settings.MEDIA_ROOT)
    img_url = f"{settings.MEDIA_URL}{img_path}"

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
        json_file_path = os.path.join(settings.MEDIA_ROOT, f'pdf_coords_{pdf_id}.json')
        final_json_file_path = os.path.join(settings.MEDIA_ROOT, 'final_coords.json')

        if not os.path.exists(final_json_file_path):
            with open(final_json_file_path, 'w') as f:
                json.dump({}, f)  # Initialize with an empty dictionary

        if os.path.exists(json_file_path):
            with open(json_file_path, 'r') as f:
                coords_per_page = json.load(f)

            with open(final_json_file_path, 'w') as f:
                json.dump(coords_per_page, f, indent=4)

            # Move final_json_file_path to the 'transferred' directory
            transfer_dir = os.path.join(settings.MEDIA_ROOT, 'transferred')
            if os.path.exists(transfer_dir):
                for filename in os.listdir(transfer_dir):
                    file_path = os.path.join(transfer_dir, filename)
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
            else:
                os.makedirs(transfer_dir, exist_ok=True)

            transfer_path = os.path.join(transfer_dir, 'final_coords.json')

            with open(transfer_path, 'w') as f:
                json.dump(coords_per_page, f, indent=4)

            # Handle keyword-specific final_coords.json
            keyword_coords_dir = os.path.join(settings.MEDIA_ROOT, 'keyword_coords')
            os.makedirs(keyword_coords_dir, exist_ok=True)

            # Retrieve the selected keyword from the session
            selected_keyword = request.session.get('selected_keyword')
            if selected_keyword:
                keyword_final_coords_path = os.path.join(keyword_coords_dir, f'{selected_keyword}_final_coords.json')

                generic_final_coords_path = os.path.join(settings.MEDIA_ROOT, 'final_coords.json')
                if os.path.exists(generic_final_coords_path):
                    with open(generic_final_coords_path, 'r') as f:
                        final_coords = json.load(f)
                    with open(keyword_final_coords_path, 'w') as f:
                        json.dump(final_coords, f, indent=4)

            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error', 'message': 'No coordinates found'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
