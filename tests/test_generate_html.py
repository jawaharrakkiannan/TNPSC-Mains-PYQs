# tests/test_generate_html.py
from scripts.generate_html import generate_html
from tests.conftest import MINIMAL_QUESTIONS


def test_returns_html_string():
    html = generate_html(MINIMAL_QUESTIONS)
    assert html.startswith("<!DOCTYPE html>")


def test_embeds_questions_json():
    html = generate_html(MINIMAL_QUESTIONS)
    assert "const QUESTIONS =" in html
    assert "Paper II" in html


def test_has_filter_selects():
    html = generate_html(MINIMAL_QUESTIONS)
    for fid in ["f-year", "f-paper", "f-unit", "f-theme", "f-keyword", "f-section", "f-marks"]:
        assert fid in html, f"Missing filter: {fid}"


def test_has_two_views():
    html = generate_html(MINIMAL_QUESTIONS)
    assert "view-questions" in html
    assert "view-frequency" in html


def test_has_frequency_tables():
    html = generate_html(MINIMAL_QUESTIONS)
    assert "themes-table" in html
    assert "keywords-table" in html


def test_esc_function_present():
    html = generate_html(MINIMAL_QUESTIONS)
    assert "function esc(" in html
