# tests/test_extract_questions.py
import json
import pytest
from scripts.extract_questions import (
    is_math_aptitude,
    parse_marks_and_wordlimit,
    flag_noise_questions,
    _extract_json_array,
    _cache_path,
)


# --- is_math_aptitude ---

def test_is_math_aptitude_profit_loss():
    assert is_math_aptitude("A trader bought goods at a profit of 20 percent.") is True


def test_is_math_aptitude_dice():
    assert is_math_aptitude("Two fair dice are rolled once. Find the probability.") is True


def test_is_math_aptitude_clean_history_question():
    assert is_math_aptitude("Discuss the significance of Avadi Congress of 1955.") is False


def test_is_math_aptitude_empty_string():
    assert is_math_aptitude("") is False


# --- parse_marks_and_wordlimit ---

def test_parse_marks_wordlimit_three_marks_30_words():
    text = "Answer not exceeding 30 words each.\nEach question carries three marks.\n(30 x 3 = 90)"
    marks, wl = parse_marks_and_wordlimit(text)
    assert marks == 3
    assert wl == 30


def test_parse_marks_wordlimit_ten_marks_150_words():
    text = "Answer not exceeding 150 words each.\nEach question carries ten marks.\n(4 x 10 = 40)"
    marks, wl = parse_marks_and_wordlimit(text)
    assert marks == 10
    assert wl == 150


def test_parse_marks_wordlimit_fifteen_marks_250_words():
    text = "Answer not exceeding 250 words each.\nEach question carries fifteen marks."
    marks, wl = parse_marks_and_wordlimit(text)
    assert marks == 15
    assert wl == 250


def test_parse_marks_wordlimit_missing_returns_none():
    marks, wl = parse_marks_and_wordlimit("Some random text without marks info.")
    assert marks is None
    assert wl is None


# --- flag_noise_questions ---

def test_flag_noise_empty_english():
    qs = [{"english": "", "tamil": "", "noise_flagged": False}]
    result = flag_noise_questions(qs)
    assert result[0]["noise_flagged"] is True


def test_flag_noise_short_english():
    qs = [{"english": "Hi.", "tamil": "", "noise_flagged": False}]
    result = flag_noise_questions(qs)
    assert result[0]["noise_flagged"] is True


def test_flag_noise_real_question_untouched():
    qs = [{"english": "Discuss the importance of Panchayati Raj institutions.", "tamil": "", "noise_flagged": False}]
    result = flag_noise_questions(qs)
    assert result[0]["noise_flagged"] is False


# --- _extract_json_array ---

def test_extract_json_array_clean_json():
    raw = '[{"question_number": 1, "english": "Test"}]'
    result = _extract_json_array(raw, "test")
    assert result[0]["question_number"] == 1


def test_extract_json_array_wrapped_in_explanation():
    raw = 'Here is the result:\n[{"question_number": 1, "english": "Test"}]\nDone.'
    result = _extract_json_array(raw, "test")
    assert result[0]["english"] == "Test"


def test_extract_json_array_raises_on_garbage():
    with pytest.raises(ValueError, match="non-JSON"):
        _extract_json_array("This is not JSON at all", "test")


# --- _cache_path ---

def test_cache_path_format():
    path = _cache_path("Paper I", 2024)
    assert path == "data/ocr_cache/Paper-I_2024.md"


def test_cache_path_paper_ii():
    path = _cache_path("Paper II", 2019)
    assert path == "data/ocr_cache/Paper-II_2019.md"
