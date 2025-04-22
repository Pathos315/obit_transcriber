import re
from functools import lru_cache
from typing import List, Set

from spellchecker import SpellChecker

# Initialize spell checker once, outside function
spell = SpellChecker()
spell.word_frequency.load_text_file("obit_transcriber/valid_words.txt")

# Pre-compile regex pattern and punctuation set
PUNCT_SET: Set[str] = set('.,:;!?()[]{}""\'')
PUNCT_PATTERN = re.compile(r"([^\w\s]*)$")


# Cache frequent corrections
@lru_cache(maxsize=10000)
def cached_correction(word: str) -> str:
    return spell.correction(word) or word


def autocorrect_text(text: str) -> str:
    """
    Autocorrect misspelled words in a text using pyspellchecker, optimized for speed.

    Args:
        text (str): The input text to correct

    Returns:
        str: The corrected text
    """
    if not text:
        return text

    # Split text and prepare result list with estimated capacity
    words = text.split()
    result: List[str] = []
    result_append = result.append  # type: ignore

    # Process words directly without batching to reduce overhead
    for word in words:
        # Skip empty words
        if not word:
            result_append(word)
            continue

        # Fast path for capitalized words (likely proper nouns)
        if word[0].isupper():
            result_append(word)
            continue

        # Fast check if word has any punctuation
        if word[-1] not in PUNCT_SET:
            result_append(cached_correction(word))
            continue

        # Use regex to efficiently extract punctuation
        match = PUNCT_PATTERN.search(word)
        if match:
            punct_start = match.start()
            if punct_start == 0:
                # Word is all punctuation
                result_append(word)
                continue

            actual_word = word[:punct_start]
            punctuation = word[punct_start:]
            result_append(cached_correction(actual_word) + punctuation)
        else:
            result_append(cached_correction(word))

    return " ".join(result)
