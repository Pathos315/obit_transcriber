import functools
import re
from pathlib import Path

import cv2
import pytesseract
from PIL import Image, UnidentifiedImageError
from tqdm import tqdm

from src.autocorrection import autocorrect_text, normalize_whitespace
from src.config import TESSERACT_CONFIG
from src.database import ObituaryDatabase, ObituaryRecord
from src.logger import logger
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
    normalize: bool = True,
    db_path: str = "obituaries.db",
) -> list[ObituaryRecord]:
    """
    Transcribes text from images in a given directory using Tesseract OCR.
    Args:
        filepath (str): Path to the directory containing images
        spellcheck (bool): Whether to perform spell checking on the extracted text
    """
    # Initialize database once
    db = ObituaryDatabase(db_path)
    processed_records: list[ObituaryRecord] = []

    directory = list(Path(filepath).rglob("*.jpg"))
    for file in tqdm(
        directory,
        total=len(directory),
        desc="Transcribing obituaries: ",
        unit="obituary",
    ):

        # Check if the file is already in the database
        existing_record = db.get_record_by_image_path(str(file))
        if existing_record:
            processed_records.append(existing_record)
            continue

        # Preprocess the image
        try:
            processed_img = preprocess_image(file)
            temp_file: str = "temp_processed.jpg"
            cv2.imwrite(temp_file, processed_img)
        except ValueError as e:
            logger.error(f"Error preprocessing {file}: {e}")
            continue

        try:
            with Image.open(temp_file) as temp_img:
                # Extract text
                text = pytesseract.image_to_string(  # type: ignore
                    temp_img,
                    lang="eng",
                    config=TESSERACT_CONFIG,
                )
                text = clean_irregular_text(text)  # type: ignore
                if normalize:
                    text = normalize_whitespace(text)
                if spellcheck:
                    text = autocorrect_text(text)
                obituary_url = get_obituary_url(file)

                # Create and store record
                record = ObituaryRecord.from_image_path(
                    image_path=str(file.name),
                    text_content=text,
                    obituary_url=obituary_url,
                )
                db.add_record(record)
                processed_records.append(record)

        except UnidentifiedImageError:
            continue
        except Exception as e:
            logger.error(f"Error processing {file}: {e}")
            continue
    # Close database connection
    db.close()

    return processed_records


def get_obituary_url(file: Path) -> str:
    """
    Generates the obituary URL based on the filename.
    Args:
        file (Path): The file path of the image
    Returns:
        str: The generated obituary URL
    """
    # Extract the filename without extension
    filename = file.stem
    obituary_url = f"http://obit.glbthistory.org/olo/display.jsp?name={filename}"
    return obituary_url
