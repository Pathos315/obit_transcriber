import functools
import re
from pathlib import Path

import cv2
import numpy as np
import pytesseract
from PIL import Image, UnidentifiedImageError
from spellchecker import SpellChecker

spell = SpellChecker()
spell.word_frequency.load_text_file("obit_transcriber/valid_words.txt")


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


def preprocess_image(image_path: Path) -> cv2.typing.MatLike:
    """
    Preprocess the image for OCR by:
    1. Converting to grayscale
    2. Applying thresholding to handle background noise
    3. Performing dilation to connect broken text
    4. Inverting the image to have black text on a white background
    Args:
        image_path (Path): Path to the image file
    Returns:
        cv2.typing.MatLike: Preprocessed image ready for OCR
    """
    # Check if the file exists
    if not image_path.is_file():
        raise FileNotFoundError(f"File not found: {image_path}")
    # Check if the file is an image
    if not image_path.suffix.lower() in [".jpg", ".jpeg", ".png"]:
        raise ValueError(f"Unsupported file type: {image_path.suffix}")
    # Check if the file is empty
    if image_path.stat().st_size == 0:
        raise ValueError(f"File is empty: {image_path}")
    # Check if the file is corrupted
    try:
        with Image.open(image_path) as img:
            img.verify()  # Verify the image is not corrupted
    except (IOError, UnidentifiedImageError):
        raise ValueError(f"File is corrupted: {image_path}")

    # Read the image
    img = cv2.imread(image_path)

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Apply thresholding to handle background noise
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # Perform dilation to connect broken text
    kernel = np.ones((1, 1), np.uint64)
    dilated = cv2.dilate(thresh, kernel, iterations=1)

    # Invert back to black text on white background
    processed = cv2.bitwise_not(dilated)

    return processed


def autocorrect_text(text: str) -> str:
    """
    Autocorrect misspelled words in a text using pyspellchecker, optimized for speed.

    Args:
        text (str): The input text to correct

    Returns:
        str: The corrected text
    """
    # Pre-compile the punctuation set for faster lookups
    PUNCT_SET = set('.,:;!?()[]{}""\'')

    # Use list comprehension for initial splitting (faster than calling split())
    words = text.split()
    result = []
    result_append = result.append  # Local reference for faster method calls

    # Process words in batches to reduce function call overhead
    batch_size = 100
    for i in range(0, len(words), batch_size):
        batch = words[i : i + batch_size]

        for word in batch:
            # Handle common case first (no punctuation) for early return
            if not word:
                continue

            # Check if word has any punctuation at all before processing
            if word[-1] not in PUNCT_SET:
                # Skip correction for capitalized words (likely proper nouns)
                if word[0].isupper():
                    result_append(word)
                else:
                    # Only correct lowercase words
                    result_append(spell.correction(word) or word)
                continue

            # Fast punctuation extraction with less string operations
            end_idx = len(word) - 1
            while end_idx >= 0 and word[end_idx] in PUNCT_SET:
                end_idx -= 1

            # Extract word and punctuation more efficiently
            if end_idx < 0:
                # Word is all punctuation
                result_append(word)
                continue

            actual_word = word[: end_idx + 1]
            punctuation = word[end_idx + 1 :]

            # Skip correction for capitalized words (likely proper nouns)
            if actual_word and actual_word[0].isupper():
                result_append(actual_word + punctuation)
            elif actual_word:
                corrected = spell.correction(actual_word)
                result_append((corrected or actual_word) + punctuation)
            else:
                result_append(punctuation)

    # Join is typically faster than multiple string concatenations
    return " ".join(result)


def process_images(filepath: str) -> None:
    """
    Transcribes text from images in a given directory using Tesseract OCR.
    Args:
        filepath (str): Path to the directory containing images
    """
    directory = Path(filepath).glob("*.jpg")
    for file in directory:

        # Preprocess the image
        processed_img = preprocess_image(file)
        temp_file = "temp_processed.jpg"
        # Save the processed image temporarily for debugging
        cv2.imwrite(temp_file, processed_img)

        try:
            # Preprocess the image
            with Image.open(temp_file) as temp_img:
                # Extract text
                text = pytesseract.image_to_string(
                    temp_img,
                    config=r"--oem 3 --psm 1 --dpi 150",
                )

                text = clean_irregular_text(text)
                # text = autocorrect_text(text)
                print(text)
        except UnidentifiedImageError:
            continue


if __name__ == "__main__":
    process_images("../obituaries/1997")
