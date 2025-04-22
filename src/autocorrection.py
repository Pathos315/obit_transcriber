import re
from functools import lru_cache
from threading import Lock
from typing import Optional, Set

from spellchecker import SpellChecker

from src.logger import logger


class SingletonMeta(type):
    """
    Thread-safe implementation of Singleton pattern using metaclass.
    """

    _instances = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):  # type: ignore[override]
        with cls._lock:
            if cls not in cls._instances:  # type: ignore[override]
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance  # type: ignore
        return cls._instances[cls]  # type: ignore


class SpellCheckerSingleton(metaclass=SingletonMeta):
    """
    Thread-safe Singleton SpellChecker for the obituary reader project.
    """

    _spell_checker: Optional[SpellChecker] = None
    _custom_word_file: str = "valid_words.txt"

    def __init__(self, custom_word_file: Optional[str] = None):
        """
        Initialize the SpellChecker with optional custom word file.

        Args:
            custom_word_file: Path to a file with custom valid words to load
        """
        if custom_word_file:
            self._custom_word_file = custom_word_file

        if self._spell_checker is None:
            self._spell_checker = SpellChecker()
            try:
                self._spell_checker.word_frequency.load_text_file(
                    self._custom_word_file
                )
                logger.info(f"Loaded custom words from {self._custom_word_file}")
            except Exception as e:
                logger.error(
                    f"Failed to load custom words from {self._custom_word_file}: {e}"
                )

    @property
    def spell_checker(self) -> SpellChecker:
        """
        Get the SpellChecker instance.

        Returns:
            SpellChecker: The initialized SpellChecker instance
        """
        return self._spell_checker  # type: ignore[override]

    def correction(self, word: str) -> str:
        """
        Get the corrected spelling of a word.

        Args:
            word: The word to correct

        Returns:
            str: The corrected word or the original if no correction is found
        """
        if not word:
            return word

        corrected = self._spell_checker.correction(word)  # type: ignore[override]
        return corrected if corrected else word


# Pre-compile punctuation set for performance
PUNCT_SET: Set[str] = set('.,:;!?()[]{}""\'')


# Cache frequent corrections
@lru_cache(maxsize=10000)
def cached_correction(word: str) -> str:
    """
    Get the corrected spelling of a word with caching for performance.

    Args:
        word: The word to correct

    Returns:
        str: The corrected word or the original if no correction is found
    """
    spell_checker = SpellCheckerSingleton()
    return spell_checker.correction(word)


def normalize_whitespace(text: str) -> str:
    """
    Splits the text into lines, strips all trailing whitespace, regularizes all quote glyphs,
    and rejoins it.

    Args:
        text: Input text, which likely has irregular spacing or quotation marks.

    Returns:
        str: A cleaned body of text with normalized whitespaces and quotes.
    """
    logger.debug(f"Normalizing whitespace for text of length {len(text)}")

    normalized_lines = [line.strip() for line in text.splitlines()]

    # strip trailing whitespace
    normalized_lines = [re.sub(r" +", " ", line) for line in normalized_lines]

    # regularize quotes
    normalized_lines = [re.sub(r"[\"`´]", "'", line) for line in normalized_lines]

    logger.debug(
        f"Whitespace normalization complete, result length: {len(normalized_lines)}"
    )
    return "\n".join(normalized_lines)


def autocorrect_text(text: str) -> str:
    """
    Autocorrect misspelled words in a text using pyspellchecker, optimized for speed.

    Args:
        text: The input text to correct

    :returns str: The corrected text
    """
    # Split the text into words
    words = text.split()

    # Corrected words list
    corrected_words: list[str] = []

    for word in words:
        # Skip empty words
        if not word:
            result_append(word)
            continue

        # Fast path for capitalized words (likely proper nouns)
        if word[0].isupper():
            result_append(word)
            continue

        # Skip empty strings
        if not word:
        # Skip empty strings
        if not word:
            continue

        # Get the corrected word using cached correction
        corrected = cached_correction(word)

        # Add back punctuation
        corrected_words.append(corrected + punctuation)

    # Join the corrected words back into a text
    return " ".join(corrected_words)
