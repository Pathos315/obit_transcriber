import re
from functools import lru_cache
from typing import List, Set

from spellchecker import SpellChecker

# Initialize spell checker once, outside function
spell = SpellChecker()
spell.word_frequency.load_text_file("valid_words.txt")

# Pre-compile regex pattern and punctuation set
PUNCT_SET: Set[str] = set('.,:;!?()[]{}""\'')
PUNCT_PATTERN = re.compile(r"([^\w\s]*)$")


# Cache frequent corrections
@lru_cache(maxsize=10000)
def cached_correction(word: str) -> str:
    return spell.correction(word) or word


def normalize_whitespace(text: str) -> str:
    """
    Splits the text into lines, strips all trailing whitespace, regularizes all quote glyphs,
    and rejoins it.

    :param str text: Input text, which likely has irregular spacing or quotation marks.

    :return str: A cleaned body of text with normalized whitespaces and quotes.
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
    Autocorrect misspelled words in a text using pyspellchecker.

    :param text: The input text to correct
    :type text: str

    :returns str: The corrected text
    """

    # Split the text into words
    words = text.split()

    # Corrected words list
    corrected_words = []

    for word in words:
        # Preserve punctuation
        punctuation = ""
        while word and word[-1] in '.,:;!?()[]{}""\'':
            punctuation = word[-1] + punctuation
            word = word[:-1]

        # Skip correction for capitalized words (likely proper nouns)
        if word and word[0].isupper():
            corrected_words.append(word + punctuation)
            continue

        # Skip empty strings
        if not word:
            continue

        # Get the corrected word
        corrected = spell.correction(word)

        # Add back punctuation
        if corrected:
            corrected_words.append(corrected + punctuation)
        else:
            corrected_words.append(word + punctuation)

    # Join the corrected words back into a text
    return " ".join(corrected_words)
