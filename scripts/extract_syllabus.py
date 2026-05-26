# scripts/extract_syllabus.py
import json
import os
import re
import sys
import fitz
import anthropic

SYLLABUS_PDF = "Mains_PYQs/Group_I_Mains_Syllabus.pdf"
OUTPUT_PATH  = "data/syllabus_themes.json"

_PAPER_RE = re.compile(r"^PAPER\s+[IVX]+", re.IGNORECASE)
_UNIT_RE  = re.compile(r"^UNIT\s+[IVX]+",  re.IGNORECASE)


def extract_text_blocks(pdf_path: str) -> list[dict]:
    doc = fitz.open(pdf_path)
    blocks = []
    for page_num, page in enumerate(doc):
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if text:
                        blocks.append({
                            "text": text,
                            "size": round(span["size"]),
                            "bold": bool(span["flags"] & (1 << 4)),
                            "page": page_num,
                        })
    return blocks


def parse_syllabus_hierarchy(blocks: list[dict]) -> dict:
    result: dict = {}
    current_paper: str | None = None
    current_unit:  str | None = None
    current_heading: str | None = None

    for b in blocks:
        text, bold = b["text"], b["bold"]

        if _PAPER_RE.match(text):
            current_paper = text
            current_unit = current_heading = None
            result.setdefault(current_paper, {})
            continue

        if _UNIT_RE.match(text) and current_paper:
            current_unit = text
            current_heading = None
            result[current_paper].setdefault(current_unit, {})
            continue

        if bold and current_unit and 5 < len(text) < 100:
            current_heading = text
            result[current_paper][current_unit].setdefault(current_heading, [])
            continue

        if current_heading and len(text) > 3:
            result[current_paper][current_unit][current_heading].append(text)

    return result
