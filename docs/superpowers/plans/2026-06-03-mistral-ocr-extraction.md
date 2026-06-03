# Mistral OCR Extraction Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `scripts/extract_questions.py` with a two-pass Mistral OCR pipeline that produces the same `questions_raw.json` schema with better Tamil and English extraction.

**Architecture:** Pass 1 sends each PDF to `mistral-ocr-2512` and caches the markdown to `data/ocr_cache/`. Pass 2 sends cached markdown to `mistral-large-2512` with a structured prompt and writes `questions_raw.json`. `--years` re-extracts specific years and merges; `--reocr` forces Pass 1 to bypass cache.

**Tech Stack:** Python 3.11+, `mistralai` SDK, `pytest`, `unittest.mock`

---

## Codebase Context

This is a 4-step pipeline for TNPSC Group I Mains exam questions.

```
Step 1: extract_syllabus.py   → data/syllabus_themes.json
Step 2: extract_questions.py  → data/questions_raw.json      ← this rewrite
Step 3: tag_questions.py      → data/questions_tagged.json
Step 4: generate_html.py      → output/viewer.html
```

Source PDFs: `Mains_PYQs/Paper-{I,II,III}/{year}.pdf` (years: 2013,2015,2016,2017,2019,2022,2023,2024,2025).

`MISTRAL_API_KEY` must be set in environment (same pattern as existing `ANTHROPIC_API_KEY` — no dotenv dependency; user sets env var before running).

**Existing test file** `tests/test_extract_questions.py` imports functions that will be deleted (`has_tamil`, `split_bilingual`, `is_noise`, `extract_pattern_b`, `extract_pattern_a_from_page`, `extract_pdf`). It must be replaced entirely.

**Functions retained from old implementation:**
- `is_math_aptitude` / `_MATH_APT_RE` — same regex
- `parse_marks_and_wordlimit` — same logic
- `flag_noise_questions` — same logic

---

## File Structure

| File | Action |
|------|--------|
| `scripts/extract_questions.py` | Complete rewrite |
| `tests/test_extract_questions.py` | Complete replacement |
| `requirements.txt` | Add `mistralai>=1.0.0` |
| `.gitignore` | Add `data/ocr_cache/` |

---

## Task 1: Dependencies & .gitignore

**Files:**
- Modify: `requirements.txt`
- Modify: `.gitignore`

- [ ] **Step 1: Add mistralai to requirements.txt**

Replace the contents of `requirements.txt` with:

```
pymupdf>=1.24.0
flask>=3.0.0
anthropic>=0.40.0
mistralai>=1.0.0
pytest>=8.0.0
pytest-flask>=1.3.0
```

- [ ] **Step 2: Install the new dependency**

Run: `pip install mistralai`
Expected: Successfully installed (or already satisfied)

- [ ] **Step 3: Add ocr_cache to .gitignore**

Replace the contents of `.gitignore` with:

```
data/*.json
data/ocr_cache/
output/
__pycache__/
*.pyc
.env
.pytest_cache/
```

- [ ] **Step 4: Commit**

```bash
git add requirements.txt .gitignore
git commit -m "chore: add mistralai dep, ignore ocr_cache dir"
```

---

## Task 2: Utility Functions (TDD)

**Files:**
- Create: `scripts/extract_questions.py` (new skeleton + utilities)
- Create: `tests/test_extract_questions.py` (replaces old file)

- [ ] **Step 1: Write failing tests for utility functions**

Replace the entire content of `tests/test_extract_questions.py` with:

```python
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
```

- [ ] **Step 2: Run tests to verify they all fail**

Run: `pytest tests/test_extract_questions.py -v`
Expected: All tests FAIL with `ImportError` or `ModuleNotFoundError` since the functions don't exist yet.

- [ ] **Step 3: Write new extract_questions.py with utility functions**

Create `scripts/extract_questions.py` with this content:

