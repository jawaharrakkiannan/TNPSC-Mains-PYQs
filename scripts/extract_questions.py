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

_TESSERACT_CMD   = r"C:/Program Files/Tesseract-OCR/tesseract.exe"
_TESSDATA_PREFIX = os.path.expanduser("~")

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

# Math aptitude questions found in older exams (pre-2024); filter these out
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
    r"|cards?\s+drawn.*pack\s+of\s+52)"
    ,
    re.IGNORECASE,
)


def is_math_aptitude(english: str) -> bool:
    return bool(_MATH_APT_RE.search(english or ""))


def has_tamil(text: str) -> bool:
    return any("஀" <= c <= "௿" for c in text)


def _has_shree_font(doc) -> bool:
    for page in doc:
        for f in page.get_fonts():
            if "SHREE" in (f[3] or "").upper():
                return True
    return False


def _strip_shree_garbage(text: str) -> str:
    """Remove leading garbled Shree-TAM encoded chars, keeping ASCII English."""
    if not text:
        return text
    # Find first run of 3+ consecutive ASCII printable chars (start of English)
    m = re.search(r"[A-Za-z]{3}", text)
    if not m:
        return text
    # But don't strip if the whole text is already clean
    non_ascii = sum(1 for c in text if ord(c) > 0x7F)
    if non_ascii == 0:
        return text
    # Strip leading garbled block: find first word that is mostly ASCII
    parts = text.split()
    english_start = 0
    for i, word in enumerate(parts):
        ascii_ratio = sum(1 for c in word if ord(c) < 0x80) / max(len(word), 1)
        if ascii_ratio > 0.7 and len(word) > 2:
            english_start = i
            break
    return " ".join(parts[english_start:])


def _ocr_page_tamil(page) -> list[tuple[str, float]]:
    """Returns [(tamil_text, y_pdf), ...] for each Tamil text line on page."""
    import pytesseract
    from PIL import Image
    import io

    pytesseract.pytesseract.tesseract_cmd = _TESSERACT_CMD
    os.environ["TESSDATA_PREFIX"] = _TESSDATA_PREFIX

    scale = 2.5
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat)
    img = Image.open(io.BytesIO(pix.tobytes("png")))

    data = pytesseract.image_to_data(
        img, lang="tam+eng", output_type=pytesseract.Output.DICT
    )

    # Group words into lines
    line_map: dict[tuple, dict] = {}
    for i, word in enumerate(data["text"]):
        if not word.strip():
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        top = data["top"][i]
        ht  = data["height"][i]
        line_map.setdefault(key, {"words": [], "y": top + ht / 2})
        line_map[key]["words"].append(word)

    result: list[tuple[str, float]] = []
    for key in sorted(line_map):
        info = line_map[key]
        text = " ".join(info["words"])
        if has_tamil(text):
            result.append((text, info["y"] / scale))
    return result


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


_SEC_RE      = re.compile(r"SECTION\s*[-–—]\s*([A-C])", re.IGNORECASE)
_UNIT_NUM_RE = re.compile(r"UNIT\s*[-–—]\s*([IVX]+)",  re.IGNORECASE)
_UNIT_NM_RE  = re.compile(r"^\s*\(([A-Z][A-Z ,&/\-]+)\)\s*$")
_Q_NUM_RE    = re.compile(r"^\s*(\d+)\.\s+(.+)")


