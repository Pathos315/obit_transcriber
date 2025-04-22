# Obituary Reader

A Python module to download, process, and transcribe obituaries from the Bay Area Reporter GLBT History archives.

## Overview

This tool provides functionality to:

1. **Download obituaries** from the GLBT History archives for a specified year
2. **Process and preprocess images** to enhance readability for OCR
3. **Transcribe text** from obituary images using Tesseract OCR
4. **Clean and autocorrect** the extracted text for improved accuracy

## Installation

This project uses Poetry for dependency management.

### Prerequisites

- Python 3.12+
- Tesseract OCR engine
- Poetry

### Installing Tesseract OCR

#### On Ubuntu/Debian:

```bash
sudo apt update
sudo apt install tesseract-ocr
```

#### On macOS:

```bash
brew install tesseract
```

#### On Windows:

Download and install from [GitHub Tesseract release page](https://github.com/UB-Mannheim/tesseract/wiki)

### Installing the Package

```bash
# Clone the repository
git clone https://github.com/yourusername/obituary-reader.git
cd obituary-reader

# Install dependencies using Poetry
poetry install

# Install in development mode
poetry install
```

## Command-Line Usage

After installation, you can run the tool using the `obituary_reader` command:

### Downloading Obituaries

```bash
# Download obituaries from a specific year
obituary_reader download 1991

# Download obituaries from a range of years
obituary_reader download 1991 --yearto 1999
```

### Transcribing Obituaries

```bash
# Transcribe all obituaries in the default directory
obituary_reader transcribe

# Transcribe obituaries in a specific directory with spellchecking
obituary_reader transcribe --directory obituaries/1991 --spellcheck
```

## Programmatic Usage

You can also use the module in your Python scripts:

### 1. Downloading Obituaries

```python
from src.downloader import download_obituaries

# Download obituaries for a specific year range
download_obituaries("1991", "1997")
```

### 2. Processing and Transcribing Obituaries

```python
from src.transcriber import transcribe_images

# Process images with spellchecking
transcribe_images("obituaries/1991", spellcheck=True)
```

### 3. Custom Preprocessing

```python
from src.preprocessing import preprocess_image
from pathlib import Path

# Preprocess a single image
processed_img = preprocess_image(Path("path/to/image.jpg"))
```

## Module Structure

- **obit_scanner.py**: Web scraper to download obituaries
- **preprocessing.py**: Image preprocessing for OCR enhancement
- **obit_reader.py**: OCR and text extraction
- **autocorrection.py**: Text cleaning and spellchecking
- **valid_words.txt**: Domain-specific words for spellchecking

## Technical Details

### Image Preprocessing Steps

1. Converts images to grayscale
2. Applies thresholding to handle background noise
3. Increases resolution for better OCR with small fonts
4. Applies denoising filters
5. Enhances contrast to improve text visibility
6. Connects broken text with dilation
7. Inverts images to have black text on white background

### Text Cleaning Process

1. Fixes hyphenated words at line breaks
2. Corrects common OCR errors (e.g., "1" instead of "l")
3. Removes irregular characters
4. Applies spellchecking with domain-specific exceptions

## License

MIT

## Author

John Fallot <john.fallot@gmail.com>
