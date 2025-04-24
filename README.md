# Obituary Reader
A Python module to download, process, transcribe, and store obituaries, from
the [Bay Area Reporter Obituary Archives](http://obit.glbthistory.org/olo/index.jsp). The archives are run in
partnership with the [GLBT Historical Society](https://www.glbthistory.org/) in San Francisco, CA.

▼ What Is Remembered Lives. ▼

## Overview

This tool provides comprehensive functionality to:
1. **Download obituaries** from the GLBT History archives for a specified year range
2. **Process and preprocess images** to enhance readability for OCR
3. **Transcribe text** from obituary images using Tesseract OCR
4. **Clean and autocorrect** the extracted text for improved accuracy
5. **Store transcriptions** in a SQLite database with metadata
6. **Export data** to CSV or Excel formats

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
git clone https://github.com/<yourusername>/obituary-reader.git
cd obituary-reader

# Install dependencies using Poetry
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

# Process images with spellchecking and store in database
records = transcribe_images("obituaries/1991", spellcheck=True)
```

## Module Structure
- **downloader.py**: Web scraper to download obituaries
- **preprocessing.py**: Image preprocessing for OCR enhancement
- **transcriber.py**: OCR and text extraction
- **textnormalizer.py**: Text cleaning and normalization
- **autocorrection.py**: Spellchecking with custom dictionary
- **database.py**: SQLite database for storing obituary data
- **config.py**: Configuration settings
- **logger.py**: Logging functionality
- **valid_words.txt**: Domain-specific words for spellchecking

## License
MIT

## Author
John Fallot <john.fallot@gmail.com>
