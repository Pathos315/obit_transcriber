import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import UnidentifiedImageError

from src.transcriber import replace_text_with_dict, transcribe_images


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


@pytest.mark.parametrize(
    "input_text, expected_output",
    [
        # Test for hyphenated words at line breaks
        ("hello-\nworld", "helloworld"),
        # Test for replacing '4' with 'a' between letters
        ("c4t", "cat"),
        # Test for replacing '1' with 'l' between letters
        ("he1lo", "hello"),
        # Test for replacing '0' with 'o' between letters
        ("h0me", "home"),
        # Test for replacing '5' with 's' between letters
        ("pas5word", "password"),
        # Test for replacing specific year patterns
        ("'9o", "'90"),
        ("'8o", "'80"),
        ("'7o", "'70"),
        ("'6o", "'60"),
        # Test for removing unwanted characters
        ("hello§world", "helloworld"),
        ("hello•world", "helloworld"),
        ("hello~world", "helloworld"),
        ("hello`world", "helloworld"),
        # Test for preserving newlines unless followed by <PARAGRAPH>
        ("line1\nline2", "line1\nline2"),
        ("line1\n<PARAGRAPH>\nline2", "line1\n<PARAGRAPH>\nline2"),
    ],
)
def test_replace_text_with_dict(input_text, expected_output):

    assert replace_text_with_dict(input_text) == expected_output