```python
# scripts/extract_questions.py
import argparse
import base64
import json
import os
import re

from mistralai import Mistral

OUTPUT_PATH   = "data/questions_raw.json"
OCR_CACHE_DIR = "data/ocr_cache"
PAPER_DIRS    = {
    "Paper I":   "Mains_PYQs/Paper-I",
    "Paper II":  "Mains_PYQs/Paper-II",
    "Paper III": "Mains_PYQs/Paper-III",
}
MISTRAL_OCR_MODEL   = "mistral-ocr-2512"
MISTRAL_PARSE_MODEL = "mistral-large-2512"

_MARKS_MAP  = {"three": 3, "five": 5, "ten": 10, "fifteen": 15, "twenty": 20}
_WORDS_RE   = re.compile(r"(\d+)\s+words", re.IGNORECASE)
_MARKS_RE   = re.compile(r"carries\s+(\w+)\s+marks", re.IGNORECASE)
_MARKS_N_RE = re.compile(r"[x×]\s*(\d+)\s*=", re.IGNORECASE)

_MATH_APT_RE = re.compile(
    r"(litres?\s+of\s+(milk|water)"
    r"|balls?\s+(in|contains?)"
    r"|probability\s+(to\s+get|that)"
    r"|(dice|die)\s+(are\s+rolled|rolled\s+once)"
    r"|profit.*loss|loss.*profit"
    r"|selling\s+price|cost\s+price"
    r"|gained?\s+\d+\s*percent"
    r"|rupees?\s+each\s+gain"
    r"|coins.*ratio.*rupees?"
    r"|simple\s+interest.*double"
    r"|compound\s+interest.*bank"
    r"|diagonal.*cm.*perimeter"
    r"|perimeter.*cm.*area"
    r"|circular\s+(pool|swimming)"
    r"|equilateral\s+triangle.*diagonal"
    r"|revolutions\s+per\s+minute.*diameter"
    r"|rate\s+percent.*simple\s+interest"
    r"|slant\s+height.*cone"
    r"|fair\s+dice.*probability"
    r"|leap\s+year.*probability"
    r"|cards?\s+drawn.*pack\s+of\s+52)",
    re.IGNORECASE,
)

_PARSE_PROMPT = """\
You are extracting exam questions from a TNPSC Group I Mains paper OCR output.

Paper: {paper}, Year: {year}

The markdown below contains bilingual questions (Tamil + English).
Extract every question and return a JSON array.

Each object must have exactly these fields:
- question_number: integer
- unit_number: Roman numeral string ("I"/"II"/"III") or null
- section: "A", "B", or "C" or null
- marks: integer or null
- word_limit: integer or null
- tamil: Tamil text string (empty string "" if absent)
- english: English question text string

Rules:
- Preserve Tamil and English text verbatim, do not translate
- unit_number and section come from section/unit headers in the markdown
- marks and word_limit come from instruction lines (e.g. "carries three marks", "30 words")
- Use null (not empty string) for unknown integers
- Do NOT include answer text, only questions

Markdown:
{markdown}

Return ONLY a valid JSON array, no explanation."""


def is_math_aptitude(english: str) -> bool:
    return bool(_MATH_APT_RE.search(english or ""))


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


def flag_noise_questions(questions: list[dict]) -> list[dict]:
    for q in questions:
        if not q.get("english") or len(q.get("english", "")) < 10:
            q["noise_flagged"] = True
    return questions


def _extract_json_array(raw: str, context: str) -> list:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    start = raw.find("[")
    if start != -1:
        depth = 0
        in_str = False
        escape = False
        for i, c in enumerate(raw[start:], start):
            if escape:
                escape = False
                continue
            if c == "\\" and in_str:
                escape = True
                continue
            if c == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(raw[start: i + 1])
                    except json.JSONDecodeError:
                        break
    raise ValueError(f"LLM returned non-JSON for {context}: {raw[:300]!r}")


def _cache_path(paper: str, year: int) -> str:
    return os.path.join(OCR_CACHE_DIR, f"{paper.replace(' ', '-')}_{year}.md")


def call_mistral_ocr(pdf_path: str, client: Mistral) -> str:
    raise NotImplementedError


def get_or_create_ocr_cache(
    paper: str, year: int, pdf_path: str, client: Mistral, reocr: bool = False
) -> str:
    raise NotImplementedError


def parse_markdown_to_questions(
    markdown: str, paper: str, year: int, client: Mistral
) -> list[dict]:
    raise NotImplementedError


def main(years: list[int] | None = None, reocr: bool = False) -> None:
    raise NotImplementedError


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, nargs="*")
    ap.add_argument("--reocr", action="store_true")
    args = ap.parse_args()
    main(years=args.years, reocr=args.reocr)
```

- [ ] **Step 4: Run tests to verify utility tests pass**

Run: `pytest tests/test_extract_questions.py -v`
Expected: All 14 utility tests PASS. No `NotImplementedError` — main/OCR/parse tests not written yet.

- [ ] **Step 5: Commit**

```bash
git add scripts/extract_questions.py tests/test_extract_questions.py
git commit -m "feat: scaffold new extract_questions with utility functions"
```

---

## Task 3: Pass 1 — OCR Functions (TDD)

