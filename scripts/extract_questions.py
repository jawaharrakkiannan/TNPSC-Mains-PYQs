# scripts/extract_questions.py
import argparse
import base64
import json
import os
import re

from mistralai.client import Mistral

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
    r"|profit.*loss|loss.*profit|profit\s+of\s+\d+\s*percent"
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
    return f"{OCR_CACHE_DIR}/{paper.replace(' ', '-')}_{year}.md"


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
    if not response.pages:
        raise ValueError(f"Mistral OCR returned no pages for {pdf_path}")
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
