import functools
import re
from pathlib import Path

import cv2
import pytesseract
from autocorrection import autocorrect_text
from PIL import Image, UnidentifiedImageError
from preprocessing import preprocess_image
from lang_processing import merge_ocr_results

TESS_CONFIG = r"--oem 3 --psm 1 --dpi 200 -c preserve_interword_spaces=1 -c classify_font_name='Times New Roman' -c tessedit_enable_dict_correction=1 -c tessedit_char_whitelist=0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.,' '\'\"-"


def replace_text_with_dict(text: str) -> str:
    """
    Replaces specific patterns in the text with their replacements
    using a dictionary of patterns and replacements.
    This is a more efficient way to apply multiple replacements
    without creating intermediate strings.
    The lambda function takes the current string and a pattern,
    and applies the replacement using re.sub.

    Args:
        text (str): The input text to process
    Returns:
        str: The processed text with replacements"""

    # Dictionary of patterns and replacements
    replacements = {
        r"(\w+)-\s*\n\s*(\w+)": r"\1\2",
        r"([a-zA-Z])4([a-zA-Z])": r"\1a\2",
        r"([a-zA-Z])1([a-zA-Z])": r"\1l\2",
        r"([a-zA-Z])0([a-zA-Z])": r"\1o\2",
        r"([a-zA-Z])5([a-zA-Z])": r"\1s\2",
        r"'9o": "'90",
        r"'8o": "'80",
        r"'7o": "'70",
        r"'6o": "'60",
        r"[§|•~`]": "",
        r"\n(?!<PARAGRAPH>)": "\n",
    }

    return functools.reduce(
        lambda s, pattern: re.sub(pattern, replacements[pattern], s),
        replacements.keys(),
        text,
    )


def clean_irregular_text(text: str) -> str:
    """
    Cleans up irregular text by:
    1. Fixing hyphenated words at line breaks
    2. Converting multiple consecutive line breaks to paragraph breaks
    3. Joining lines that are part of the same paragraph
    4. Normalizing whitespace

    Args:
        text (str): Raw irregular text from OCR

    Returns:
        str: Cleaned text with proper paragraphs
    """
    # Step 1: Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Step 2: Remove excess leading/trailing spaces from each line
    lines = (line.strip() for line in text.split("\n"))
    text = "\n".join(lines)

    text = replace_text_with_dict(text)

    return text


def process_images(filepath: str | Path, spellcheck: bool = False) -> None:
    """
    Transcribes text from images in a given directory using Tesseract OCR.
    Args:
        filepath (str): Path to the directory containing images
        spellcheck (bool): Whether to perform spell checking on the extracted text
    """
    directory = Path(filepath).glob("*.jpg")
    for file in directory:

        # Preprocess the image
        processed_img = preprocess_image(file)
        temp_file = "temp_processed.jpg"
        # Save the processed image temporarily for debugging
        cv2.imwrite(temp_file, processed_img)

        try:
            with Image.open(temp_file) as temp_img:
                # Extract text
                text = pytesseract.image_to_string(
                    temp_img,
                    lang="eng",
                    config=TESS_CONFIG,
                )
                text = clean_irregular_text(text)
                if spellcheck:
                    text = autocorrect_text(text)
                print(text)
        except UnidentifiedImageError:
            continue


if __name__ == "__main__":
    process_images("../obituaries/1997")