def extract_pattern_b(text: str, year: int, paper: str) -> list[dict]:
    questions: list[dict] = []
    current_section: str | None = None
    current_unit:    str | None = None
    current_unit_name: str | None = None
    current_marks: int | None = None
    current_wl:    int | None = None

    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        sec_m = _SEC_RE.search(line)
        if sec_m:
            current_section = sec_m.group(1).upper()
            instr = " ".join(lines[i:i + 8])
            current_marks, current_wl = parse_marks_and_wordlimit(instr)
            i += 1
            continue

        unit_m = _UNIT_NUM_RE.search(line)
        if unit_m:
            current_unit = unit_m.group(1).upper()
            current_unit_name = None
            i += 1
            continue

        name_m = _UNIT_NM_RE.match(line)
        if name_m and current_unit:
            current_unit_name = name_m.group(1).strip()
            i += 1
            continue

        q_m = _Q_NUM_RE.match(line)
        if q_m and current_section:
            q_num = int(q_m.group(1))
            raw = [q_m.group(2).strip()]
            j = i + 1
            while j < len(lines):
                nxt = lines[j].strip()
                if not nxt:
                    j += 1
                    continue
                if _Q_NUM_RE.match(nxt) or _SEC_RE.search(nxt) or _UNIT_NUM_RE.search(nxt):
                    break
                if not is_noise(nxt):
                    raw.append(nxt)
                j += 1
            tamil, english = split_bilingual("\n".join(raw))
            questions.append({
                "year": year, "paper": paper,
                "unit_number": current_unit, "unit_name": current_unit_name,
                "section": current_section, "question_number": q_num,
                "marks": current_marks, "word_limit": current_wl,
                "tamil": tamil, "english": english,
                "sub_questions": [], "noise_flagged": False,
            })
            i = j
            continue

        i += 1
    return questions


_PAGE_UNIT_RE = re.compile(r"UNIT\s*[-–—]\s*([IVX]+)", re.IGNORECASE)
_PAGE_SEC_RE  = re.compile(r"SECTION\s*[-–—]\s*([A-C])", re.IGNORECASE)

_QNUM_CELL_RE = re.compile(r"Q\.?\s*\n?No\.?\s*\n?(\d+)", re.IGNORECASE)


def extract_pattern_a_from_page(
    page,
    year: int,
    paper: str,
    current_unit: str | None,
    current_section: str | None,
    current_marks: int | None,
    current_word_limit: int | None,
    tamil_lines: list[tuple[str, float]] | None = None,
    page_y0: float = 0.0,
) -> list[dict]:
    questions: list[dict] = []
    page_height = page.rect.height

    # Collect all table rows with their bounding boxes for Tamil matching
    rows_with_bbox: list[tuple[int, float, str, str]] = []

    for table in page.find_tables():
        for row_idx, row in enumerate(table.extract()):
            if not row or len(row) < 2:
                continue
            qno_cell  = str(row[0] or "").strip()
            text_cell = str(row[1] or "").strip()
            m = _QNUM_CELL_RE.search(qno_cell)
            if not m:
                continue
            q_num = int(m.group(1))

            # Get row y-position for Tamil matching
            row_y = page_height * (0.1 + 0.8 * row_idx / max(len(table.extract()), 1))

            if tamil_lines is not None:
                tamil = _find_tamil_for_row(tamil_lines, row_y)
                english = _strip_shree_garbage(text_cell)
            else:
                tamil, english = split_bilingual(text_cell)

            rows_with_bbox.append((q_num, row_y, tamil, english))

    # Sort by question number and build question dicts
    for q_num, row_y, tamil, english in sorted(rows_with_bbox, key=lambda x: x[0]):
        questions.append({
            "year": year, "paper": paper,
            "unit_number": current_unit, "unit_name": None,
            "section": current_section, "question_number": q_num,
            "marks": current_marks, "word_limit": current_word_limit,
            "tamil": tamil, "english": english,
            "sub_questions": [], "noise_flagged": False,
        })
    return questions


def _find_tamil_for_row(tamil_lines: list[tuple[str, float]], row_y: float) -> str:
    """Find Tamil OCR lines near the given y-coordinate."""
    if not tamil_lines:
        return ""
    # Find lines within ±60 PDF units of row_y
    nearby = [text for text, y in tamil_lines if abs(y - row_y) < 60]
    return " ".join(nearby)


def extract_pdf(pdf_path: str, year: int, paper: str) -> list[dict]:
    doc = fitz.open(pdf_path)
    try:
        if year >= PATTERN_YEAR_CUTOFF:
            use_ocr = _has_shree_font(doc)
            return _extract_pattern_a_doc(doc, year, paper, use_ocr=use_ocr)
        full_text = "\n".join(page.get_text() for page in doc)
        return extract_pattern_b(full_text, year=year, paper=paper)
    finally:
        doc.close()


