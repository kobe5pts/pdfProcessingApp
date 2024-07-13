import sys
import json

def extract_certificate_no(data):
    """
    Extracts items for "Certificate No" from the provided data.

    Args:
    data (dict): The input JSON data.

    Returns:
    dict: Extracted data formatted as required.
    """
    extracted_data = {}
    certificate_no_key = "Certificate No"

    if certificate_no_key in data:
        certificate_list = data[certificate_no_key]
        filtered_items = [item for item in certificate_list if isinstance(item, str)]
        
        for index, certificate in enumerate(filtered_items, start=1):
            extracted_data[str(index)] = [certificate]
    
    return {"certificate no": extracted_data}

def save_results_to_file(results, output_file):
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(results, file, indent=4)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python extract_certNo.py <input JSON file> <output JSON file>")
        sys.exit(1)

    input_json_path = sys.argv[1]
    output_json_path = sys.argv[2]

    # Load data from JSON file
    with open(input_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Extract certificate numbers
    extracted_data = extract_certificate_no(data)
    
    # Save results to file
    save_results_to_file(extracted_data, output_json_path)
    print(f"Extracted certificate numbers saved to '{output_json_path}'")
