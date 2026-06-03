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


# --- OCR Pass ---

import os
import tempfile
from unittest.mock import MagicMock
from scripts.extract_questions import call_mistral_ocr, get_or_create_ocr_cache


def _make_ocr_client(markdown_pages: list[str]) -> MagicMock:
    pages = [MagicMock(markdown=m) for m in markdown_pages]
    response = MagicMock(pages=pages)
    client = MagicMock()
    client.ocr.process.return_value = response
    return client


def test_call_mistral_ocr_joins_pages(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF fake content")
    client = _make_ocr_client(["## Page 1\nQuestion 1", "## Page 2\nQuestion 2"])
    result = call_mistral_ocr(str(pdf), client)
    assert result == "## Page 1\nQuestion 1\n\n## Page 2\nQuestion 2"


def test_call_mistral_ocr_sends_base64(tmp_path):
    import base64
    pdf = tmp_path / "test.pdf"
    content = b"%PDF test"
    pdf.write_bytes(content)
    client = _make_ocr_client(["markdown"])
    call_mistral_ocr(str(pdf), client)
    call_args = client.ocr.process.call_args
    doc = call_args.kwargs["document"]
    expected_b64 = base64.b64encode(content).decode()
    assert expected_b64 in doc["document_url"]


def test_get_or_create_cache_hit_skips_api(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.extract_questions.OCR_CACHE_DIR", str(tmp_path))
    cache = tmp_path / "Paper-I_2024.md"
    cache.write_text("cached markdown", encoding="utf-8")
    client = MagicMock()
    result = get_or_create_ocr_cache("Paper I", 2024, "irrelevant.pdf", client, reocr=False)
    assert result == "cached markdown"
    client.ocr.process.assert_not_called()


def test_get_or_create_cache_miss_calls_api(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.extract_questions.OCR_CACHE_DIR", str(tmp_path))
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF fake")
    client = _make_ocr_client(["fresh markdown"])
    result = get_or_create_ocr_cache("Paper I", 2024, str(pdf), client, reocr=False)
    assert result == "fresh markdown"
    assert (tmp_path / "Paper-I_2024.md").read_text(encoding="utf-8") == "fresh markdown"


def test_get_or_create_cache_reocr_bypasses_cache(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.extract_questions.OCR_CACHE_DIR", str(tmp_path))
    cache = tmp_path / "Paper-I_2024.md"
    cache.write_text("stale markdown", encoding="utf-8")
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF fake")
    client = _make_ocr_client(["fresh markdown"])
    result = get_or_create_ocr_cache("Paper I", 2024, str(pdf), client, reocr=True)
    assert result == "fresh markdown"
    client.ocr.process.assert_called_once()


# --- Parse Pass ---

from scripts.extract_questions import parse_markdown_to_questions


def _make_chat_client(json_response: str) -> MagicMock:
    msg = MagicMock(content=json_response)
    choice = MagicMock(message=msg)
    resp = MagicMock(choices=[choice])
    client = MagicMock()
    client.chat.complete.return_value = resp
    return client


def test_parse_markdown_injects_paper_and_year():
    items = '[{"question_number":1,"unit_number":"I","section":"A","marks":3,"word_limit":30,"tamil":"தமிழ்","english":"Discuss the significance."}]'
    client = _make_chat_client(items)
    qs = parse_markdown_to_questions("## markdown", "Paper I", 2024, client)
    assert qs[0]["paper"] == "Paper I"
    assert qs[0]["year"] == 2024


def test_parse_markdown_sets_fixed_fields():
    items = '[{"question_number":1,"unit_number":"II","section":"B","marks":10,"word_limit":150,"tamil":"","english":"Explain the role of RBI in monetary policy."}]'
    client = _make_chat_client(items)
    qs = parse_markdown_to_questions("## md", "Paper III", 2023, client)
    q = qs[0]
    assert q["unit_name"] is None
    assert q["sub_questions"] == []
    assert q["noise_flagged"] is False


def test_parse_markdown_preserves_tamil():
    items = '[{"question_number":1,"unit_number":"I","section":"A","marks":3,"word_limit":30,"tamil":"இந்தியாவின் தேசிய கொடி","english":"Examine the National Flag code."}]'
    client = _make_chat_client(items)
    qs = parse_markdown_to_questions("## md", "Paper II", 2024, client)
    assert "இந்தியாவின்" in qs[0]["tamil"]


def test_parse_markdown_handles_llm_explanation_wrapper():
    wrapped = 'Here is the extracted data:\n[{"question_number":1,"unit_number":"I","section":"A","marks":3,"word_limit":30,"tamil":"","english":"What is the significance of monsoon?"}]\nEnd.'
    client = _make_chat_client(wrapped)
    qs = parse_markdown_to_questions("## md", "Paper III", 2019, client)
    assert len(qs) == 1
    assert qs[0]["question_number"] == 1


def test_parse_markdown_null_fields_preserved():
    items = '[{"question_number":5,"unit_number":null,"section":null,"marks":null,"word_limit":null,"tamil":"","english":"Explain the Western Ghats biodiversity."}]'
    client = _make_chat_client(items)
    qs = parse_markdown_to_questions("## md", "Paper III", 2017, client)
    q = qs[0]
    assert q["unit_number"] is None
    assert q["section"] is None
    assert q["marks"] is None
    assert q["word_limit"] is None


def test_parse_markdown_uses_correct_model():
    from scripts.extract_questions import MISTRAL_PARSE_MODEL
    items = '[{"question_number":1,"unit_number":"I","section":"A","marks":3,"word_limit":30,"tamil":"","english":"Long enough question text here."}]'
    client = _make_chat_client(items)
    parse_markdown_to_questions("## md", "Paper I", 2024, client)
    call_args = client.chat.complete.call_args
    assert call_args.kwargs["model"] == MISTRAL_PARSE_MODEL
