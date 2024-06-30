
from celery import shared_task
import subprocess
from django.conf import settings
from .models import PDFDocument
import os

@shared_task
def process_pdf(pdf_id, pdf_path):
    try:
        document = PDFDocument.objects.get(pk=pdf_id)
        print("PDF path retrieved from database:", pdf_path)

        final_coords_path = os.path.join(settings.MEDIA_ROOT, 'transferred', 'final_coords.json')
        generic_output_json = os.path.join(settings.MEDIA_ROOT, 'outputs', 'genericSearch_results.json')
        cert_no_output_json = os.path.join(settings.MEDIA_ROOT, 'outputs', 'certNo_results.json')
        pdfPages_savedCert = os.path.join(settings.MEDIA_ROOT, 'splitPDFs')

        os.makedirs(os.path.join(settings.MEDIA_ROOT, 'outputs'), exist_ok=True)
        os.makedirs(os.path.join(settings.MEDIA_ROOT, 'splitPDFs'), exist_ok=True)

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
        scripts = [
            ('genericPDF_extract.py', [pdf_path, final_coords_path, generic_output_json]),
            ('extract_certNo.py', [generic_output_json, cert_no_output_json]),
            ('pdf_splitting.py', [pdf_path, cert_no_output_json, pdfPages_savedCert]),
            ('excel_management.py', [generic_output_json, 'output.xlsx', 'Client Name', '{"Page1": "Error1", "Page2": "Error2"}'])
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

    except subprocess.CalledProcessError as e:
        print(f"Subprocess failed with return code {e.returncode}")
        print(f"Error Output: {e.stderr}")
        document.status = 'Failed'
    except Exception as e:
        print(f"Error processing PDF {pdf_id}: {e}")
        document.status = 'Error'
    finally:
        document.save()
