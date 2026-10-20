import logging
import os
import shutil
import io
from typing import Tuple, Union
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

def perform_ocr(image_input: Union[str, bytes, bytearray, Image.Image]) -> Tuple[str, bool, str]:
    """
    Performs OCR on an image file path, raw image bytes, or PIL Image instance.
    Returns: (extracted_text, is_success, message)
    """
    tess_path = get_tesseract_path()
    if not tess_path:
        msg = "Tesseract OCR binary not found. Please install Tesseract and configure TESSERACT_CMD."
        logger.warning(msg)
        return "", False, msg

    try:
        pytesseract.pytesseract.tesseract_cmd = tess_path
        # Auto-configure TESSDATA_PREFIX if not explicitly set
        tess_dir = os.path.dirname(tess_path)
        candidates = [
            os.path.join(tess_dir, "tessdata"),
            tess_dir,
            "/usr/share/tesseract-ocr/4.00/tessdata",
            "/usr/share/tesseract-ocr/5/tessdata",
            "/usr/share/tessdata"
        ]
        for c in candidates:
            if os.path.exists(os.path.join(c, "eng.traineddata")):
                os.environ["TESSDATA_PREFIX"] = c
                break

        if isinstance(image_input, Image.Image):
            img = image_input
            should_close = False
        elif isinstance(image_input, (bytes, bytearray)):
            img = Image.open(io.BytesIO(image_input))
            should_close = True
        else:
            img = Image.open(str(image_input))
            should_close = True

        try:
            processed = preprocess_image(img)
            text = pytesseract.image_to_string(processed, lang='eng', config='--psm 11')
            cleaned_text = text.strip()
            if not cleaned_text:
                # Try raw image without extra pre-processing
                text = pytesseract.image_to_string(img)
                cleaned_text = text.strip()
            
            return cleaned_text, True, "OCR completed successfully"
        finally:
            if should_close:
                img.close()
    except Exception as e:
        input_desc = f"bytes ({len(image_input)} B)" if isinstance(image_input, (bytes, bytearray)) else str(image_input)
        logger.error(f"OCR execution failed on {input_desc}: {e}")
        return "", False, f"OCR error: {str(e)}"
