import os
import cv2
import pandas as pd
import numpy as np

# EasyOCR is much better for product packaging and supports Arabic/English well
try:
    import easyocr
except ImportError:
    print("EasyOCR not found. Please install it using: !pip install easyocr")

# Path to the images directory
IMAGE_DIR = 'market_image/New folder'

def process_image(image_path, reader):
    """
    Uses EasyOCR to extract text and attempts to identify the 'Main Product Name'
    based on bounding box size and confidence.
    """
    try:
        # Read the image
        img = cv2.imread(image_path)
        if img is None:
            return "Error", "Error"

        # Run OCR (Arabic and English)
        # detail=1 returns bounding box, text, and confidence
        results = reader.readtext(image_path, detail=1)
        
        if not results:
            return "", ""

        # Logic to find the 'Main Product Name':
        # 1. Calculate the area of each bounding box.
        # 2. Prefer larger text (often the product name).
        # 3. Filter out very low confidence scores.
        
        processed_data = []
        for (bbox, text, prob) in results:
            # bbox is [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
            # Calculate approximate area
            width = max(bbox[1][0], bbox[2][0]) - min(bbox[0][0], bbox[3][0])
            height = max(bbox[2][1], bbox[3][1]) - min(bbox[0][1], bbox[1][1])
            area = width * height
            
            processed_data.append({
                "text": text.strip(),
                "area": area,
                "confidence": prob
            })

        # Sort by area descending to find the biggest text
        processed_data.sort(key=lambda x: x['area'], reverse=True)
        
        # The main name is likely the largest text block with decent confidence
        main_name = ""
        if processed_data:
            # We take the largest one as the 'Main' name
            main_name = processed_data[0]['text']
        
        # The 'All Text' is everything else joined together
        all_text = " | ".join([d['text'] for d in processed_data if d['confidence'] > 0.2])
        
        return main_name, all_text

    except Exception as e:
        return f"Error: {str(e)}", ""

def main():
    if not os.path.exists(IMAGE_DIR):
        print(f"Directory not found: {IMAGE_DIR}")
        return

    # Initialize EasyOCR reader for Arabic and English
    print("Initializing EasyOCR (this may take a moment to download models)...")
    reader = easyocr.Reader(['ar', 'en'])

    results = []
    files = sorted([f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    
    print(f"Found {len(files)} images. Starting OCR...")

    for filename in files:
        file_path = os.path.join(IMAGE_DIR, filename)
        print(f"Processing {filename}...")
        
        main_name, all_text = process_image(file_path, reader)
        
        results.append({
            "filename": filename,
            "product_name": main_name,
            "full_details": all_text
        })

    # Save results to a CSV
    df = pd.DataFrame(results)
    df.to_csv('ocr_results.csv', index=False, encoding='utf-8-sig')
    print("\nOCR extraction complete. Results saved to 'ocr_results.csv'.")
    
    # Display results
    print("\nSample Results:")
    print(df[['filename', 'product_name']].head(20))

if __name__ == "__main__":
    # In Colab:
    # !pip install easyocr
    main()
