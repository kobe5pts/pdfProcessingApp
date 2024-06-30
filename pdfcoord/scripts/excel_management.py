import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side
import json
import re
import sys

column_mapping = {
    "Id Number": "A",
    "RFID": "B",
    "Item Category": "C",
    "Item Description": "D",
    "Model": "E",
    "SWL Value": "F",
    "SWL Unit": "G",
    "SWL Note": "H",
    "Manufacturer": "I",
    "Certificate No": "J",
    "Location": "K",
    "Detailed Location ": "L",
    "Previous Inspection": "M",
    "Next Inspection Due Date": "N",
    "Fit For Purpose Y/N": "O",
    "Status" : "P",
    "Provider Identification": "Q",
    "Errors": "R"
}


def create_excel(extracted_data: dict, filename: str, client: str, page_errors: dict):
        
    # try:
        print("<--------------Creating new excel------------------>")
        workbook = openpyxl.Workbook()  # Create a new Workbook

        # Create a sheet for extracted data
        sheet_data = workbook.active
        sheet_data.title = "Extraction Data"  # Set sheet name

        sheet_data['A1'] = "Rig-Ware import v2"
        sheet_data['B1'] = client
        sheet_data['C1'] = "CreateLocations=No"

        # Write column headers for extracted data sheet
        for header, column in column_mapping.items():
            cell = sheet_data[column + '2']
            cell.value = header
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center', vertical='center')  # Center align the text
            cell.border = Border(bottom=Side(border_style='thin'))  # Add a thin border at the bottom

            # Adjust column width to fit the header text
            column_width = max(len(header), 10)  # Set a minimum width of 10 characters
            sheet_data.column_dimensions[column].width = column_width
        
        
        nameList = list(extracted_data.keys())  
        # print(nameList)

        row_idx = 3

        for name in nameList:
            if name == "SWL":
                    swlVlaue = extracted_data.get(name)
                    
                    swlProcess(sheet_data, swlVlaue)
            else:
                column_name = column_mapping.get(name)  
                if column_name:
                    row_idx = 3
                    
                    for val in extracted_data.get(name, []):
                        if isinstance(val, str):  
                            sheet_data.cell(row=row_idx, column=ord(column_name) - 64, value=val)
                            row_idx += 1  


        # Create a sheet for errors
        sheet_errors = workbook.create_sheet(title="Errors")  # Create a new worksheet
        sheet_errors.append(["Page No", "Error"])  # Write column headers

        # Write errors to the worksheet
        for key, value in page_errors.items():
            sheet_errors.append([key, value])  # Write key-value pairs as rows

        try:
            workbook.save(filename)  # Save the workbook with the provided filename
            workbook.close()
            print("<-------------- Excel created successfully ------------------>")
        except Exception as e:
            print(f"An error occurred in excel creation: {e}")

def swlProcess(sheet_data, swlValue):
    
    valPattern = r'\d+(?:\.\d+)?'   # Pattern to extract numeric values
    unitPattern = r'[a-zA-Z]+'      # Pattern to extract alphabetic strings (units)
    notePattern = r'[\s\n]+(\S.*)'  # Pattern to extract notes following whitespace or newline

    # idx = 3     # Start inserting at row 3 in the Excel sheet
    # for val in swlValue:
    #     if isinstance(val, str):
    #         swlVal = re.findall(valPattern, val)[0]
    #         print(swlVal)
    #         sheet_data.cell(row=idx, column=ord("F") - 64, value=swlVal)
            
    #         swlUnit = re.findall(unitPattern, val)[0]
    #         print(swlUnit)
    #         sheet_data.cell(row=idx, column=ord("G") - 64, value=swlUnit)
            
    #         swlNote = re.findall(notePattern, val)
    #         if(len(swlNote) > 0):
    #             swlNote = swlNote[0]
    #             sheet_data.cell(row=idx, column=ord("H") - 64, value=swlNote)
    #         print(swlNote)
            
    #         idx += 1
    
    idx = 3  # Start inserting at row 3 in the Excel sheet

    for val in swlValue:
        if isinstance(val, str):
            swlVal_matches = re.findall(valPattern, val)
            swlUnit_matches = re.findall(unitPattern, val)
            swlNote_matches = re.findall(notePattern, val)

            # Check if matches found for value, unit, and note; handle cases where matches are not found
            swlVal = swlVal_matches[0] if swlVal_matches else "N/A"
            swlUnit = swlUnit_matches[0] if swlUnit_matches else "N/A"
            swlNote = swlNote_matches[0] if swlNote_matches else "No additional notes"

            # Print values for debugging
            print(f"Value: {swlVal}, Unit: {swlUnit}, Note: {swlNote}")

            # Assign values to cells in Excel
            sheet_data.cell(row=idx, column=ord("F") - 64, value=swlVal)
            sheet_data.cell(row=idx, column=ord("G") - 64, value=swlUnit)
            sheet_data.cell(row=idx, column=ord("H") - 64, value=swlNote)

            idx += 1  # Move to the next row for the next entry    


# def jsonProcess():

#     with open('genericSearch_results.json', 'r') as file:
#         data = json.load(file)
    
#     return data


# if __name__ == "__main__":
#     data = jsonProcess()
#     create_excel(data, "output.xlsx", "Client Name", {"Page1": "Error1", "Page2": "Error2"})

# def load_data(json_path):
#     with open(json_path, 'r', encoding='utf-8') as file:
#         return json.load(file)

# if __name__ == "__main__":
#     if len(sys.argv) != 5:
#         print("Usage: python excel_management.py <input JSON file> <output Excel file> <Client Name> <Error JSON file>")
#         sys.exit(1)

#     data = load_data(sys.argv[1])
#     page_errors = load_data(sys.argv[4])
#     create_excel(data, sys.argv[2], sys.argv[3], page_errors)
import os
def load_data(input_data):
    try:
        # First, try assuming input_data is a path to a JSON file
        if os.path.exists(input_data) and os.path.isfile(input_data):
            with open(input_data, 'r', encoding='utf-8') as file:
                return json.load(file)
        else:
            # If the input is not a valid file path, treat it as a JSON string
            return json.loads(input_data)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return {}
    except Exception as e:
        print(f"Error loading data: {e}")
        return {}

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python excel_management.py <input JSON file> <output Excel file> <Client Name> <Error JSON file>")
        sys.exit(1)

    data = load_data(sys.argv[1])
    page_errors = load_data(sys.argv[4])
    create_excel(data, sys.argv[2], sys.argv[3], page_errors)