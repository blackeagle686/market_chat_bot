import os
import cv2
import pytesseract
from PIL import Image
import pandas as pd

# Path to the images directory (Update this for Colab if necessary)
IMAGE_DIR = 'market_image/New folder'

def extract_text_from_image(image_path):
    try:
        # Load the image using OpenCV
        img = cv2.imread(image_path)
        if img is None:
            return "Error: Could not read image"
        
        # Convert to grayscale for better OCR
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply some thresholding to clean up the image
        # You might need to adjust these parameters depending on the images
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        
        # Use pytesseract to extract text
        text = pytesseract.image_to_string(thresh)
        return text.strip()
    except Exception as e:
        return f"Error: {str(e)}"

def main():
    if not os.path.exists(IMAGE_DIR):
        print(f"Directory not found: {IMAGE_DIR}")
        return

    results = []
    files = sorted([f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    
    print(f"Found {len(files)} images. Starting OCR...")

    for filename in files:
        file_path = os.path.join(IMAGE_DIR, filename)
        print(f"Processing {filename}...")
        extracted_text = extract_text_from_image(file_path)
        
        # Clean up the text (remove newlines, extra spaces)
        clean_text = " ".join(extracted_text.split())
        
        results.append({
            "filename": filename,
            "extracted_text": clean_text
        })

    # Save results to a CSV
    df = pd.DataFrame(results)
    df.to_csv('ocr_results.csv', index=False)
    print("\nOCR extraction complete. Results saved to 'ocr_results.csv'.")
    print(df.head(20))

if __name__ == "__main__":
    # In Colab, you need to install tesseract-ocr:
    # !apt-get install tesseract-ocr
    # !pip install pytesseract
    
    # You might also need to specify the tesseract cmd path if it's not in the PATH
    # pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'
    
    main()
