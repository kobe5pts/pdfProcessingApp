
import sys
import os
import json
import re
from PyPDF2 import PdfReader, PdfWriter
# from pypdf import PdfReader, PdfWriter

def load_search_results(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        print(f"Failed to load search results from {json_path}: {e}")
        raise

def split_pdf_by_values(pdf_path, search_results, output_dir):
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        if not os.path.isfile(pdf_path):
            raise FileNotFoundError(f"The file {pdf_path} does not exist.")

        pdf_reader = PdfReader(pdf_path)
        total_pages = len(pdf_reader.pages)

        for key, page_dict in search_results.items():
            if key == "completed":
                continue
            for page_num_str, values in page_dict.items():
                try:
                    page_num = int(page_num_str) - 1  # Convert to zero-based index
                except ValueError:
                    print(f"Warning: Skipping invalid page number {page_num_str}.")
                    continue

                if 0 <= page_num < total_pages:
                    for value in values:
                        pdf_writer = PdfWriter()
                        pdf_writer.add_page(pdf_reader.pages[page_num])
                        
                        sanitized_value = re.sub(r'[^\w\-_\. ]', '_', value)  # Sanitize the value for file name
                        output_filename = os.path.join(output_dir, f'{sanitized_value}_Page_{page_num + 1}.pdf')
                        
                        with open(output_filename, 'wb') as out:
                            pdf_writer.write(out)
                else:
                    print(f"Warning: Page number {page_num + 1} out of range.")
    except Exception as e:
        print(f"Error during PDF splitting: {e}")
        raise

if __name__ == "__main__":
    try:
        if len(sys.argv) != 4:
            print("Usage: python pdf_splitting.py <PDF path> <JSON path> <output directory>")
            sys.exit(1)

        pdf_path = sys.argv[1]
        json_path = sys.argv[2]
        output_dir = sys.argv[3]

        search_results = load_search_results(json_path)
        split_pdf_by_values(pdf_path, search_results, output_dir)
        print(f"PDF splitting completed, files saved in '{output_dir}'")
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
