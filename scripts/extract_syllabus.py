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
    try:
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
    finally:
        doc.close()


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

        if current_unit and len(text) > 3 and not re.match(r'^(Page|\d+|of)$', text, re.IGNORECASE):
            effective_heading = current_heading or current_unit
            result[current_paper][current_unit].setdefault(effective_heading, [])
            result[current_paper][current_unit][effective_heading].append(text)

    return result


def group_keywords_with_llm(
    heading: str, keywords: list[str], client: anthropic.Anthropic
) -> list[dict]:
    prompt = (
        f"You are organising the TNPSC Group I Mains exam syllabus.\n\n"
        f"Heading: {heading}\n"
        f"Keywords: {json.dumps(keywords, ensure_ascii=False)}\n\n"
        "Group these keywords into 2-5 logical themes. Rules:\n"
        "- Every keyword must appear in exactly one theme\n"
        "- Theme names must be specific and domain-appropriate\n"
        "- Preserve logical flow — related topics stay together\n"
        "- IMPORTANT: Do not use double-quote characters inside string values; use single quotes instead\n"
        'Return ONLY a JSON array: [{"theme_name": "...", "keywords": [...]}]'
    )
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(
            f"LLM returned non-JSON for heading '{heading}': {raw!r}"
        ) from exc


def apply_themes_to_hierarchy(
    hierarchy: dict, client: anthropic.Anthropic
) -> dict:
    result: dict = {}
    for paper, units in hierarchy.items():
        result[paper] = {}
        for unit, headings in units.items():
            result[paper][unit] = {}
            for heading, keywords in headings.items():
                try:
                    themes = group_keywords_with_llm(heading, keywords, client)
                except ValueError as exc:
                    print(f"  WARNING: skipping heading '{heading}': {exc}", flush=True)
                    themes = []
                result[paper][unit][heading] = {"themes": themes}
    return result


def main() -> None:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    print("Extracting syllabus text blocks...")
    blocks = extract_text_blocks(SYLLABUS_PDF)
    print(f"  {len(blocks)} text spans")
    print("Parsing hierarchy...")
    hierarchy = parse_syllabus_hierarchy(blocks)
    print(f"  {len(hierarchy)} papers found")
    print("Grouping keywords via LLM...")
    themed = apply_themes_to_hierarchy(hierarchy, client)
    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(themed, f, ensure_ascii=False, indent=2)
    print(f"Written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
