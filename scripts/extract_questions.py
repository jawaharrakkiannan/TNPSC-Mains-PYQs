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
) -> list[dict]:
    questions: list[dict] = []
    for table in page.find_tables():
        for row in table.extract():
            if not row or len(row) < 2:
                continue
            qno_cell  = str(row[0] or "").strip()
            text_cell = str(row[1] or "").strip()
            m = _QNUM_CELL_RE.search(qno_cell)
            if not m:
                continue
            q_num = int(m.group(1))
            tamil, english = split_bilingual(text_cell)
            questions.append({
                "year": year, "paper": paper,
                "unit_number": current_unit, "unit_name": None,
                "section": current_section, "question_number": q_num,
                "marks": current_marks, "word_limit": current_word_limit,
                "tamil": tamil, "english": english,
                "sub_questions": [], "noise_flagged": False,
            })
    return questions


def extract_pdf(pdf_path: str, year: int, paper: str) -> list[dict]:
    doc = fitz.open(pdf_path)
    try:
        if year >= PATTERN_YEAR_CUTOFF:
            return _extract_pattern_a_doc(doc, year, paper)
        full_text = "\n".join(page.get_text() for page in doc)
        return extract_pattern_b(full_text, year=year, paper=paper)
    finally:
        doc.close()


def _extract_pattern_a_doc(doc, year: int, paper: str) -> list[dict]:
    questions: list[dict] = []
    current_unit    = current_section  = None
    current_marks   = current_word_limit = None

    for page in doc:
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
        questions.extend(extract_pattern_a_from_page(
            page, year, paper,
            current_unit, current_section,
            current_marks, current_word_limit,
        ))
    return questions


def flag_noise_questions(questions: list[dict]) -> list[dict]:
    for q in questions:
        if not q.get("english") and not q.get("tamil"):
            q["noise_flagged"] = True
        elif len(q.get("english", "")) < 10:
            q["noise_flagged"] = True
    return questions


def main(review: bool = False) -> None:
    all_questions: list[dict] = []
    for paper, folder in PAPER_DIRS.items():
        if not os.path.isdir(folder):
            print(f"  Warning: {folder} not found, skipping", flush=True)
            continue
        pdfs = sorted(f for f in os.listdir(folder) if f.endswith(".pdf") and f[:-4].isdigit())
        print(f"\n[{paper}] {len(pdfs)} PDFs found", flush=True)
        paper_total = 0
        for fname in pdfs:
            year = int(fname[:-4])
            pdf_path = os.path.join(folder, fname)
            print(f"  {year}...", end=" ", flush=True)
            try:
                qs = extract_pdf(pdf_path, year=year, paper=paper)
                all_questions.extend(qs)
                paper_total += len(qs)
                print(f"{len(qs)} Qs  (total so far: {len(all_questions)})", flush=True)
            except Exception as e:
                print(f"ERROR: {e}", flush=True)
        print(f"  -> {paper} subtotal: {paper_total} questions", flush=True)

    all_questions = flag_noise_questions(all_questions)
    flagged = sum(1 for q in all_questions if q["noise_flagged"])

    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_questions, f, ensure_ascii=False, indent=2)
    print(f"\nWritten {len(all_questions)} questions ({flagged} flagged) to {OUTPUT_PATH}")

    if review and flagged:
        flagged_qs = [q for q in all_questions if q["noise_flagged"]]
        with open("data/review_flags.json", "w", encoding="utf-8") as f:
            json.dump(flagged_qs, f, ensure_ascii=False, indent=2)
        print(f"Flagged questions written to data/review_flags.json")


if __name__ == "__main__":
    main(review="--review" in sys.argv)
