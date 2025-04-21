# config.py
from pathlib import Path

# Base paths
BASE_DIR = Path("obit_transcriber")
DATA_DIR = BASE_DIR / Path("obituaries")
LOG_DIR = BASE_DIR / Path("logs")

# OCR Settings
TESSERACT_CONFIG = r"--oem 3 --psm 1 --dpi 200 -c preserve_interword_spaces=1 -c tessedit_enable_dict_correction=1 -c tessedit_char_whitelist=0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.,' '\'\"-"

# Image preprocessing
SCALE_FACTOR = 3.0
BILATERAL_FILTER_D = 9
GAUSSIAN_KERNEL_SIZE = (5, 5)
BILATERAL_D = 9
CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_SIZE = (8, 8)

# Network settings
REQUEST_TIMEOUT = 30
RATE_LIMIT_DELAY = 1  # seconds
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