def _extract_pattern_a_doc(doc, year: int, paper: str, use_ocr: bool = False) -> list[dict]:
    questions: list[dict] = []
    current_unit    = current_section  = None
    current_marks   = current_word_limit = None

    for page_num, page in enumerate(doc):
        page_height = page.rect.height
        page_text = "\n".join(
            block[4]
            for block in page.get_text("blocks")
            if block[1] > page_height * 0.05 and block[3] < page_height * 0.90
            and block[6] == 0
        )
        um = _PAGE_UNIT_RE.search(page_text)
        if um:
            current_unit = um.group(1).upper()
        sm = _PAGE_SEC_RE.search(page_text)
        if sm:
            current_section = sm.group(1).upper()
            m, wl = parse_marks_and_wordlimit(page_text)
            if m:
                current_marks = m
            if wl:
                current_word_limit = wl

        # Also look for unit/section in OCR-friendly Tamil headers
        if current_unit is None or current_section is None:
            for pattern, field in [(_PAGE_UNIT_RE, "unit"), (_PAGE_SEC_RE, "section")]:
                pass  # already handled above

        tamil_lines = _ocr_page_tamil(page) if use_ocr else None

        questions.extend(extract_pattern_a_from_page(
            page, year, paper,
            current_unit, current_section,
            current_marks, current_word_limit,
            tamil_lines=tamil_lines,
        ))
    return questions


def flag_noise_questions(questions: list[dict]) -> list[dict]:
    for q in questions:
        if not q.get("english") and not q.get("tamil"):
            q["noise_flagged"] = True
        elif len(q.get("english", "")) < 10:
            q["noise_flagged"] = True
    return questions


def main(review: bool = False, years: list[int] | None = None) -> None:
    new_questions: list[dict] = []
    for paper, folder in PAPER_DIRS.items():
        if not os.path.isdir(folder):
            print(f"  Warning: {folder} not found, skipping", flush=True)
            continue
        pdfs = sorted(f for f in os.listdir(folder) if f.endswith(".pdf") and f[:-4].isdigit())
        if years:
            pdfs = [f for f in pdfs if int(f[:-4]) in years]
        print(f"\n[{paper}] {len(pdfs)} PDFs", flush=True)
        paper_total = 0
        for fname in pdfs:
            year = int(fname[:-4])
            pdf_path = os.path.join(folder, fname)
            print(f"  {year}...", end=" ", flush=True)
            try:
                qs = extract_pdf(pdf_path, year=year, paper=paper)
                before = len(qs)
                qs = [q for q in qs if not is_math_aptitude(q.get("english", ""))]
                if before != len(qs):
                    print(f"[filtered {before-len(qs)} math]", end=" ", flush=True)
                new_questions.extend(qs)
                paper_total += len(qs)
                print(f"{len(qs)} Qs", flush=True)
            except Exception as e:
                print(f"ERROR: {e}", flush=True)
        print(f"  -> {paper} subtotal: {paper_total}", flush=True)

    # When re-extracting specific years, merge with existing data for other years
    if years and os.path.exists(OUTPUT_PATH):
        years_set = set(years)
        with open(OUTPUT_PATH, encoding="utf-8") as f:
            existing = json.load(f)
        kept = [q for q in existing if q.get("year") not in years_set]
        all_questions = kept + new_questions
        print(f"\nMerged: kept {len(kept)} existing + {len(new_questions)} re-extracted = {len(all_questions)} total")
    else:
        all_questions = new_questions

    all_questions = flag_noise_questions(all_questions)
    flagged = sum(1 for q in all_questions if q["noise_flagged"])

    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_questions, f, ensure_ascii=False, indent=2)
    print(f"Written {len(all_questions)} questions ({flagged} flagged) to {OUTPUT_PATH}")

    if review and flagged:
        flagged_qs = [q for q in all_questions if q["noise_flagged"]]
        with open("data/review_flags.json", "w", encoding="utf-8") as f:
            json.dump(flagged_qs, f, ensure_ascii=False, indent=2)
        print(f"Flagged questions written to data/review_flags.json")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", action="store_true")
    ap.add_argument("--years", type=int, nargs="*", help="Only process these years")
    args = ap.parse_args()
    main(review=args.review, years=args.years)
