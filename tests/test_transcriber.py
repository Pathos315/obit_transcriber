from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch

from PIL import UnidentifiedImageError
import pytest

from src.transcriber import transcribe_images


@pytest.fixture
def mock_preprocess_image():
    with patch("src.transcriber.preprocess_image") as mock:
        mock.return_value = MagicMock()
        yield mock


@pytest.fixture
def mock_pytesseract():
    with patch("src.transcriber.pytesseract.image_to_string") as mock:
        mock.return_value = "Sample OCR text"
        yield mock


@pytest.fixture
def mock_clean_irregular_text():
    with patch("src.transcriber.clean_irregular_text") as mock:
        mock.side_effect = lambda text: text
        yield mock


@pytest.fixture
def mock_autocorrect_text():
    with patch("src.transcriber.autocorrect_text") as mock:
        mock.side_effect = lambda text: f"Corrected {text}"
        yield mock


@pytest.fixture
def temp_image_directory():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        # Create a mock image file
        (temp_path / "test_image.jpg").touch()
        yield temp_path


def test_transcribe_images_without_spellcheck(
    temp_image_directory,
    mock_preprocess_image,
    mock_pytesseract,
    mock_clean_irregular_text,
):
    with (
        patch("cv2.imwrite") as mock_cv2_imwrite,
        patch("PIL.Image.open") as mock_image_open,
    ):
        mock_image_open.return_value.__enter__.return_value = MagicMock()

        transcribe_images(temp_image_directory, spellcheck=False)

        mock_preprocess_image.assert_called_once()
        mock_pytesseract.assert_called_once()
        mock_clean_irregular_text.assert_called_once()
        mock_cv2_imwrite.assert_called_once()


def test_transcribe_images_with_spellcheck(
    temp_image_directory,
    mock_preprocess_image,
    mock_pytesseract,
    mock_clean_irregular_text,
    mock_autocorrect_text,
):
    with (
        patch("cv2.imwrite") as mock_cv2_imwrite,
        patch("PIL.Image.open") as mock_image_open,
    ):
        mock_image_open.return_value.__enter__.return_value = MagicMock()

        transcribe_images(temp_image_directory, spellcheck=True)

        mock_preprocess_image.assert_called_once()
        mock_pytesseract.assert_called_once()
        mock_clean_irregular_text.assert_called_once()
        mock_autocorrect_text.assert_called_once()
        mock_cv2_imwrite.assert_called_once()


def test_transcribe_images_handles_unidentified_image_error(
    temp_image_directory,
    mock_preprocess_image,
):
    with (
        patch("cv2.imwrite") as mock_cv2_imwrite,
        patch("PIL.Image.open") as mock_image_open,
    ):
        mock_image_open.side_effect = UnidentifiedImageError

        transcribe_images(temp_image_directory, spellcheck=False)

        mock_preprocess_image.assert_called_once()
        mock_cv2_imwrite.assert_called_once()
