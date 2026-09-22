import logging
import os
import shutil
from typing import Tuple
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from app.config import settings

logger = logging.getLogger("investigation.ocr")

def get_tesseract_path() -> str:
    """Detects or configures the Tesseract OCR executable path."""
    if os.path.exists(settings.TESSERACT_CMD):
        return settings.TESSERACT_CMD
    which_path = shutil.which("tesseract")
    if which_path:
        return which_path
    # Common default locations on Windows
    fallbacks = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe")
    ]
    for p in fallbacks:
        if os.path.exists(p):
            return p
    return ""

def preprocess_image(image: Image.Image) -> Image.Image:
    """Preprocesses image to maximize OCR recognition accuracy."""
    # Convert to grayscale
    gray = image.convert('L')
    # Enhance contrast
    enhancer = ImageEnhance.Contrast(gray)
    contrasted = enhancer.enhance(2.0)
    # Slight sharpening filter
    sharpened = contrasted.filter(ImageFilter.SHARPEN)
    return sharpened

def perform_ocr(image_path: str) -> Tuple[str, bool, str]:
    """
    Performs OCR on an image file.
    Returns: (extracted_text, is_success, message)
    """
    tess_path = get_tesseract_path()
    if not tess_path:
        msg = "Tesseract OCR binary not found. Please install Tesseract and configure TESSERACT_CMD."
        logger.warning(msg)
        return "", False, msg

    try:
        pytesseract.pytesseract.tesseract_cmd = tess_path
        with Image.open(image_path) as img:
            processed = preprocess_image(img)
            text = pytesseract.image_to_string(processed, lang='eng', config='--psm 11')
            cleaned_text = text.strip()
            if not cleaned_text:
                # Try raw image without extra pre-processing
                text = pytesseract.image_to_string(img)
                cleaned_text = text.strip()
            
            return cleaned_text, True, "OCR completed successfully"
    except Exception as e:
        logger.error(f"OCR execution failed on {image_path}: {e}")
        return "", False, f"OCR error: {str(e)}"
