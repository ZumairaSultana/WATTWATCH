"""Read the number on a meter photo using Tesseract OCR.

OCR on meter displays is not always reliable (glare, angle, 7-segment
digits), so the app always shows the detected number in an editable box
for the user to confirm before it is saved.

Requires the Tesseract program to be installed on the computer, in
addition to the `pytesseract` Python package.
"""

import re
from dataclasses import dataclass

from PIL import ImageFilter, ImageOps

NUMBER_PATTERN = re.compile(r"\d+(?:[.,]\d+)?")
TESSERACT_CONFIG = "--psm 6 -c tessedit_char_whitelist=0123456789."


@dataclass(frozen=True)
class OcrResult:
    value: float | None
    raw_text: str
    error: str | None = None


def preprocess(image):
    """Make the digits stand out: fix rotation, grayscale, enlarge, sharpen contrast, black/white."""
    image = ImageOps.exif_transpose(image)
    gray = ImageOps.grayscale(image)
    if gray.width < 1000:
        scale = 1000 / gray.width
        gray = gray.resize((1000, int(gray.height * scale)))
    gray = ImageOps.autocontrast(gray)
    gray = gray.filter(ImageFilter.MedianFilter(3))
    return gray.point(lambda p: 255 if p > 128 else 0)


def parse_reading(text):
    """Pick the longest number in the OCR text (the meter reading is usually the biggest)."""
    matches = NUMBER_PATTERN.findall(text or "")
    if not matches:
        return None
    best = max(matches, key=lambda m: sum(ch.isdigit() for ch in m))
    return float(best.replace(",", "."))


def read_meter(image):
    try:
        import pytesseract
    except ImportError:
        return OcrResult(None, "", "pytesseract is not installed (pip install pytesseract).")

    processed = preprocess(image)
    texts = []
    try:
        # Try dark-on-light and light-on-dark, since meter displays differ.
        for candidate in (processed, ImageOps.invert(processed)):
            texts.append(pytesseract.image_to_string(candidate, config=TESSERACT_CONFIG))
    except pytesseract.TesseractNotFoundError:
        return OcrResult(None, "", "Tesseract OCR program not found. Install it or type the reading.")

    raw = "\n".join(t.strip() for t in texts if t.strip())
    values = [v for v in (parse_reading(t) for t in texts) if v is not None]
    if not values:
        return OcrResult(None, raw, "No number found in the photo. Please type the reading.")
    best = max(values, key=lambda v: len(str(int(v))))
    return OcrResult(best, raw)
