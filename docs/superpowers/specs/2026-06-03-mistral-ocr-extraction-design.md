# Mistral OCR Extraction Pipeline — Design Spec

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `scripts/extract_questions.py` with a two-pass Mistral OCR pipeline that produces the same `questions_raw.json` schema with higher-quality Tamil and English extraction.

**Architecture:** Pass 1 sends each PDF to `mistral-ocr-2512` and caches the markdown response to disk. Pass 2 sends each cached markdown to `mistral-large-2512` with a structured extraction prompt and writes the merged `questions_raw.json`. The rest of the pipeline (tag_questions.py, generate_html.py) is unchanged.

**Tech Stack:** Python, `mistralai` SDK, `MISTRAL_API_KEY` in `.env`

---

## Context

Current extraction uses PyMuPDF text layer + Tesseract OCR (for Shree-TAM-0802 font PDFs, 2019+). Tamil extraction quality is inconsistent (64–95% coverage). Mistral OCR handles bilingual PDFs natively, eliminating the need for Tesseract and font-specific code paths.

Pipeline position: Step 2 of 4.

```
Step 1: extract_syllabus.py   → data/syllabus_themes.json
Step 2: extract_questions.py  → data/questions_raw.json      ← this redesign
Step 3: tag_questions.py      → data/questions_tagged.json   (untouched)
Step 4: generate_html.py      → output/viewer.html           (untouched)
```

---

## Output Schema

Each question in `questions_raw.json` must match this schema exactly:

```json
{
  "year": 2024,
  "paper": "Paper I",
  "unit_number": "I",
  "unit_name": null,
  "section": "A",
  "question_number": 10,
  "marks": 3,
  "word_limit": 30,
  "tamil": "தமிழ் உரை...",
  "english": "English question text...",
  "sub_questions": [],
  "noise_flagged": false
}
```

- `unit_number`: Roman numeral string ("I", "II", "III") or `null`
- `section`: "A", "B", or "C" or `null`
- `marks` / `word_limit`: integer or `null` (not empty string)
- `tamil`: Tamil Unicode text or `""` if absent
- `english`: English text
- `noise_flagged`: `true` if english is empty or < 10 chars

---

## Model Constants

```python
MISTRAL_OCR_MODEL   = "mistral-ocr-2512"
MISTRAL_PARSE_MODEL = "mistral-large-2512"
```

---

## Pass 1 — OCR (PDF → Markdown cache)

**Input:** `Mains_PYQs/Paper-{I,II,III}/{year}.pdf`
**Output:** `data/ocr_cache/Paper-I_2024.md` (one file per PDF)

Cache key: `data/ocr_cache/{paper.replace(' ', '-')}_{year}.md`
e.g. `Paper-I_2024.md`, `Paper-II_2019.md`

**Cache logic:**
- If cache file exists AND `--reocr` not set → read from cache, skip API call
- Otherwise → call Mistral OCR, write cache, continue

**API call:**
```python
import base64
from mistralai import Mistral

client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

with open(pdf_path, "rb") as f:
    pdf_b64 = base64.b64encode(f.read()).decode()

response = client.ocr.process(
    model=MISTRAL_OCR_MODEL,
    document={
        "type": "document_url",
        "document_url": f"data:application/pdf;base64,{pdf_b64}"
    }
)
markdown = "\n\n".join(page.markdown for page in response.pages)
```

**Error handling:** If API raises, print error and skip that PDF. Cache is only written on success.

---

## Pass 2 — Parse (Markdown → JSON questions)

**Input:** `data/ocr_cache/Paper-I_2024.md`
**Output:** list of question dicts (merged into `questions_raw.json`)

One API call per cached markdown file. Prompt:

```
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

After the LLM returns this array, the caller injects `year`, `paper`, `unit_name` (always null), `sub_questions` (always []), and `noise_flagged` (always false, set later by flag_noise_questions).

Rules:
- Preserve Tamil and English text verbatim, do not translate
- unit_number and section come from headers/section titles in the markdown
- marks and word_limit come from instruction lines (e.g. "carries three marks", "30 words")
- Use null (not empty string) for unknown integers
- Do NOT include answer text, only questions

Markdown:
{markdown}

Return ONLY a valid JSON array, no explanation.
```

**JSON extraction:** Use bracket-matching fallback (same as `_extract_json_array` in `tag_questions.py`) in case LLM wraps output in explanation text.

**Math filter:** After parsing, apply `_MATH_APT_RE` regex to drop math aptitude questions (same filter as current implementation).

**Noise flagging:** After parsing, set `noise_flagged=True` for questions where `english` is empty or < 10 chars.

**Error handling:** If parse API fails for one file, print error and skip. That year's questions will be absent from output but cache is preserved — cheap to retry with `--years`.

---

## --years Merge Logic

Preserved from current implementation:

```python
if years and os.path.exists(OUTPUT_PATH):
    years_set = set(years)
    with open(OUTPUT_PATH, encoding="utf-8") as f:
        existing = json.load(f)
    kept = [q for q in existing if q.get("year") not in years_set]
    all_questions = kept + new_questions
else:
    all_questions = new_questions
```

---

## CLI Interface

Identical to current:

```bash
python scripts/extract_questions.py                    # all PDFs
python scripts/extract_questions.py --years 2022       # specific years, use cache if exists
python scripts/extract_questions.py --years 2022 --reocr  # force re-OCR
```

---

## File Changes

| File | Action |
|------|--------|
| `scripts/extract_questions.py` | Rewrite entirely |
| `data/ocr_cache/` | New directory (created at runtime) |
| `.gitignore` | Add `data/ocr_cache/` |
| `.env` | Add `MISTRAL_API_KEY=...` (manual step) |

No other files changed.

---

## What Is Removed

- All PyMuPDF table extraction logic (`extract_pattern_a_from_page`, `_extract_pattern_a_doc`)
- All Tesseract OCR code (`_ocr_page_tamil`, `_TESSERACT_CMD`, `_TESSDATA_PREFIX`)
- Shree font detection (`_has_shree_font`, `_strip_shree_garbage`)
- Pattern B text extraction (`extract_pattern_b`)
- `split_bilingual`, `is_noise`, `has_tamil` utilities (no longer needed)
- `fitz` / `pytesseract` / `PIL` imports

`_MATH_APT_RE`, `is_math_aptitude`, `parse_marks_and_wordlimit`, `flag_noise_questions`, and `--years` merge logic are retained.
