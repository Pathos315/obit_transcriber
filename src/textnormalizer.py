import re
from dataclasses import dataclass, field
from typing import Dict, Pattern

from src.logger import logger


@dataclass
class TextNormalizer:
    """
    A class for normalizing and cleaning text, particularly OCR output.
    Organizes text transformations by category and pre-compiles regex patterns.
    """

    # Compiled pattern dictionaries (initialized in __post_init__)
    ocr_corrections: Dict[Pattern[str], str] = field(default_factory=dict)
    hyphenation_fixes: Dict[Pattern[str], str] = field(default_factory=dict)
    year_fixes: Dict[Pattern[str], str] = field(default_factory=dict)
    character_removals: Dict[Pattern[str], str] = field(default_factory=dict)
    whitespace_fixes: Dict[Pattern[str], str] = field(default_factory=dict)
    quote_fixes: Dict[Pattern[str], str] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize and compile all regex patterns"""
        # OCR digit-to-letter corrections (common OCR errors)
        ocr_corrections = {
            r"([a-zA-Z])4([a-zA-Z])": r"\1a\2",  # '4' between letters → 'a'
            r"([a-zA-Z])1([a-zA-Z])": r"\1l\2",  # '1' between letters → 'l'
            r"([a-zA-Z])0([a-zA-Z])": r"\1o\2",  # '0' between letters → 'o'
            r"([a-zA-Z])5([a-zA-Z])": r"\1s\2",  # '5' between letters → 's'
        }
        self.ocr_corrections = {re.compile(k): v for k, v in ocr_corrections.items()}

        # Fix hyphenated words at line breaks
        self.hyphenation_fixes = {re.compile(r"(\w+)-\s*\n\s*(\w+)"): r"\1\2"}

        # Fix year abbreviations
        year_fixes = {
            r"'9o": "'90",
            r"'8o": "'80",
            r"'7o": "'70",
            r"'6o": "'60",
        }
        self.year_fixes = {re.compile(k): v for k, v in year_fixes.items()}

        # Characters to remove
        self.character_removals = {re.compile(r"[§|•~`]"): ""}

        # Whitespace normalization
        self.whitespace_fixes = {
            re.compile(r" +"): " ",
            re.compile(r"\r\n"): "\n",
            re.compile(r"\r"): "\n",
        }

        # Quote glyph normalization
        self.quote_fixes = {re.compile(r"[\"`´]"): "'"}

        # Paragraph normalization - only included if needed
        self.paragraph_fixes = {re.compile(r"\n(?!<PARAGRAPH>)"): "\n"}

    def apply_patterns(self, text: str, pattern_dict: Dict[Pattern[str], str]) -> str:
        """Apply a dictionary of compiled patterns to the text."""
        result = text
        for pattern, replacement in pattern_dict.items():
            result = pattern.sub(replacement, result)
        return result

    def normalize_line_endings(self, text: str) -> str:
        """Normalize all line endings to '\n'."""
        return self.apply_patterns(
            text,
            {
                re.compile(r"\r\n"): "\n",
                re.compile(r"\r"): "\n",
            },
        )

    def strip_lines(self, text: str) -> str:
        """Strip whitespace from each line."""
        lines = (line.strip() for line in text.split("\n"))
        return "\n".join(lines)

    def normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace within lines."""
        logger.debug(f"Normalizing whitespace for text of length {len(text)}")

        # Split into lines and strip
        lines = [line.strip() for line in text.splitlines()]

        # Normalize spaces within each line
        lines = [self.apply_patterns(line, {re.compile(r" +"): " "}) for line in lines]

        # Normalize quotes
        lines = [self.apply_patterns(line, self.quote_fixes) for line in lines]

        logger.debug(f"Whitespace normalization complete, result length: {len(lines)}")
        return "\n".join(lines)

    def fix_ocr_errors(self, text: str) -> str:
        """Fix common OCR errors like digit/letter confusion."""
        text = self.apply_patterns(text, self.ocr_corrections)
        text = self.apply_patterns(text, self.year_fixes)
        return text

    def clean_text(self, text: str, normalize_quotes: bool = True) -> str:
        """
        Perform comprehensive text cleaning and normalization.

        Args:
            text: The input text to clean
            normalize_quotes: Whether to normalize quotation marks

        Returns:
            str: The cleaned and normalized text
        """
        if not text:
            return text

        logger.debug(f"Cleaning text of length {len(text)}")

        # Normalize line endings
        text = self.normalize_line_endings(text)

        # Strip excess whitespace from each line
        text = self.strip_lines(text)

        # Fix hyphenated words at line breaks
        text = self.apply_patterns(text, self.hyphenation_fixes)

        # Fix OCR errors (digit/letter confusion)
        text = self.fix_ocr_errors(text)

        # Remove unwanted characters
        text = self.apply_patterns(text, self.character_removals)

        # Normalize whitespace within lines
        text = self.normalize_whitespace(text)

        # Apply quote normalization if requested
        if normalize_quotes:
            text = self.apply_patterns(text, self.quote_fixes)

        logger.debug(f"Text cleaning complete, result length: {len(text)}")
        return text
