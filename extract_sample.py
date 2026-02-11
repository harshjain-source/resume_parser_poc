import fitz  # PyMuPDF
import json

# pdf_path = r"c:\Users\Dell\Desktop\resume_parser\BE (1).pdf"
# output_path = r"c:\Users\Dell\Desktop\resume_parser\extracted_sample.txt"

# try:
#     doc = fitz.open(pdf_path)
#     full_text = ""
    
#     for page_num, page in enumerate(doc, 1):
#         text = page.get_text()
#         full_text += f"\n{'='*50}\n PAGE {page_num}\n{'='*50}\n{text}"
    
#     # Save to file
#     with open(output_path, 'w', encoding='utf-8') as f:
#         f.write(full_text)
    
#     print(f"Extracted {len(doc)} pages")
#     print(f"Total characters: {len(full_text)}")
#     print(f"Saved to: {output_path}")
    
#     # Show first 2000 characters
#     print("\n--- PREVIEW (first 2000 chars) ---")
#     print(full_text[:2000])
    
# except Exception as e:
#     print(f"Error: {e}")



# import fitz  # PyMuPDF

# def extract_unstructured_text(pdf_path):
#     doc = fitz.open(pdf_path)
#     text = ""
#     for page_num in range(len(doc)):
#         page = doc.load_page(page_num)
#         text += page.get_text("text") 
        
    
#     return text

# pdf_path = r"C:\Users\Dell\Downloads\rodic resumes\rodic resumes\BE.pdf"
# output_path = r"c:\Users\Dell\Desktop\resume_parser\extracted_unstructured_text.txt"

# unstructured_text = extract_unstructured_text(pdf_path)

# # Save to file
# with open(output_path, 'w', encoding='utf-8') as f:
#     f.write(unstructured_text) # Extracting unstructured text

# print(unstructured_text)


# import pdfplumber

# def extract_table_data(pdf_path):
#     with pdfplumber.open(pdf_path) as pdf:
#         tables = []
#         for page in pdf.pages:
#             # Extract tables from each page
#             for table in page.extract_tables():
#                 tables.append(table)
#         return tables

# # Example usage

# print(tables[0])  # Print the first table (if available)



import pdfplumber
import json

def extract_data_from_pdf(pdf_path):
    # Initialize a dictionary to store data
    data = {}
    
    # Open the PDF file using pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        # Iterate over each page
        for page_num in range(len(pdf.pages)):
            page = pdf.pages[page_num]
            
            # Extract unstructured text from the page
            text = page.extract_text()

            # Extract tables from the page
            tables = page.extract_tables()

            # Store extracted text and tables in the dictionary
            data[page_num + 1] = {
                "text": text,
                "tables": tables
            }
    
    return data

def save_data_to_json(data, output_path):
    # Save the extracted data into a JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


pdf_path = r"C:\Users\Dell\Downloads\rodic resumes\rodic resumes\BE.pdf"
output_path = r"c:\Users\Dell\Desktop\resume_parser\extracted_data_pdfplumber.json"

# Extract data from the PDF
extracted_data = extract_data_from_pdf(pdf_path)

# Save the extracted data to a JSON file
save_data_to_json(extracted_data, output_path)

print(f"Data extracted and saved to {output_path}")





# tables = extract_table_data(pdf_path)

# # Save to file
# with open(output_path, 'w', encoding='utf-8') as f:
#     for table in tables:
#             for row in table:
#                 # Convert None values to empty strings, then join
#                 cleaned_row = [str(cell) if cell is not None else "" for cell in row]
#                 f.write(", ".join(cleaned_row) + "\n")  # Writing row data to file, each cell separated by a comma
#             f.write("\n")  

# if tables:
#     print(tables[0])
# else:
#     print("No tables found in the PDF")
