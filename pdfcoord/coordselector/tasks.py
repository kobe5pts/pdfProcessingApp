
# from celery import shared_task
# import subprocess
# from django.conf import settings
# from .models import PDFDocument
# import os
# import boto3
# from botocore.exceptions import NoCredentialsError
# from .custom_storages import UploadsStorage, JSONStorage, OutputsStorage
# import io
# import zipfile
# from .utils import get_file_from_s3, save_file_to_s3

# # Define the locations as in settings
# UPLOADS_LOCATION = getattr(settings, 'UPLOADS_LOCATION', 'uploads')
# JSON_LOCATION = getattr(settings, 'JSON_LOCATION', 'json')
# OUTPUTS_LOCATION = getattr(settings, 'OUTPUTS_LOCATION', 'outputs')

# s3_client = boto3.client('s3')

# def download_from_s3(s3_key, local_path, as_text=False):
#     try:
#         print(f"Downloading file key: {s3_key}")
#         content = get_file_from_s3(settings.AWS_STORAGE_BUCKET_NAME, s3_key, as_text=as_text)
#         if content:
#             with open(local_path, 'wb' if not as_text else 'w') as f:
#                 if as_text:
#                     f.write(content)
#                 else:
#                     f.write(content)
#             print(f"Download Successful: {s3_key}")
#             return True
#         else:
#             print(f"Failed to retrieve content from S3: {s3_key}")
#             return False
#     except Exception as e:
#         print(f"Error downloading {s3_key} from S3: {e}")
#         return False
    
# def upload_to_s3(local_file, s3_file):
#     try:
#         s3_client.upload_file(local_file, settings.AWS_STORAGE_BUCKET_NAME, s3_file)
#         print(f"Upload Successful: {s3_file}")
#         return True
#     except FileNotFoundError:
#         print("The file was not found")
#         return False
#     except NoCredentialsError:
#         print("Credentials not available")
#         return False

# @shared_task
# def process_pdf(pdf_id, pdf_s3_key):
#     try:
#         print(f"Processing PDF with ID: {pdf_id}")
#         document = PDFDocument.objects.get(pk=pdf_id)
#         print("PDF path retrieved from database:", pdf_s3_key)

#         # Local paths for processing
#         local_pdf_path = '/tmp/pdf_file.pdf'
#         final_coords_path = '/tmp/final_coords.json'
#         generic_output_json = '/tmp/genericSearch_results.json'
#         cert_no_output_json = '/tmp/certNo_results.json'
#         pdfPages_savedCert = '/tmp/splitPDFs'
#         output_xlsx_path = '/tmp/output.xlsx'
#         zip_output_path = '/tmp/splitPDFs.zip'

#         os.makedirs('/tmp/outputs', exist_ok=True)
#         os.makedirs('/tmp/splitPDFs', exist_ok=True)

#         # Download necessary files from S3
#         if not download_from_s3(pdf_s3_key, local_pdf_path, as_text=False):
#             print("Failed to download the PDF file from S3.")
#             document.status = 'Error'
#             document.save()
#             return

#         final_coords_s3_key = f'{JSON_LOCATION}/final_coords.json'
#         if not download_from_s3(final_coords_s3_key, final_coords_path, as_text=True):
#             print(f"Failed to download {final_coords_s3_key} from S3.")
#             document.status = 'Error'
#             document.save()
#             return

#         # Paths
#         python_exe = os.path.join(settings.BASE_DIR, 'env', 'Scripts', 'python.exe')
#         script_dir = os.path.join(settings.BASE_DIR, 'scripts')

#         # Confirm paths before execution
#         print("Python executable:", python_exe)
#         print("Script directory:", script_dir)

#         if not os.path.exists(python_exe):
#             raise FileNotFoundError(f"The Python executable does not exist at {python_exe}")
#         if not os.path.isdir(script_dir):
#             raise FileNotFoundError(f"The script directory does not exist at {script_dir}")

