# tests/test_tag_questions.py
import json
from unittest.mock import MagicMock
from scripts.tag_questions import form_batches, tag_batch_with_llm, merge_tags


def test_form_batches_groups_by_paper_and_unit():
    qs = [
        {"paper": "Paper II", "unit_number": "I",  "question_number": 1},
        {"paper": "Paper II", "unit_number": "I",  "question_number": 2},
        {"paper": "Paper II", "unit_number": "II", "question_number": 11},
        {"paper": "Paper I",  "unit_number": "I",  "question_number": 1},
    ]
    batches = form_batches(qs)
    assert len(batches) == 3
    pairs = {(b["paper"], b["unit_number"]) for b in batches}
    assert ("Paper II", "I")  in pairs
    assert ("Paper II", "II") in pairs
    assert ("Paper I",  "I")  in pairs


def test_tag_batch_returns_tags():
    syllabus_slice = {
        "Colonial Period": {"themes": [
            {"theme_name": "European Colonialism", "keywords": ["Advent of Europeans"]}
        ]}
    }
    qs = [{"question_number": 1, "english": "Describe the advent of Europeans in India."}]
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text=json.dumps([
        {"question_number": 1, "heading": "Colonial Period",
         "theme": "European Colonialism", "keyword": "Advent of Europeans"}
    ]))]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_resp

    result = tag_batch_with_llm(qs, syllabus_slice, "Paper II", "I", mock_client)
    assert result[0]["heading"] == "Colonial Period"
    assert result[0]["keyword"] == "Advent of Europeans"


def test_merge_tags_adds_tags_field():
    qs = [{"paper": "Paper II", "unit_number": "I", "question_number": 1, "english": "Q1"}]
    tag_map = {("Paper II", "I", 1): {
        "heading": "Colonial Period", "theme": "Colonialism", "keyword": "Advent of Europeans"
    }}
    syllabus = {"PAPER II": {"UNIT I: Modern History": {}}}
    result = merge_tags(qs, tag_map, syllabus)
    assert "tags" in result[0]
    assert result[0]["tags"]["keyword"] == "Advent of Europeans"
    assert "unit" in result[0]["tags"]