**Files:**
- Modify: `scripts/extract_questions.py` (implement `call_mistral_ocr`, `get_or_create_ocr_cache`)
- Modify: `tests/test_extract_questions.py` (add OCR tests)

- [ ] **Step 1: Add failing OCR tests to test file**

Append these tests to `tests/test_extract_questions.py`:

```python
# --- OCR Pass ---

import os
import tempfile
from unittest.mock import MagicMock, patch, mock_open
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
```

- [ ] **Step 2: Run tests to verify new OCR tests fail**

Run: `pytest tests/test_extract_questions.py -k "ocr or cache" -v`
Expected: All 5 OCR tests FAIL with `NotImplementedError`.

- [ ] **Step 3: Implement call_mistral_ocr and get_or_create_ocr_cache**

In `scripts/extract_questions.py`, replace the two stub functions with:

```python
def call_mistral_ocr(pdf_path: str, client: Mistral) -> str:
    with open(pdf_path, "rb") as f:
        pdf_b64 = base64.b64encode(f.read()).decode()
    response = client.ocr.process(
        model=MISTRAL_OCR_MODEL,
        document={
            "type": "document_url",
            "document_url": f"data:application/pdf;base64,{pdf_b64}",
        },
    )
    return "\n\n".join(page.markdown for page in response.pages)


def get_or_create_ocr_cache(
    paper: str, year: int, pdf_path: str, client: Mistral, reocr: bool = False
) -> str:
    path = _cache_path(paper, year)
    if os.path.exists(path) and not reocr:
        with open(path, encoding="utf-8") as f:
            return f.read()
    markdown = call_mistral_ocr(pdf_path, client)
    os.makedirs(OCR_CACHE_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(markdown)
    return markdown
```

- [ ] **Step 4: Run tests to verify OCR tests pass**

Run: `pytest tests/test_extract_questions.py -v`
Expected: All 19 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/extract_questions.py tests/test_extract_questions.py
git commit -m "feat: implement OCR pass with markdown cache"
```

---

## Task 4: Pass 2 — Parse Markdown → Questions (TDD)

**Files:**
- Modify: `scripts/extract_questions.py` (implement `parse_markdown_to_questions`)
- Modify: `tests/test_extract_questions.py` (add parse tests)

- [ ] **Step 1: Add failing parse tests to test file**

Append these tests to `tests/test_extract_questions.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify new parse tests fail**

Run: `pytest tests/test_extract_questions.py -k "parse" -v`
Expected: All 6 parse tests FAIL with `NotImplementedError`.

- [ ] **Step 3: Implement parse_markdown_to_questions**

In `scripts/extract_questions.py`, replace the stub with:

```python
def parse_markdown_to_questions(
    markdown: str, paper: str, year: int, client: Mistral
) -> list[dict]:
    prompt = _PARSE_PROMPT.format(paper=paper, year=year, markdown=markdown)
    resp = client.chat.complete(
        model=MISTRAL_PARSE_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.choices[0].message.content.strip()
    items = _extract_json_array(raw, f"{paper} {year}")
    return [
        {
            "year":            year,
            "paper":           paper,
            "unit_number":     item.get("unit_number"),
            "unit_name":       None,
            "section":         item.get("section"),
            "question_number": item.get("question_number"),
            "marks":           item.get("marks"),
            "word_limit":      item.get("word_limit"),
            "tamil":           item.get("tamil", ""),
            "english":         item.get("english", ""),
            "sub_questions":   [],
            "noise_flagged":   False,
        }
        for item in items
    ]
```

- [ ] **Step 4: Run full test suite to verify all pass**