#         # Running the Python scripts in sequence
#         scripts = [
#             ('genericPDF_extract.py', [local_pdf_path, final_coords_path, generic_output_json]),
#             ('extract_certNo.py', [generic_output_json, cert_no_output_json]),
#             ('pdf_splitting.py', [local_pdf_path, cert_no_output_json, pdfPages_savedCert]),
#             ('excel_management.py', [generic_output_json, output_xlsx_path, 'Client Name', "Error Page"])
#         ]

#         for script_name, args in scripts:
#             script_path = os.path.join(script_dir, script_name)
#             if not os.path.exists(script_path):
#                 raise FileNotFoundError(f"Script file does not exist at {script_path}")
            
#             print(f"Executing {script_name}...")
#             result = subprocess.run(
#                 [python_exe, script_path] + args, 
#                 text=True, capture_output=True, check=True
#             )
#             if result.stdout:
#                 print(f"Output of {script_name}: {result.stdout}")
#             if result.stderr:
#                 print(f"Error of {script_name}: {result.stderr}")

#         # Create a ZIP archive of the split PDF files
#         with zipfile.ZipFile(zip_output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
#             for root, _, files in os.walk(pdfPages_savedCert):
#                 for file in files:
#                     local_file = os.path.join(root, file)
#                     zipf.write(local_file, arcname=file)

#         # Extract the base name of the PDF file to use as the folder name
#         pdf_base_name = os.path.splitext(os.path.basename(local_pdf_path))[0]

#         # Upload files to S3
#         upload_to_s3(final_coords_path, f'{JSON_LOCATION}/final_coords.json')
#         upload_to_s3(generic_output_json, f'{JSON_LOCATION}/genericSearch_results.json')
#         upload_to_s3(cert_no_output_json, f'{JSON_LOCATION}/certNo_results.json')
#         upload_to_s3(zip_output_path, f'{OUTPUTS_LOCATION}/{pdf_base_name}/splitPDFs.zip')
#         upload_to_s3(output_xlsx_path, f'{OUTPUTS_LOCATION}/output.xlsx')

#     except subprocess.CalledProcessError as e:
#         print(f"Subprocess failed with return code {e.returncode}")
#         print(f"Error Output: {e.stderr}")
#         document.status = 'Failed'
#     except Exception as e:
#         print(f"Error processing PDF {pdf_id}: {e}")
#         document.status = 'Error'
#     finally:
#         document.save()


from celery import shared_task
import subprocess
from django.conf import settings
from .models import PDFDocument
import os
import boto3
from botocore.exceptions import NoCredentialsError
from .custom_storages import UploadsStorage, JSONStorage, OutputsStorage
import io
import fitz
import zipfile
from PIL import Image
from .utils import get_file_from_s3, save_file_to_s3

# Define the locations as in settings
UPLOADS_LOCATION = getattr(settings, 'UPLOADS_LOCATION', 'uploads')
JSON_LOCATION = getattr(settings, 'JSON_LOCATION', 'json')
OUTPUTS_LOCATION = getattr(settings, 'OUTPUTS_LOCATION', 'outputs')

s3_client = boto3.client('s3')

def download_from_s3_to_memory(s3_key):
    try:
        print(f"Downloading file key: {s3_key}")
        content = get_file_from_s3(settings.AWS_STORAGE_BUCKET_NAME, s3_key)
        if content:
            print(f"Download Successful: {s3_key}")
            return io.BytesIO(content)
        else:
            print(f"Failed to retrieve content from S3: {s3_key}")
            return None
    except Exception as e:
        print(f"Error downloading {s3_key} from S3: {e}")
        return None
    
def upload_from_memory_to_s3(memory_file, s3_key):
    try:
        memory_file.seek(0)
        s3_client.upload_fileobj(memory_file, settings.AWS_STORAGE_BUCKET_NAME, s3_key)
        print(f"Upload Successful: {s3_key}")
        return True
    except FileNotFoundError:
        print("The file was not found")
        return False
    except NoCredentialsError:
        print("Credentials not available")
        return False

