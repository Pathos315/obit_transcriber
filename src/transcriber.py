import functools
import re
from pathlib import Path

import cv2
import pytesseract
from PIL import Image, UnidentifiedImageError

from src.autocorrection import autocorrect_text
from src.config import TESSERACT_CONFIG
from src.preprocessing import preprocess_image


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


def transcribe_images(
    filepath: str | Path,
    spellcheck: bool = False,
) -> None:
    """
    Transcribes text from images in a given directory using Tesseract OCR.
    Args:
        filepath (str): Path to the directory containing images
        spellcheck (bool): Whether to perform spell checking on the extracted text
    """
    directory = Path(filepath).rglob("*.jpg")
    for file in directory:

        # Preprocess the image
        processed_img = preprocess_image(file)
        temp_file: str = "temp_processed.jpg"
        cv2.imwrite(temp_file, processed_img)

        try:
            with Image.open(temp_file) as temp_img:
                # Extract text
                text = pytesseract.image_to_string(  # type: ignore
                    temp_img,
                    lang="eng",
                    config=TESSERACT_CONFIG,
                )
                text = clean_irregular_text(text)  # type: ignore
                if spellcheck:
                    text = autocorrect_text(text)
                print(text)
        except UnidentifiedImageError:
            continue
