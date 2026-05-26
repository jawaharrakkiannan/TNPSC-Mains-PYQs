# scripts/tag_questions.py
import json
import os
import re
import sys
import anthropic

INPUT_PATH    = "data/questions_corrected.json"
FALLBACK_PATH = "data/questions_raw.json"
SYLLABUS_PATH = "data/syllabus_themes.json"
OUTPUT_PATH   = "data/questions_tagged.json"


_BATCH_SIZE = 15


def form_batches(questions: list[dict]) -> list[dict]:
    bucket: dict[tuple, list] = {}
    for q in questions:
        key = (q["paper"], q.get("unit_number") or "unknown")
        bucket.setdefault(key, []).append(q)
    batches = []
    for (paper, unit), qs in bucket.items():
        for i in range(0, len(qs), _BATCH_SIZE):
            batches.append({"paper": paper, "unit_number": unit, "questions": qs[i:i + _BATCH_SIZE]})
    return batches


_ROMAN_VAL = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6}
_PAPER_OFFSET = 1  # question "Paper N" maps to syllabus "Paper N+1"


def _roman_num(text: str) -> int | None:
    m = re.search(r"\bPaper\s+([IVX]+)\b", text, re.IGNORECASE)
    if m:
        return _ROMAN_VAL.get(m.group(1).upper())
    return None


def _paper_matches(paper: str, p_key: str) -> bool:
    n1, n2 = _roman_num(paper), _roman_num(p_key)
    if n1 is not None and n2 is not None:
        return n1 + _PAPER_OFFSET == n2
    return paper.replace(" ", "").lower() == p_key.replace(" ", "").lower()


def _unit_matches(unit_number: str, u_key: str) -> bool:
    return bool(re.search(r"\bUnit\s+" + re.escape(unit_number.upper()) + r"\b", u_key, re.IGNORECASE))


def _syllabus_slice(syllabus: dict, paper: str, unit_number: str) -> dict:
    for p_key, units in syllabus.items():
        if _paper_matches(paper, p_key):
            for u_key, headings in units.items():
                if _unit_matches(unit_number, u_key):
                    return headings
    return {}


def _unit_full_name(syllabus: dict, paper: str, unit_number: str) -> str:
    for p_key, units in syllabus.items():
        if _paper_matches(paper, p_key):
            for u_key in units:
                if _unit_matches(unit_number, u_key):
                    return u_key
    return f"Unit {unit_number}"


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
                        return json.loads(raw[start : i + 1])
                    except json.JSONDecodeError:
                        break
    raise ValueError(f"LLM returned non-JSON for {context}: {raw[:300]!r}")


def tag_batch_with_llm(
    questions: list[dict],
    syllabus_slice: dict,
    paper: str,
    unit_number: str,
    client: anthropic.Anthropic,
) -> list[dict]:
    compact = json.dumps(
        {h: [kw for t in v.get("themes", []) for kw in t["keywords"]]
         for h, v in syllabus_slice.items()},
        ensure_ascii=False,
    )
    q_list = [{"question_number": q["question_number"], "english": q.get("english", "")}
              for q in questions]
    prompt = (
        f"You are tagging TNPSC exam questions to their syllabus topics.\n\n"
        f"Paper: {paper}, Unit {unit_number}\n"
        f"Syllabus (heading -> keywords):\n{compact}\n\n"
        f"Questions:\n{json.dumps(q_list, ensure_ascii=False)}\n\n"
        "For each question identify the closest heading, theme, and keyword.\n"
        'Return ONLY a JSON array: [{"question_number":N,"heading":"...","theme":"...","keyword":"..."}]'
    )
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.content[0].text.strip()
    return _extract_json_array(raw, f"{paper} Unit {unit_number}")


def merge_tags(questions: list[dict], tag_map: dict, syllabus: dict) -> list[dict]:
    for q in questions:
        key = (q["paper"], q.get("unit_number") or "unknown", q["question_number"])
        raw = tag_map.get(key, {})
        q["tags"] = {
            "paper":   q["paper"],
            "unit":    _unit_full_name(syllabus, q["paper"], q.get("unit_number") or ""),
            "heading": raw.get("heading", ""),
            "theme":   raw.get("theme", ""),
            "keyword": raw.get("keyword", ""),
        }
    return questions


def main() -> None:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    src = INPUT_PATH if os.path.exists(INPUT_PATH) else FALLBACK_PATH
    print(f"Loading questions from {src}...", flush=True)
    with open(src, encoding="utf-8") as f:
        questions = json.load(f)
    with open(SYLLABUS_PATH, encoding="utf-8") as f:
        syllabus = json.load(f)

    batches = form_batches(questions)
    print(f"{len(batches)} batches to tag", flush=True)
    tag_map: dict = {}

    for i, batch in enumerate(batches, 1):
        paper, unit = batch["paper"], batch["unit_number"]
        print(f"  [{i}/{len(batches)}] {paper} Unit {unit} ({len(batch['questions'])} Qs)...", end=" ", flush=True)
        sl = _syllabus_slice(syllabus, paper, unit)
        try:
            tags = tag_batch_with_llm(batch["questions"], sl, paper, unit, client)
            for t in tags:
                tag_map[(paper, unit, t["question_number"])] = t
            print("ok", flush=True)
        except Exception as e:
            print(f"ERROR: {e}", flush=True)

    tagged = merge_tags(questions, tag_map, syllabus)
    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(tagged, f, ensure_ascii=False, indent=2)
    print(f"Written to {OUTPUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
