from pathlib import Path
import tempfile

from PIL import Image, UnidentifiedImageError
import cv2
import pytesseract
from tqdm import tqdm

from src.autocorrection import autocorrect_text
from src.config import TESSERACT_CONFIG
from src.database import ObituaryDatabase, ObituaryRecord
from src.logger import logger
from src.preprocessing import preprocess_image
from src.textnormalizer import TextNormalizer


def _process_single_image(
    file: Path,
    db: ObituaryDatabase,
    normalizer: TextNormalizer,
    processed_records: list[ObituaryRecord],
    spellcheck: bool = False,
) -> None:
    """
    Process a single obituary image with proper resource management.

    This method handles:
    - Temporary file creation and cleanup
    - Image resource management with context managers
    - Error handling and logging

    Args:
        file: Path to the image file
        db: Database instance for storing records
        normalizer: Text normalizer instance
        processed_records: List to append processed records to
        spellcheck: Whether to perform spell checking
    """
    # Check if the file is already in the database
    existing_record = db.get_record_by_image_path(str(file))
    if existing_record:
        processed_records.append(existing_record)
        return

    # Preprocess the image and use a temporary file with automatic cleanup
    try:
        processed_img = preprocess_image(file)

        # Use NamedTemporaryFile for automatic cleanup
        # delete=False because we need to write with cv2 and read with PIL
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Write preprocessed image to temp file
            cv2.imwrite(temp_path, processed_img)

            # Open both images with proper context managers
            with Image.open(temp_path) as temp_img, Image.open(file) as raw_img:
                process_obituary_image(
                    db,
                    normalizer,
                    processed_records,
                    file,
                    temp_img,
                    raw_img,
                    spellcheck=spellcheck,
                )
        finally:
            # Ensure temp file is deleted even if an error occurs
            Path(temp_path).unlink(missing_ok=True)

    except ValueError as e:
        logger.error(f"Error preprocessing {file}: {e}")
    except UnidentifiedImageError as e:
        logger.warning(f"Could not identify image {file}: {e}")
    except Exception as e:
        logger.error(f"Error processing {file}: {e}")


def transcribe_images(
    filepath: str | Path,
    spellcheck: bool = False,
    db_path: str = "obituaries.db",
) -> list[ObituaryRecord]:
    """
    Transcribes text from images in a given directory using Tesseract OCR.

    This function implements proper resource management for:
    - Database connections
    - Temporary files (automatically cleaned up)
    - Image file handles (properly closed via context managers)

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

    try:
        for file in tqdm(
            directory,
            total=len(directory),
            desc="Transcribing obituaries: ",
            unit="obituary",
        ):
            _process_single_image(file, db, normalizer, processed_records, spellcheck)
    finally:
        # Ensure database connection is always closed
        db.close()

    return processed_records


def process_obituary_image(
    db: ObituaryDatabase,
    normalizer: TextNormalizer,
    processed_records: list[ObituaryRecord],
    file: Path,
    temp_img: Image.Image,
    raw_img: Image.Image,
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
        raw_image=raw_img,
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
