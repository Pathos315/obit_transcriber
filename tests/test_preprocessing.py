from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytest

import src.config as config
from src.preprocessing import denoise, preprocess_image, scale_up_image


@pytest.fixture
def valid_image_path(tmp_path: Path):
    """Fixture to create a valid image file for testing."""
    image_path = tmp_path / "test_image.jpg"
    # Create a simple black image
    black_image = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.imwrite(str(image_path), black_image)  # type: ignore
    return image_path


@pytest.fixture
def empty_image_path(tmp_path: Path):
    """Fixture to create an empty image file."""
    empty_path = tmp_path / "empty_image.jpg"
    empty_path.touch()  # Create an empty file
    return empty_path


@pytest.fixture
def corrupted_image_path(tmp_path: Path):
    """Fixture to create a corrupted image file."""
    corrupted_path = tmp_path / "corrupted_image.jpg"
    with open(corrupted_path, "wb") as f:
        f.write(b"not an image")
    return corrupted_path


def test_preprocess_image_valid(valid_image_path: Any):
    """Test preprocess_image with a valid image."""
    processed_image = preprocess_image(valid_image_path)
    assert processed_image is not None
    assert isinstance(processed_image, np.ndarray)
    assert processed_image.shape[:2] == (100, 100)  # Check dimensions


def test_preprocess_image_file_not_found():
    """Test preprocess_image with a non-existent file."""
    non_existent_path = Path("non_existent.jpg")
    with pytest.raises(FileNotFoundError):
        preprocess_image(non_existent_path)


def test_preprocess_image_unsupported_file_type(tmp_path: Path):
    """Test preprocess_image with an unsupported file type."""
    unsupported_path = tmp_path / "test.txt"
    unsupported_path.write_text("This is a text file.")
    with pytest.raises(ValueError, match="Unsupported file type"):
        preprocess_image(unsupported_path)


def test_preprocess_image_empty_file(empty_image_path: Any):
    """Test preprocess_image with an empty file."""
    with pytest.raises(ValueError, match="File is empty"):
        preprocess_image(empty_image_path)


def test_preprocess_image_corrupted_file(corrupted_image_path: Any):
    """Test preprocess_image with a corrupted image file."""
    with pytest.raises(ValueError, match="File is corrupted"):
        preprocess_image(corrupted_image_path)


@pytest.fixture
def sample_image():
    """Fixture to create a sample image for testing."""
    return np.zeros((50, 50, 3), dtype=np.uint8)  # A simple black image


def test_scale_up_image_valid(sample_image):
    """Test scale_up_image with a valid image."""
    config.SCALE_FACTOR = 2  # Set scale factor for testing
    scaled_image = scale_up_image(sample_image)
    assert scaled_image is not None
    assert isinstance(scaled_image, np.ndarray)
    assert scaled_image.shape[:2] == (100, 100)  # Check dimensions after scaling


def test_scale_up_image_invalid_input():
    """Test scale_up_image with invalid input."""
    with pytest.raises(AttributeError):
        scale_up_image(None)  # Passing None should raise an error


def test_scale_up_image_zero_scale_factor(
    sample_image: _Array[tuple[int, int, int], np.unsignedinteger[_8Bit]],
):
    """Test scale_up_image with a zero scale factor."""
    config.SCALE_FACTOR = 0  # Set scale factor to zero
    with pytest.raises(cv2.error):
        scale_up_image(sample_image)


def test_scale_up_image_negative_scale_factor(
    sample_image: _Array[tuple[int, int, int], np.uint8],
):
    """Test scale_up_image with a negative scale factor."""
    config.SCALE_FACTOR = -1  # Set scale factor to negative
    with pytest.raises(cv2.error):
        scale_up_image(sample_image)


def test_denoise_valid_image(sample_image):
    """Test denoise with a valid image."""
    config.GAUSSIAN_KERNEL_SIZE = (5, 5)  # Set kernel size for testing
    config.CLAHE_TILE_SIZE = (8, 8)  # Set CLAHE tile size for testing
    denoised_image = denoise(sample_image)
    assert denoised_image is not None
    assert isinstance(denoised_image, np.ndarray)
    assert (
        denoised_image.shape[:2] == sample_image.shape[:2]
    )  # Dimensions should remain the same


def test_denoise_invalid_input():
    """Test denoise with invalid input."""
    with pytest.raises(cv2.error):
        denoise(None)  # Passing None should raise an error


def test_denoise_empty_image():
    """Test denoise with an empty image."""
    empty_image = np.zeros((0, 0, 3), dtype=np.uint8)  # Empty image
    with pytest.raises(cv2.error):
        denoise(empty_image)


def test_denoise_grayscale_image():
    """Test denoise with a grayscale image."""
    config.GAUSSIAN_KERNEL_SIZE = (5, 5)  # Set kernel size for testing
    config.CLAHE_TILE_SIZE = (8, 8)  # Set CLAHE tile size for testing
    grayscale_image = np.zeros((50, 50), dtype=np.uint8)  # Grayscale image
    denoised_image = denoise(grayscale_image)
    assert denoised_image is not None
    assert isinstance(denoised_image, np.ndarray)
    assert (
        denoised_image.shape == grayscale_image.shape
    )  # Dimensions should remain the same
