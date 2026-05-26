# scripts/extract_questions.py
import json
import os
import re
import sys
import fitz

OUTPUT_PATH = "data/questions_raw.json"
PAPER_DIRS = {
    "Paper I":   "Mains_PYQs/Paper-I",
    "Paper II":  "Mains_PYQs/Paper-II",
    "Paper III": "Mains_PYQs/Paper-III",
}
PATTERN_YEAR_CUTOFF = 2019

_NOISE_RE = re.compile(
    r"(\d{3,5}-\d{7,8})"
    r"|www\."
    r"|SHANKAR\s+IAS"
    r"|திருப்புக"
    r"|Turn\s+over"
    r"|^GS\d[A-Z]+/\d{2}$"
    r"|TNPSC\s+SPECIMEN",
    re.IGNORECASE | re.MULTILINE,
)
_MARKS_MAP  = {"three": 3, "five": 5, "ten": 10, "fifteen": 15, "twenty": 20}
_WORDS_RE   = re.compile(r"(\d+)\s+words", re.IGNORECASE)
_MARKS_RE   = re.compile(r"carries\s+(\w+)\s+marks", re.IGNORECASE)
_MARKS_N_RE = re.compile(r"[x×]\s*(\d+)\s*=", re.IGNORECASE)


def has_tamil(text: str) -> bool:
    return any("஀" <= c <= "௿" for c in text)


def split_bilingual(text: str) -> tuple[str, str]:
    if not text:
        return "", ""
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    tamil_lines: list[str] = []
    english_lines: list[str] = []
    for line in lines:
        if has_tamil(line):
            tamil_lines.append(line)
        else:
            english_lines.append(line)
    return " ".join(tamil_lines), " ".join(english_lines)


def is_noise(text: str) -> bool:
    text = text.strip()
    if re.match(r"^\d{1,3}$", text):
        return True
    return bool(_NOISE_RE.search(text))


def parse_marks_and_wordlimit(instr: str) -> tuple[int | None, int | None]:
    wm = _WORDS_RE.search(instr)
    mm = _MARKS_RE.search(instr)
    nm = _MARKS_N_RE.search(instr)
    word_limit = int(wm.group(1)) if wm else None
    marks = None
    if mm:
        marks = _MARKS_MAP.get(mm.group(1).lower())
    if marks is None and nm:
        marks = int(nm.group(1))
    return marks, word_limit
