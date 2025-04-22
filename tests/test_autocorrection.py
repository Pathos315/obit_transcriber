from src.autocorrection import autocorrect_text, cached_correction


def test_autocorrect_empty_text():
    assert autocorrect_text("") == ""


def test_autocorrect_no_misspellings():
    text = "This is a correctly spelled sentence."
    assert autocorrect_text(text) == text


def test_autocorrect_with_misspellings():
    text = "Ths is a sentnce with erors."
    expected = "This is a sentence with errors."
    assert autocorrect_text(text) == expected


def test_autocorrect_with_punctuation():
    text = "Ths, is a tst."
    expected = "This, is a test."
    assert autocorrect_text(text) == expected


def test_autocorrect_with_proper_nouns():
    text = "John and Marry went to Londn."
    expected = "John and Marry went to London."
    assert autocorrect_text(text) == expected


def test_autocorrect_with_all_punctuation():
    text = "!!! ???"
    assert autocorrect_text(text) == text


def test_autocorrect_with_mixed_case():
    text = "thIs is a tEst."
    expected = "this is a test."
    assert autocorrect_text(text) == expected


def test_autocorrect_with_numbers():
    text = "Ths is 2023."
    expected = "This is 2023."
    assert autocorrect_text(text) == expected


def test_autocorrect_with_special_characters():
    text = "Ths is a t#st."
    expected = "This is a t#st."
    assert autocorrect_text(text) == expected


def test_cached_correction_correct_word():
    assert cached_correction("correct") == "correct"


def test_cached_correction_misspelled_word():
    # Assuming "corect" is corrected to "correct" by the spell checker
    assert cached_correction("corect") == "correct"


def test_cached_correction_nonexistent_word():
    # Assuming "asdfgh" is not in the dictionary and remains unchanged
    assert cached_correction("asdfgh") == "asdfgh"


def test_cached_correction_with_punctuation():
    # Assuming "corect." is corrected to "correct."
    assert cached_correction("corect.") == "correct."


def test_cached_correction_case_sensitivity():
    # Assuming "Corect" is corrected to "Correct"
    assert cached_correction("Corect") == "Correct"
