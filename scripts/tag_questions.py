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


def form_batches(questions: list[dict]) -> list[dict]:
    bucket: dict[tuple, list] = {}
    for q in questions:
        key = (q["paper"], q.get("unit_number") or "unknown")
        bucket.setdefault(key, []).append(q)
    return [
        {"paper": k[0], "unit_number": k[1], "questions": qs}
        for k, qs in bucket.items()
    ]


def _paper_matches(paper: str, p_key: str) -> bool:
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
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    try:
        return json.loads(resp.content[0].text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"LLM returned non-JSON for {paper} Unit {unit_number}: {resp.content[0].text!r}"
        ) from exc


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
