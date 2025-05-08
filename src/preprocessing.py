from pathlib import Path

from PIL import Image, UnidentifiedImageError
import cv2
import numpy as np

import src.config as config


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
    img_cv: cv2.typing.MatLike = cv2.imread(str(image_path))

    # By default OpenCV stores images in BGR format and since pytesseract assumes RGB format,
    # we need to convert from BGR to RGB format/mode:
    img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)

    img_rgb = scale_up_image(img_rgb)

    img_rgb = denoise(img_rgb)

    # Convert to binary image, applying thresholding to handle background noise
    thresh = cv2.threshold(
        img_rgb,
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )[1]

    # Perform dilation to connect broken text
    kernel = np.ones(
        (1, 1),
        np.uint8,
    )
    dilated = cv2.dilate(
        thresh,
        kernel,
        iterations=2,
    )

    # Invert back to black text on white background
    processed = cv2.bitwise_not(dilated)
    return processed


def scale_up_image(image: cv2.typing.MatLike) -> cv2.typing.MatLike:
    """Increases resolution to help with small fonts
    Newspaper font can be very small, scaling helps OCR
    """
    height, width = image.shape[:2]  # Triple the size
    return cv2.resize(
        image,
        (
            int(width * config.SCALE_FACTOR),
            int(height * config.SCALE_FACTOR),
        ),
        interpolation=cv2.INTER_CUBIC,
    )  # Use CUBIC for better quality


def denoise(img: cv2.typing.MatLike) -> cv2.typing.MatLike:
    """
    Denoise the image to improve OCR accuracy
    Args:
        img (cv2.typing.MatLike): Input image
    Returns:
        cv2.typing.MatLike: Denoised image
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, config.GAUSSIAN_KERNEL_SIZE, 0)
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)

    # 4. CONTRAST ENHANCEMENT - Improve text visibility
    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=config.CLAHE_TILE_SIZE)
    return clahe.apply(denoised)
