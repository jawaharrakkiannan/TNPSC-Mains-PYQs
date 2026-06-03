# TNPSC Group I Mains PYQ Pipeline

Previous year questions (PYQs) for TNPSC Group I Mains exam — extracted from PDFs, syllabus-tagged via LLM, browsable via static HTML viewer.

## Dataset

- **967 questions** across 3 papers, 8 years (2013, 2015, 2016, 2017, 2019, 2023, 2024, 2025)
- Paper I: 291 Qs | Paper II: 364 Qs | Paper III: 312 Qs
- Math aptitude questions excluded (pre-2024 exams had a "General Aptitude and Mental Ability" section — not General Studies)

## Pipeline (run in order)

```bash
python scripts/extract_syllabus.py      # Step 1: syllabus → data/syllabus_themes.json
python scripts/extract_questions.py     # Step 2: PDFs  → data/questions_raw.json
python scripts/tag_questions.py         # Step 3: LLM tagging → data/questions_tagged.json
python scripts/generate_html.py         # Step 4: viewer → output/viewer.html
```

Orchestrator (runs all 4 steps):
```bash
python run_pipeline.py
```

Partial re-extraction (e.g. after adding new PDFs for specific years):
```bash
python scripts/extract_questions.py --years 2024 2025
python scripts/extract_questions.py --years 2022 --reocr  # force re-OCR even if cache exists
```

## Key Files

| Path | Purpose |
|------|---------|
| `Mains_PYQs/Paper-I/` | Source PDFs named `YYYY.pdf` |
| `Mains_PYQs/Paper-II/` | Source PDFs |
| `Mains_PYQs/Paper-III/` | Source PDFs |
| `Mains_PYQs/Group_I_Mains_Syllabus.pdf` | Official syllabus PDF |
| `data/syllabus_themes.json` | LLM-structured syllabus (paper→unit→heading→themes) |
| `data/ocr_cache/` | Mistral OCR markdown cache (one `.md` per PDF, gitignored) |
| `data/questions_raw.json` | Extracted questions (no tags) |
| `data/questions_tagged.json` | Questions with syllabus tags |
| `output/viewer.html` | Self-contained browsable viewer |
| `scripts/review_server.py` | Flask server for correcting extractions (port 5000) |

## Extraction (Step 2)

`extract_questions.py` uses a two-pass Mistral OCR approach for all PDFs:

**Pass 1 — OCR:** PDF → `mistral-ocr-2512` → markdown cached to `data/ocr_cache/Paper-I_YYYY.md`
- Cache is reused on subsequent runs; bypass with `--reocr`

**Pass 2 — Parse:** cached markdown → `mistral-large-2512` → question dicts
- LLM extracts both Tamil and English text, unit/section headers, marks/word limits

`MISTRAL_API_KEY` required (see Environment section below).

> **Previous approach** (PyMuPDF + Tesseract) removed. Tesseract is no longer needed.

## Syllabus Paper Numbering Offset

The syllabus PDF labels papers as Paper II, III, IV. The question PDF folders use Paper I, II, III. Offset = +1 (question "Paper N" → syllabus "Paper N+1"). Handled in `tag_questions.py::_paper_matches()`.

## Syllabus Structure

Syllabus papers:
- **Paper II** (= question Paper I): Modern History, Social Issues, Ethics
- **Paper III** (= question Paper II): Indian Polity, Science & Technology, Tamil Society
- **Paper IV** (= question Paper III): Geography, Environment, Indian Economy

## LLM Usage

`extract_questions.py` calls `mistral-ocr-2512` and `mistral-large-2512` via `MISTRAL_API_KEY`.

`extract_syllabus.py` and `tag_questions.py` call `claude-sonnet-4-6` via `ANTHROPIC_API_KEY`.

- Syllabus: groups raw keywords into themes per heading
- Tagging: assigns heading/theme/keyword per question using syllabus slice
- Batch size: 15 questions per LLM call to avoid token truncation
- JSON extraction uses bracket-matching fallback (LLM sometimes wraps JSON in explanation text)

## Viewer Features

Static HTML at `output/viewer.html`:
- **Cascading filters**: Paper → Unit → Theme → Keyword (selecting Paper filters Unit options, etc.)
- **Frequency tables**: Theme × Year and Keyword × Year cross-tabs
- Clicking a frequency cell filters to that theme/keyword + year
- Questions show Tamil text (if available) + English text + syllabus tags

## Review Server

```bash
python scripts/review_server.py
# → http://localhost:5000
```

Loads `data/questions_corrected.json` (falls back to `questions_raw.json`). Edits auto-save with 500ms debounce. Used to fix OCR extraction errors before re-tagging.

## Environment

Both keys required. Store in `.env` (no dotenv dependency — set env vars before running).

```
ANTHROPIC_API_KEY=sk-ant-...
MISTRAL_API_KEY=...
```

## Known Gaps

- **2022** not in dataset — PDFs exist (`Mains_PYQs/Paper-*/2022.pdf`) but not yet extracted. Run: `python scripts/extract_questions.py --years 2022`
- `tags.heading` for Paper III questions uses `(75 marks)` / `(100 marks)` as heading keys (PDF bold text artifact from the syllabus) — cosmetic issue only
