from __future__ import annotations

from functools import lru_cache
from threading import Lock
from typing import Optional, Set

from spellchecker import SpellChecker

from src.logger import logger


class SingletonMeta(type):
    """
    Thread-safe implementation of Singleton pattern using metaclass.
    """

    _instances: dict[type, object] = {}
    _lock: Lock = Lock()

    def __call__(cls, *args: object, **kwargs: object) -> object:
        with cls._lock:
            if cls not in cls._instances:  # type:ignore[union-attr]
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]


class SpellCheckerSingleton(metaclass=SingletonMeta):
    """
    Thread-safe Singleton SpellChecker for the obituary reader project.
    """

    _spell_checker: SpellChecker  # Instance of pyspellchecker.SpellChecker
    _custom_word_file: str = "valid_words.txt"

    def __init__(self, custom_word_file: Optional[str] = None):
        """
        Initialize the SpellChecker with optional custom word file.

        Args:
            custom_word_file: Path to a file with custom valid words to load
        """
        if custom_word_file:
            self._custom_word_file = custom_word_file

        self._spell_checker = SpellChecker()
        try:
            self._spell_checker.word_frequency.load_text_file(self._custom_word_file)
            logger.info(f"Loaded custom words from {self._custom_word_file}")
        except Exception as e:
            logger.error(
                f"Failed to load custom words from {self._custom_word_file}: {e}"
            )

    @property
    def spell_checker(self) -> SpellChecker:  # Explicitly specify the return type
        """
        Get the SpellChecker instance.

        Returns:
            SpellChecker: The initialized SpellChecker instance
        """
        if not self._spell_checker:
            raise ValueError("SpellChecker is not initialized.")
        return self._spell_checker

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

        if not self._spell_checker:
            raise ValueError("SpellChecker is not initialized.")
        corrected = self._spell_checker.correction(word)
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
    return spell_checker.correction(word)  # type: ignore


def autocorrect_text(text: str) -> str:
    """
    Autocorrect misspelled words in a text using pyspellchecker.

    Args:
        text: The input text to correct

    Returns:
        str: The corrected text
    """
    # Split the text into words
    words = text.split()

    # Corrected words list
    corrected_words: list[str] = []

    for word in words:
        # Preserve punctuation
        punctuation = ""
        while word and word[-1] in PUNCT_SET:
            punctuation = word[-1] + punctuation
            word = word[:-1]

        # Skip correction for capitalized words (likely proper nouns)
        if word and word[0].isupper():
            corrected_words.append(word + punctuation)
            continue

        # Skip empty strings
        if not word:
            continue

        # Get the corrected word using cached correction
        corrected = cached_correction(word)

        # Add back punctuation
        corrected_words.append(corrected + punctuation)

    # Join the corrected words back into a text
    return " ".join(corrected_words)
