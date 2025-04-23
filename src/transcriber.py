from pathlib import Path

import cv2
import pytesseract
from PIL import Image, UnidentifiedImageError
from tqdm import tqdm

from src.autocorrection import autocorrect_text
from src.config import TESSERACT_CONFIG
from src.database import ObituaryDatabase, ObituaryRecord
from src.logger import logger
from src.preprocessing import preprocess_image
from src.textnormalizer import TextNormalizer


def transcribe_images(
    filepath: str | Path,
    spellcheck: bool = False,
    db_path: str = "obituaries.db",
) -> list[ObituaryRecord]:
    """
    Transcribes text from images in a given directory using Tesseract OCR.
    Args:
        filepath (str): Path to the directory containing images
        spellcheck (bool): Whether to perform spell checking on the extracted text
        db_path (str): Path to the SQLite database file
    Returns:
        list[ObituaryRecord]: List of processed obituary records
    """
    # Initialize database once
    normalizer = TextNormalizer()
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
                process_obituary_image(
                    db,
                    normalizer,
                    processed_records,
                    file,
                    temp_img,
                    spellcheck=spellcheck,
                )

        except UnidentifiedImageError:
            continue
        except Exception as e:
            logger.error(f"Error processing {file}: {e}")
            continue
    # Close database connection
    db.close()

    return processed_records


def process_obituary_image(
    db: ObituaryDatabase,
    normalizer: TextNormalizer,
    processed_records: list[ObituaryRecord],
    file: Path,
    temp_img: Image.Image,
    spellcheck: bool = False,
) -> None:
    """
    Processes the image to extract text and create a record in the database.
    Args:
        db (ObituaryDatabase): The database instance
        processed_records (list[ObituaryRecord]): List to store processed records
        file (Path): The file path of the image
        temp_img (Image.Image): The preprocessed image
        spellcheck (bool): Whether to perform spell checking on the extracted text

    Returns:
        None
    """
    text: str = pytesseract.image_to_string(  # type: ignore
        temp_img,
        lang="eng",
        config=TESSERACT_CONFIG,
    )
    text = normalizer.clean_text(text)  # type: ignore
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
