import pandas as pd
from rapidfuzz import process, fuzz
import json
import os

def create_mapping():
    # Load OCR results
    if not os.path.exists('ocr_results.csv'):
        print("ocr_results.csv not found!")
        return
    
    ocr_df = pd.read_csv('ocr_results.csv')
    
    # Load Excel data
    if not os.path.exists('data_set.xlsx'):
        print("data_set.xlsx not found!")
        return
    
    excel_df = pd.read_excel('data_set.xlsx')
    
    # Standardize column names for Excel
    # Product Name (Brand), Price (EGP), Description, Partition, Unnamed: 4
    name_col = "Product Name (Brand)"
    if name_col not in excel_df.columns:
        # Try to find a similar column
        for col in excel_df.columns:
            if "name" in col.lower():
                name_col = col
                break
    
    print(f"Using column '{name_col}' for product names.")
    
    excel_products = excel_df[name_col].astype(str).tolist()
    mapping = {}
    
    print("Matching OCR results with Excel products...")
    
    for _, row in ocr_df.iterrows():
        filename = row['filename']
        ocr_name = str(row['product_name'])
        
        if not ocr_name or ocr_name.lower() == 'unknown':
            continue
            
        # Find best match in Excel
        # We use a threshold to avoid bad matches
        match = process.extractOne(ocr_name, excel_products, scorer=fuzz.token_set_ratio)
        
        if match:
            best_name, score, index = match
            if score >= 70:  # Adjust threshold as needed
                mapping[best_name] = filename
                print(f"Matched: '{ocr_name}' -> '{best_name}' (Score: {score}, File: {filename})")

    # Save mapping to JSON
    with open('product_image_map.json', 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=4, ensure_ascii=False)
    
    print(f"\nCreated mapping for {len(mapping)} products. Saved to 'product_image_map.json'.")

if __name__ == "__main__":
    create_mapping()
