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
```

## Usage

The module provides three main functions:

### 1. Downloading Obituaries

Run the obituary scanner to download obituaries for a specific year:

```bash
poetry run python obit_scanner.py
```

When prompted, enter the desired year (e.g., 1991, 1997). The script will:

- Scrape obituary links from the GLBT History website
- Download the obituary images
- Save them to the `obituaries/YEAR` directory

### 2. Processing and Transcribing Obituaries

To process downloaded obituaries and extract text:

```bash
poetry run python obit_reader.py
```

By default, this processes images in the `obituaries/1997` directory. To specify a different directory or enable spellchecking:

```python
# In your script or modify obit_reader.py
from obit_reader import process_images

# Process images with spellchecking
process_images("obituaries/1991", spellcheck=True)
```

### 3. Custom Preprocessing

You can also use the preprocessing functionality separately:

```python
from preprocessing import preprocess_image
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
