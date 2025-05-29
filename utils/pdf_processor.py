import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import os
import pdfplumber

class PDFProcessor:
    def __init__(self):
        pytesseract.pytesseract.tesseract_cmd = os.getenv('TESSERACT_CMD', '/usr/bin/tesseract')

    def extract_text(self, pdf_path):
        """Extract text with OCR fallback for images"""
        text = ""
        
        # First try pdfplumber for clean text extraction
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            if len(text) > 100:  # If sufficient text extracted
                return text
        except:
            pass

        # Fallback to PyMuPDF with OCR
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text() + "\n"
            
            # OCR for images if text is minimal
            if len(text) < 50 * (page_num + 1):  # Rough heuristic
                for img in page.get_images():
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image = Image.open(io.BytesIO(image_bytes))
                    text += pytesseract.image_to_string(image) + "\n"
        return text

    def process_directory(self, directory):
        """Process all PDFs in a directory"""
        documents = []
        for filename in os.listdir(directory):
            if filename.endswith(".pdf"):
                pdf_path = os.path.join(directory, filename)
                text = self.extract_text(pdf_path)
                chapter_num = filename.split('_')[1].replace('C', '')
                documents.append({
                    "text": text,
                    "metadata": {
                        "source": filename,
                        "chapter": f"Chapter {chapter_num}",
                        "subject": "Science",
                        "class": "9"
                    }
                })
        return documents