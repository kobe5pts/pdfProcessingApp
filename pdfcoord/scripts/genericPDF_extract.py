
import os
import json
import pdfplumber
import sys

def extract_text_from_coordinates(pdf_path, coordinates_dict):
    """
    Extracts text from specified areas on specific pages in a PDF.

    Args:
    pdf_path (str): Path to the PDF file.
    coordinates_dict (dict): Dictionary containing page numbers as keys and lists of dictionaries with coordinates and keywords.

    Returns:
    dict: Extracted text from each specified area on each page.
    """
    extracted_texts = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page_num_str, items in coordinates_dict.items():
            try:
                page_num = int(page_num_str)  # Convert page number to integer
            except ValueError:
                print(f"Invalid page number: {page_num_str}")
                continue

            for item in items:
                keyword = item["keyword"]
                for coord in item["coordinates"]:
                    x0, y0, x1, y1 = coord["x0"], coord["y0"], coord["x1"], coord["y1"]
                    
                    if 0 <= page_num < len(pdf.pages):
                        page = pdf.pages[page_num]
                        if (0 <= x0 < page.width and 0 <= y0 < page.height and
                            0 <= x1 <= page.width and 0 <= y1 <= page.height):
                            text = page.within_bbox((x0, y0, x1, y1)).extract_text()
                            if text:
                                extracted_texts.setdefault(keyword, []).append(text.strip())
                            else:
                                extracted_texts.setdefault(keyword, []).append(None)  # No text extracted
                        else:
                            extracted_texts.setdefault(keyword, []).append("Bounding box is outside the page bounds.")
                    else:
                        extracted_texts.setdefault(keyword, []).append("Page number out of range.")
    
    return extracted_texts

def save_results_to_file(results, output_file):
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(results, file, indent=4)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python genericPDF_extract.py <PDF path> <coordinates JSON path> <output JSON file>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    coordinates_json_path = sys.argv[2]
    output_json_file = sys.argv[3]

    # Load coordinates from JSON file
    with open(coordinates_json_path, 'r', encoding='utf-8') as f:
        coordinates_dict = json.load(f)

    extracted_texts = extract_text_from_coordinates(pdf_path, coordinates_dict)
    
    save_results_to_file(extracted_texts, output_json_file)
    print(f"Extracted texts saved to '{output_json_file}'")