import importlib.util
import subprocess
import sys
import os
import tempfile
import zipfile
from pathlib import Path


def check_and_install_packages():
    """Check and install required packages if they aren't already installed."""
    required_packages = {
        "pytesseract": "pytesseract",
        "cv2": "opencv-python",
        "pdf2image": "pdf2image",
        "PIL": "Pillow"
    }
    
    for module, package in required_packages.items():
        if importlib.util.find_spec(module) is None:
            print(f"Installing required package: {package}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])


# Run the package check at import time
check_and_install_packages()

# Now import the required packages
import pytesseract
import cv2
import numpy as np
from pdf2image import convert_from_path
from PIL import Image


def process_pdf(pdf_path, output_zip_path):
    """
    Process a PDF file:
    1. Convert PDF to images
    2. Deskew and clean images
    3. OCR the processed images
    4. Save results to a zip file
    """
    # Create temp directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Convert PDF to images
        print(f"Converting PDF: {pdf_path}")
        images = convert_from_path(pdf_path)
        
        # Process each page
        text_files = []
        for i, img in enumerate(images):
            page_num = i + 1
            print(f"Processing page {page_num}/{len(images)}")
            
            # Save image to temp file for processing
            img_path = os.path.join(temp_dir, f"page_{page_num}.png")
            img.save(img_path)
            
            # Clean and deskew the image
            cleaned_img = clean_and_deskew(img_path)
            
            # Perform OCR
            text = pytesseract.image_to_string(cleaned_img)
            
            # Save the text to a file
            text_file_path = os.path.join(temp_dir, f"page_{page_num}.txt")
            with open(text_file_path, "w", encoding="utf-8") as text_file:
                text_file.write(text)
            text_files.append(text_file_path)
        
        # Create zip file with all text files
        create_zip(text_files, output_zip_path)
    
    print(f"OCR processing complete. Results saved to {output_zip_path}")


def clean_and_deskew(image_path):
    """
    Clean and deskew an image to improve OCR results
    """
    # Read the image
    img = cv2.imread(image_path)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply threshold to get black and white image
    _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)
    
    # Find all contours
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    # Find the largest contour (assumed to be the page)
    if contours:
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Find minimum area rectangle
        rect = cv2.minAreaRect(largest_contour)
        angle = rect[2]
        
        # Adjust angle if needed
        if angle < -45:
            angle = 90 + angle
        
        # Deskew only if significant angle detected
        if abs(angle) > 0.5:
            (h, w) = img.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            deskewed = cv2.warpAffine(gray, M, (w, h), 
                                      flags=cv2.INTER_CUBIC, 
                                      borderMode=cv2.BORDER_REPLICATE)
        else:
            deskewed = gray
    else:
        deskewed = gray
    
    # Apply adaptive threshold for better text detection
    processed = cv2.adaptiveThreshold(
        deskewed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    return processed


def create_zip(file_paths, output_zip_path):
    """
    Create a zip file containing all the given files
    """
    with zipfile.ZipFile(output_zip_path, 'w') as zipf:
        for file_path in file_paths:
            zipf.write(file_path, os.path.basename(file_path))


def check_tesseract_installed():
    """Check if Tesseract is installed and accessible."""
    try:
        # This will raise an exception if tesseract is not installed
        pytesseract.get_tesseract_version()
        return True
    except pytesseract.TesseractNotFoundError:
        return False


if __name__ == "__main__":
    import argparse
    
    # Check for tesseract installation
    if not check_tesseract_installed():
        print("ERROR: Tesseract OCR is not installed or not in PATH.")
        print("Please install Tesseract: https://github.com/tesseract-ocr/tesseract")
        sys.exit(1)
    
    # Check for poppler dependency
    try:
        convert_from_path(None)
    except Exception as e:
        if "poppler" in str(e).lower():
            print("ERROR: Poppler is not installed (required by pdf2image).")
            if sys.platform.startswith('win'):
                print("Download from: https://github.com/oschwartz10612/poppler-windows/releases")
            elif sys.platform.startswith('darwin'):
                print("Install with: brew install poppler")
            else:
                print("Install with: apt-get install poppler-utils")
            sys.exit(1)
    
    parser = argparse.ArgumentParser(description="PDF OCR Tool")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument(
        "--output", "-o", 
        help="Output zip file path (default: PDF name with .zip extension)",
        default=None
    )
    
    args = parser.parse_args()
    
    # Set default output path if not provided
    if args.output is None:
        pdf_name = Path(args.pdf_path).stem
        args.output = f"{pdf_name}_ocr.zip"
    
    # Process the PDF
    process_pdf(args.pdf_path, args.output)
