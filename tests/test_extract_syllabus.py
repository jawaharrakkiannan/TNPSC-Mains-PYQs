# tests/test_extract_syllabus.py
from unittest.mock import MagicMock, patch
from scripts.extract_syllabus import extract_text_blocks, parse_syllabus_hierarchy


def _make_mock_doc(spans):
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_doc.__iter__ = lambda s: iter([mock_page])
    mock_page.get_text.return_value = {
        "blocks": [
            {
                "type": 0,
                "lines": [{"spans": [{"text": t, "size": sz, "flags": fl}]}]
            }
            for t, sz, fl in spans
        ]
    }
    return mock_doc


def test_extract_text_blocks_captures_text_and_bold():
    doc = _make_mock_doc([("PAPER II", 14.0, 16), ("keyword", 10.0, 0)])
    with patch("scripts.extract_syllabus.fitz.open", return_value=doc):
        blocks = extract_text_blocks("fake.pdf")
    assert len(blocks) == 2
    assert blocks[0]["text"] == "PAPER II"
    assert blocks[0]["bold"] is True
    assert blocks[1]["bold"] is False


def test_parse_syllabus_hierarchy_builds_nested_dict():
    blocks = [
        {"text": "PAPER II", "size": 14, "bold": True, "page": 0},
        {"text": "UNIT I: Modern History of India", "size": 12, "bold": True, "page": 0},
        {"text": "Colonial Period and Early Uprisings", "size": 11, "bold": True, "page": 0},
        {"text": "Advent of Europeans", "size": 10, "bold": False, "page": 0},
        {"text": "Colonialism and imperialism", "size": 10, "bold": False, "page": 0},
    ]
    result = parse_syllabus_hierarchy(blocks)
    assert "PAPER II" in result
    unit_key = list(result["PAPER II"].keys())[0]
    assert "Modern History" in unit_key
    headings = result["PAPER II"][unit_key]
    assert "Colonial Period and Early Uprisings" in headings
    kws = headings["Colonial Period and Early Uprisings"]
    assert "Advent of Europeans" in kws
    assert "Colonialism and imperialism" in kws


def test_parse_ignores_very_short_texts():
    blocks = [
        {"text": "PAPER I", "size": 14, "bold": True, "page": 0},
        {"text": "UNIT I: Title", "size": 12, "bold": True, "page": 0},
        {"text": "Heading One", "size": 11, "bold": True, "page": 0},
        {"text": "ab", "size": 10, "bold": False, "page": 0},
        {"text": "Valid Keyword Here", "size": 10, "bold": False, "page": 0},
    ]
    result = parse_syllabus_hierarchy(blocks)
    kws = result["PAPER I"]["UNIT I: Title"]["Heading One"]
    assert "ab" not in kws
    assert "Valid Keyword Here" in kws