def upload_to_s3(local_file, s3_key):
    try:
        s3_client.upload_file(local_file, settings.AWS_STORAGE_BUCKET_NAME, s3_key)
        print(f"Upload Successful: {s3_key}")
        return True
    except FileNotFoundError:
        print("The file was not found")
        return False
    except NoCredentialsError:
        print("Credentials not available")
        return False

@shared_task
def process_pdf(pdf_id, pdf_s3_key):
    try:
        print(f"Processing PDF with ID: {pdf_id}")
        document = PDFDocument.objects.get(pk=pdf_id)
        print("PDF path retrieved from database:", pdf_s3_key)

        # Download necessary files from S3
        pdf_file_memory = download_from_s3_to_memory(pdf_s3_key)
        if not pdf_file_memory:
            print("Failed to download the PDF file from S3.")
            document.status = 'Error'
            document.save()
            return

        final_coords_s3_key = f'{JSON_LOCATION}/final_coords.json'
        final_coords_memory = download_from_s3_to_memory(final_coords_s3_key)
        if not final_coords_memory:
            print(f"Failed to download {final_coords_s3_key} from S3.")
            document.status = 'Error'
            document.save()
            return

        # Local paths for processing
        local_pdf_path = '/tmp/pdf_file.pdf'
        final_coords_path = '/tmp/final_coords.json'
        generic_output_json = '/tmp/genericSearch_results.json'
        cert_no_output_json = '/tmp/certNo_results.json'
        pdfPages_savedCert = '/tmp/splitPDFs'
        output_xlsx_path = '/tmp/output.xlsx'
        zip_output_path = '/tmp/splitPDFs.zip'

        os.makedirs('/tmp/outputs', exist_ok=True)
        os.makedirs('/tmp/splitPDFs', exist_ok=True)

        # Save the final_coords.json locally for the scripts to access
        with open(final_coords_path, 'w') as f:
            f.write(final_coords_memory.read().decode('utf-8'))
            
        # Save the PDF file locally for the scripts to access
        with open(local_pdf_path, 'wb') as f:
            f.write(pdf_file_memory.read())    

        # Paths
        python_exe = os.path.join(settings.BASE_DIR, 'env', 'Scripts', 'python.exe')
        script_dir = os.path.join(settings.BASE_DIR, 'scripts')

        # Confirm paths before execution
        print("Python executable:", python_exe)
        print("Script directory:", script_dir)

        if not os.path.exists(python_exe):
            raise FileNotFoundError(f"The Python executable does not exist at {python_exe}")
        if not os.path.isdir(script_dir):
            raise FileNotFoundError(f"The script directory does not exist at {script_dir}")

        # Running the Python scripts in sequence
        # scripts = [
        #     ('genericPDF_extract.py', [pdf_file_memory, final_coords_path, generic_output_json]),
        #     ('extract_certNo.py', [generic_output_json, cert_no_output_json]),
        #     ('pdf_splitting.py', [pdf_file_memory, cert_no_output_json, pdfPages_savedCert]),
        #     ('excel_management.py', [generic_output_json, output_xlsx_path, 'Client Name', "Error Page"])
        # ]
        scripts = [
            ('genericPDF_extract.py', [local_pdf_path, final_coords_path, generic_output_json]),
            ('extract_certNo.py', [generic_output_json, cert_no_output_json]),
            ('pdf_splitting.py', [local_pdf_path, cert_no_output_json, pdfPages_savedCert]),
            ('excel_management.py', [generic_output_json, output_xlsx_path, 'Client Name', "Error Page"])
        ]

        for script_name, args in scripts:
            script_path = os.path.join(script_dir, script_name)
            if not os.path.exists(script_path):
                raise FileNotFoundError(f"Script file does not exist at {script_path}")
            
            print(f"Executing {script_name}...")
            result = subprocess.run(
                [python_exe, script_path] + args, 
                text=True, capture_output=True, check=True
            )
            if result.stdout:
                print(f"Output of {script_name}: {result.stdout}")
            if result.stderr:
                print(f"Error of {script_name}: {result.stderr}")

        # Create a ZIP archive of the split PDF files
        with zipfile.ZipFile(zip_output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(pdfPages_savedCert):
                for file in files:
                    local_file = os.path.join(root, file)
                    zipf.write(local_file, arcname=file)

        # Extract the base name of the PDF file to use as the folder name
        pdf_base_name = os.path.splitext(os.path.basename(pdf_s3_key))[0]

        # Upload files to S3
        upload_to_s3(final_coords_path, f'{JSON_LOCATION}/final_coords.json')
        upload_to_s3(generic_output_json, f'{JSON_LOCATION}/genericSearch_results.json')
        upload_to_s3(cert_no_output_json, f'{JSON_LOCATION}/certNo_results.json')
        upload_to_s3(zip_output_path, f'{OUTPUTS_LOCATION}/{pdf_base_name}/splitPDFs.zip')
        upload_to_s3(output_xlsx_path, f'{OUTPUTS_LOCATION}/output.xlsx')

    except subprocess.CalledProcessError as e:
        print(f"Subprocess failed with return code {e.returncode}")
        print(f"Error Output: {e.stderr}")
        document.status = 'Failed'
    except Exception as e:
        print(f"Error processing PDF {pdf_id}: {e}")
        document.status = 'Error'
    finally:
        document.save()

@shared_task
def render_pdf_pages_task(pdf_s3_key):
    try:
        print(f"Rendering PDF pages for key: {pdf_s3_key}")
        file_content = get_file_from_s3(settings.AWS_STORAGE_BUCKET_NAME, pdf_s3_key)
        if not file_content:
            print(f"Failed to download {pdf_s3_key} from S3.")
            return 0

        doc = fitz.open(stream=file_content, filetype="pdf")
        img_dir = f'{UPLOADS_LOCATION}/pdf_images'
        total_pages = len(doc)

        os.makedirs(img_dir, exist_ok=True)
        # Clear the existing images in the directory
        for filename in os.listdir(img_dir):
            file_path = os.path.join(img_dir, filename)
            if os.path.isfile(file_path):
                os.unlink(file_path)

        for page_number in range(total_pages):
            img_key = f'{img_dir}/page_{page_number}.png'
            page = doc.load_page(page_number)
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            img_buffer = io.BytesIO()
            img.save(img_buffer, format="PNG")
            img_buffer.seek(0)
            save_file_to_s3(settings.AWS_STORAGE_BUCKET_NAME, img_key, img_buffer.getvalue())

        print(f"Rendered and uploaded {total_pages} pages for {pdf_s3_key}")
        return total_pages

    except Exception as e:
        print(f"Error rendering PDF pages for {pdf_s3_key}: {e}")
        return 0

@shared_task
def render_pdf_to_images(pdf_s3_key, pdf_id):
    try:
        print(f"Rendering PDF pages for key: {pdf_s3_key}")
        file_content = get_file_from_s3(settings.AWS_STORAGE_BUCKET_NAME, pdf_s3_key)
        if not file_content:
            print(f"Failed to download {pdf_s3_key} from S3.")
            return

        doc = fitz.open(stream=file_content, filetype="pdf")
        img_dir = f'{UPLOADS_LOCATION}/pdf_images/{pdf_id}'
        total_pages = len(doc)

        os.makedirs(img_dir, exist_ok=True)

        # Clear the existing images in the directory
        for filename in os.listdir(img_dir):
            file_path = os.path.join(img_dir, filename)
            if os.path.isfile(file_path):
                os.unlink(file_path)

        img_paths = []

        for page_number in range(total_pages):
            img_key = f'{img_dir}/page_{page_number}.png'
            page = doc.load_page(page_number)
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            img_buffer = io.BytesIO()
            img.save(img_buffer, format="PNG")
            img_buffer.seek(0)
            save_file_to_s3(settings.AWS_STORAGE_BUCKET_NAME, img_key, img_buffer.getvalue())

            img_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{img_key}"
            img_paths.append(img_url)

        print(f"Rendered and uploaded {total_pages} pages for {pdf_s3_key}")

    except Exception as e:
        print(f"Error rendering PDF pages for {pdf_s3_key}: {e}")
        return 0    