Run: `pytest tests/test_extract_questions.py -v`
Expected: All 25 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/extract_questions.py tests/test_extract_questions.py
git commit -m "feat: implement parse pass — markdown to question dicts"
```

---

## Task 5: Main Function & Full Wiring

**Files:**
- Modify: `scripts/extract_questions.py` (implement `main`)

- [ ] **Step 1: Implement main()**

In `scripts/extract_questions.py`, replace the `main` stub with:

```python
def main(years: list[int] | None = None, reocr: bool = False) -> None:
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
    new_questions: list[dict] = []

    for paper, folder in PAPER_DIRS.items():
        if not os.path.isdir(folder):
            print(f"  Warning: {folder} not found, skipping", flush=True)
            continue
        pdfs = sorted(
            f for f in os.listdir(folder)
            if f.endswith(".pdf") and f[:-4].isdigit()
        )
        if years:
            pdfs = [f for f in pdfs if int(f[:-4]) in years]
        print(f"\n[{paper}] {len(pdfs)} PDFs", flush=True)
        for fname in pdfs:
            year = int(fname[:-4])
            pdf_path = os.path.join(folder, fname)
            print(f"  {year}...", end=" ", flush=True)
            try:
                markdown = get_or_create_ocr_cache(paper, year, pdf_path, client, reocr)
                qs = parse_markdown_to_questions(markdown, paper, year, client)
                before = len(qs)
                qs = [q for q in qs if not is_math_aptitude(q.get("english", ""))]
                if before != len(qs):
                    print(f"[filtered {before - len(qs)} math]", end=" ", flush=True)
                new_questions.extend(qs)
                print(f"{len(qs)} Qs", flush=True)
            except Exception as e:
                print(f"ERROR: {e}", flush=True)

    if years and os.path.exists(OUTPUT_PATH):
        years_set = set(years)
        with open(OUTPUT_PATH, encoding="utf-8") as f:
            existing = json.load(f)
        kept = [q for q in existing if q.get("year") not in years_set]
        all_questions = kept + new_questions
        print(f"\nMerged: kept {len(kept)} + {len(new_questions)} new = {len(all_questions)} total")
    else:
        all_questions = new_questions

    all_questions = flag_noise_questions(all_questions)
    flagged = sum(1 for q in all_questions if q["noise_flagged"])

    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_questions, f, ensure_ascii=False, indent=2)
    print(f"Written {len(all_questions)} questions ({flagged} flagged) to {OUTPUT_PATH}")
```

- [ ] **Step 2: Run full test suite one more time**

Run: `pytest tests/test_extract_questions.py -v`
Expected: All 25 tests PASS. No regressions.

- [ ] **Step 3: Verify CLI help works**

Run: `python scripts/extract_questions.py --help`
Expected output contains:
```
usage: extract_questions.py [-h] [--years [YEARS ...]] [--reocr]
```

- [ ] **Step 4: Run the other test suites to check for regressions**

Run: `pytest tests/ -v --ignore=tests/test_extract_questions.py`
Expected: All other tests PASS (tag_questions, extract_syllabus, generate_html, review_server).

- [ ] **Step 5: Commit**

```bash
git add scripts/extract_questions.py
git commit -m "feat: implement main() — full two-pass Mistral OCR extraction pipeline"
```

---

## Task 6: Smoke Test Against a Real PDF

This task requires `MISTRAL_API_KEY` set in the environment and a real PDF on disk.

- [ ] **Step 1: Set MISTRAL_API_KEY**

Make sure the key is set. If it's in `.env`, source it:
```bash
# Windows PowerShell:
$env:MISTRAL_API_KEY = "sk-..."
# Or if .env file exists, read it:
# Get-Content .env | ForEach-Object { if ($_ -match '^([^#][^=]*)=(.*)$') { [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim()) } }
```

- [ ] **Step 2: Run extraction for one year**

Run: `python scripts/extract_questions.py --years 2025`
Expected:
```
[Paper I] 1 PDFs
  2025... N Qs

[Paper II] 1 PDFs
  2025... N Qs

[Paper III] 1 PDFs
  2025... N Qs

Written N questions (M flagged) to data/questions_raw.json
```
- N >= 20 for each paper
- `data/ocr_cache/Paper-I_2025.md`, `Paper-II_2025.md`, `Paper-III_2025.md` created

- [ ] **Step 3: Verify output schema**

Run this Python snippet to validate the output:
```python
import json
with open("data/questions_raw.json") as f:
    qs = json.load(f)
year_qs = [q for q in qs if q["year"] == 2025]
print(f"2025 questions: {len(year_qs)}")
print("First question:", json.dumps(year_qs[0], ensure_ascii=False, indent=2))

required_keys = {"year","paper","unit_number","unit_name","section","question_number",
                 "marks","word_limit","tamil","english","sub_questions","noise_flagged"}
missing = [k for q in year_qs for k in required_keys if k not in q]
print("Schema violations:", missing or "none")
```
Expected: Schema violations = none; Tamil text visible in `tamil` field.

- [ ] **Step 4: Re-run uses cache (verify no extra OCR calls)**

Run: `python scripts/extract_questions.py --years 2025`
Expected: Same output, completes faster (cache hit — no OCR API call). Cache files not modified (check timestamps).

- [ ] **Step 5: Test --reocr flag**

Run: `python scripts/extract_questions.py --years 2025 --reocr`
Expected: Makes fresh OCR API call (takes longer), overwrites cache files.

- [ ] **Step 6: Commit**

```bash
git add scripts/extract_questions.py tests/test_extract_questions.py
git commit -m "test: verify smoke test passes for 2025 extraction"
```
