# tests/test_extract_questions.py
from scripts.extract_questions import (
    has_tamil, split_bilingual, is_noise, parse_marks_and_wordlimit
)
from tests.conftest import BILINGUAL_BLOCK


def test_has_tamil_detects_tamil():
    assert has_tamil("இந்தியாவின்") is True
    assert has_tamil("Examine the model") is False
    assert has_tamil("Flag Code 2002 – ஆம் ஆண்டு") is True


def test_split_bilingual_separates_parts():
    tamil, english = split_bilingual(BILINGUAL_BLOCK)
    assert "இந்தியாவின்" in tamil
    assert "Examine" in english


def test_split_bilingual_empty():
    assert split_bilingual("") == ("", "")


def test_is_noise_phone():
    assert is_noise("044-43533445, 044-45543082") is True


def test_is_noise_url():
    assert is_noise("www.shankariasacademy.com") is True


def test_is_noise_institute():
    assert is_noise("SHANKAR IAS ACADEMY, Plot No 1742") is True


def test_is_noise_turn_over():
    assert is_noise("திருப்புக/Turn over") is True


def test_is_noise_page_number():
    assert is_noise("5") is True
    assert is_noise("15") is True


def test_is_noise_paper_code():
    assert is_noise("GS1MII/24") is True


def test_is_noise_real_question():
    assert is_noise("Examine the model set of instructions for hoisting National Flag") is False


def test_parse_marks_wordlimit_10m():
    text = "Answer not exceeding 150 words each.\nEach question carries ten marks.\n(4 x 10 = 40)"
    marks, wl = parse_marks_and_wordlimit(text)
    assert marks == 10
    assert wl == 150


def test_parse_marks_wordlimit_15m():
    text = "Answer not exceeding 250 words each.\nEach question carries fifteen marks."
    marks, wl = parse_marks_and_wordlimit(text)
    assert marks == 15
    assert wl == 250


def test_parse_marks_wordlimit_3m():
    text = "Answer not exceeding 30 words each.\nEach question carries three marks.\n(30 x 3 = 90)"
    marks, wl = parse_marks_and_wordlimit(text)
    assert marks == 3
    assert wl == 30
