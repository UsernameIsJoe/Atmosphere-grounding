#!/usr/bin/env python3
"""Stage 1A pilot: real Google-derived reviews -> clauses -> independent Ollama panel.

No human labels, no synthetic review inputs, no model self-verification.
Run --prepare-only first to inspect deterministic clause boundaries offline.
Outputs are provisional LLM-consensus-derived labels, not accuracy measurements.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ("calm", "inviting", "safe")
LABELS = ("supports", "opposes", "mixed", "not_relevant", "uncertain")
TYPES = ("explicit", "direct_indicator", "indirect")
STRENGTHS = ("weak", "strong")
ATTRIBUTIONS = ("first_person", "secondhand", "hedged", "general")
VERSION = "stage1a_clauses_panel_v1"
# Only split coordinating conjunctions at an explicit pause; no semantic rewrite.
BOUNDARY = re.compile(r"[.!?;]+(?=\s|$)|,(?=\s+(?:but|however|although|yet|while)\b)", re.I)
CLAUSE_SPLIT = re.compile(r"\s+(?:but|however|yet|whereas|while)\s+", re.I)

RUBRIC = {
    "calm": {
        "definition": "Reported tranquility, peacefulness, quiet, relaxation or their experienced opposites in the place.",
        "exclude": "Unrelated praise, food/service, a calm person without a place attribution; trees alone do not establish calm.",
        "hypothesis": "This place is experienced as calm and peaceful.",
    },
    "inviting": {
        "definition": "Reported welcome, approachability, social comfort or their experienced opposites at the place.",
        "exclude": "Generic positivity or accessibility facts alone do not establish felt welcome.",
        "hypothesis": "This place is experienced as inviting and welcoming.",
    },
    "safe": {
        "definition": "Reported feeling safe or unsafe at the place, distinguishing experiences from related environmental indicators.",
        "exclude": "Lighting, patrols, gates or sightlines alone do not prove felt safety; unrelated crime stories are not place experience.",
        "hypothesis": "People experience this place as safe.",
    },
}
RUBRIC_TEXT = "\n".join(
    f"{e}: {RUBRIC[e]['definition']} EXCLUDE: {RUBRIC[e]['exclude']}"
    for e in PILOT
)
PROMPTS = {
    "A": (
        "Annotate atmosphere evidence conservatively using the rubric. Label EACH numbered clause "
        "for EACH requested category. Read the FULL REVIEW to resolve context, negation and attribution. "
        "Use exact contiguous evidence spans from the numbered clause, NEVER paraphrases. "
        "distinguish explicit reported experience, direct factual indicators and indirect inferences. "
        "Generic praise, unrelated complaints and bare physical facts without an atmosphere connection "
        "are not_relevant. A physical feature is not automatically felt emotion. "
        "Use mixed only for contradictory evidence in the same clause; when needed supply multiple "
        "evidence_records for distinct conditioned observations. Respond ONLY with schema JSON."
    ),
    "B": (
        "For each specified category and clause, independently decide whether the writer gives "
        "place-attributed evidence, counterevidence, both, none, or an ambiguous case. Consider "
        "the original whole review before deciding. Copy one exact clause substring to justify each "
        "positive/negative result; never invent or paraphrase a source quote. Separate descriptions "
        "of how a place feels from reported environmental indicators and speculative associations. "
        "Don't infer experiences from trees, lamps or generic approval. Treat off-topic criticism as "
        "not_relevant. Multiple distinct observations within one clause may use evidence_records. "
        "Return a complete structured JSON response only."
    ),
}
# Controlled intervention: threshold clarification only, not a new taxonomy.
PROMPTS["C"] = (
    "For EACH requested emotion, decide independently whether this target clause "
    "provides place-attributed evidence about that emotion. Use the entire review "
    "ONLY to resolve reference, context, conditions and negation; quote evidence "
    "EXACTLY from the target clause. Separate four situations: "
    "(1) EXPLICIT experience: writer reports feeling calm, welcomed, safe or their opposites; "
    "(2) DIRECT INDICATOR: writer reports a concrete condition that directly bears on "
    "the category, such as slippery surfaces and collision risk for safe, a noisy "
    "environment for calm, or a hostile social interaction for inviting; "
    "(3) INDIRECT evidence: the described activity or experience has a clear, "
    "specific inferential connection to the category, even without an emotion word; "
    "(4) NOT RELEVANT: generic compliments, bare amenities, or features without "
    "a sufficiently specific connection. For example, shade alone does not establish "
    "calm, a gate alone does not establish felt safety, and a basketball court "
    "alone does not establish welcome. A reported intention to relax or socialize "
    "can count as indirect evidence for inviting, when anchored to this place. "
    "A reported concrete hazard can oppose safe as a direct indicator without "
    "proving that the writer felt unsafe. Use uncertain ONLY if there is a real "
    "ambiguous place-emotion connection, not just a lack of emotional words; "
    "otherwise choose not_relevant. Do not force evidence where none exists. "
    "Use mixed only when BOTH supporting and opposing evidence occur for the "
    "same emotion and clause. Cite exact contiguous evidence_span and label "
    "evidence type. Complete all JSON schema fields for every requested emotion."
)

ITEM_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "unit_id": {"type": "integer"},
        "emotion": {"type": "string", "enum": list(PILOT)},
        "relevance": {"type": "string", "enum": list(LABELS)},
        "strength": {"type": ["string", "null"], "enum": list(STRENGTHS) + [None]},
        "type": {"type": ["string", "null"], "enum": list(TYPES) + [None]},
        "condition": {"type": "string"},
        "evidence_span": {"type": "string"},
        "attribution": {"type": ["string", "null"], "enum": list(ATTRIBUTIONS) + [None]},
        "rationale": {"type": "string"},
        "evidence_records": {"type": "array", "items": {"type": "object", "additionalProperties": False, "properties": {
            "relevance": {"type": "string", "enum": ["supports", "opposes"]},
            "evidence_span": {"type": "string"},
            "strength": {"type": "string", "enum": list(STRENGTHS)},
            "type": {"type": "string", "enum": list(TYPES)},
            "condition": {"type": "string"},
        }, "required": ["relevance", "evidence_span", "strength", "type", "condition"]}},
    },
    "required": ["unit_id", "emotion", "relevance", "strength", "type", "condition",
                 "evidence_span", "attribution", "rationale", "evidence_records"],
}
SCHEMA = {"type": "object", "additionalProperties": False,
          "properties": {"labels": {"type": "array", "items": ITEM_SCHEMA}},
          "required": ["labels"]}


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def segment_review(text: str) -> list[dict]:
    """Deterministic contiguous clause candidates with ORIGINAL review offsets."""
    if not isinstance(text, str) or not text.strip():
        return []
    chunks = []
    cursor = 0
    for match in BOUNDARY.finditer(text):
        chunks.append((cursor, match.end()))
        cursor = match.end()
    if cursor < len(text):
        chunks.append((cursor, len(text)))
    units = []
    for lo, hi in chunks:
        piece = text[lo:hi]
        splits = [0] + [m.start() for m in CLAUSE_SPLIT.finditer(piece)] + [len(piece)]
        for j in range(len(splits) - 1):
            left = lo + splits[j]
            right = lo + splits[j + 1]
            while left < right and text[left].isspace():
                left += 1
            while right > left and text[right - 1].isspace():
                right -= 1
            if right > left:
                units.append({"unit_id": len(units), "start": left, "end": right,
                              "text": text[left:right]})
    assert all(text[u["start"]:u["end"]] == u["text"] for u in units)
    return units


def load_real_reviews(path: Path, max_reviews: int) -> list[dict]:
    if "fixtures" in path.parts:
        raise ValueError("Synthetic fixture paths are forbidden for research runs")
    if path.name != "reviews.jsonl":
        raise ValueError("Research input must be reviews.jsonl (not model-derived outputs)")
    rows = []
    with path.open(encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            pid = row.get("place_id", "")
            if (not isinstance(pid, str) or not pid.startswith("ChIJ")
                    or not isinstance(row.get("text"), str) or not row["text"].strip()
                    or not row.get("publish_time") or not isinstance(row.get("review_index"), int)):
                raise ValueError(f"Unverified or malformed real-review row at line {lineno}")
            rows.append(row)
            if max_reviews and len(rows) >= max_reviews:
                break
    seen = set()
    for row in rows:
        key = (row["place_id"], row["review_index"])
        if key in seen:
            raise ValueError(f"Duplicate source review key: {key}")
        seen.add(key)
    return rows


def prepare(rows: list[dict]) -> list[dict]:
    return [
        {"place_id": r["place_id"], "review_index": r["review_index"],
         "publish_time": r["publish_time"], "text": r["text"],
         "source_sha256": sha256(r["text"]), "units": segment_review(r["text"])}
        for r in rows
    ]


def validate_label(item: dict, unit: dict) -> dict:
    """Fail closed on schema violations, hallucinated quotations, invalid evidence type."""
    if not isinstance(item, dict) or set(item) != set(ITEM_SCHEMA["properties"]):
        raise ValueError("Unexpected or incomplete annotation keys")
    for k in ("condition", "evidence_span", "rationale"):
        if not isinstance(item[k], str):
            raise ValueError(f"Non-string {k}")
    if item["relevance"] not in LABELS or item["emotion"] not in PILOT:
        raise ValueError("Invalid relevance/emotion")
    if item["strength"] not in (*STRENGTHS, None) or item["type"] not in (*TYPES, None):
        raise ValueError("Invalid strength/evidence type")
    if item["attribution"] not in (*ATTRIBUTIONS, None):
        raise ValueError("Invalid attribution")
    span = item["evidence_span"]
    if item["relevance"] in ("supports", "opposes", "mixed"):
        if not span or span not in unit["text"] or item["type"] is None or item["strength"] is None:
            raise ValueError("Evidence-bearing label lacks exact source quote/type/strength")
    elif span and span not in unit["text"]:
        raise ValueError("Unmatched optional source quote")
    for record in item["evidence_records"]:
        if not isinstance(record, dict) or set(record) != {"relevance", "evidence_span", "strength", "type", "condition"}:
            raise ValueError("Invalid sub-evidence record")
        if (record["relevance"] not in ("supports", "opposes")
                or record["strength"] not in STRENGTHS or record["type"] not in TYPES
                or not isinstance(record["condition"], str)
                or not isinstance(record["evidence_span"], str)
                or not record["evidence_span"] or record["evidence_span"] not in unit["text"]):
            raise ValueError("Invalid or ungrounded sub-evidence")
    # Map exact source offsets; ambiguous duplicate substrings are recorded, not guessed.
    result = dict(item)
    result["span_offsets"] = all_offsets(unit, span)
    result["evidence_records"] = [
        {**x, "span_offsets": all_offsets(unit, x["evidence_span"])}
        for x in item["evidence_records"]
    ]
    return result


def all_offsets(unit: dict, span: str) -> list[dict]:
    if not span:
        return []
    positions = []
    at = 0
    while True:
        pos = unit["text"].find(span, at)
        if pos < 0:
            return positions
        positions.append({"start": unit["start"] + pos, "end": unit["start"] + pos + len(span)})
        at = pos + 1


def validate_response(result: dict, units: list[dict]) -> list[dict]:
    if not isinstance(result, dict) or set(result) != {"labels"} or not isinstance(result["labels"], list):
        raise ValueError("Wrong Ollama response envelope")
    expected = {(u["unit_id"], e) for u in units for e in PILOT}
    actual = []
    by_id = {u["unit_id"]: u for u in units}
    validated = []
    for item in result["labels"]:
        key = (item.get("unit_id"), item.get("emotion"))
        if key not in expected:
            raise ValueError("Annotation for unknown unit/emotion")
        actual.append(key)
        validated.append(validate_label(item, by_id[key[0]]))
    if len(actual) != len(expected) or set(actual) != expected:
        raise ValueError("Missing/duplicate unit × emotion judgments")
    return validated


def ollama_call(base: str, model: str, prompt_id: str, review: dict, timeout: int,
                trace_path: Path | None = None) -> dict:
    """Annotate one clause at a time, retrying category-by-category if needed.

    Full review always stays in context. Every original raw model response
    (including malformed ones) is preserved in a JSONL trace for audit.
    No repairs or fake labels are added to model predictions.
    """
    all_labels = []
    calls = []
    for unit in review["units"]:
        pending = list(PILOT)
        # First attempt: three labels for one clause. Fallback: one category per call.
        for categories in (list(PILOT),):
            labels = _request_labels(base, model, prompt_id, review, unit,
                                     categories, timeout, trace_path)
            if labels is not None:
                all_labels.extend(labels)
                pending = []
                break
        for category in pending:
            labels = _request_labels(base, model, prompt_id, review, unit,
                                     [category], timeout, trace_path)
            if labels is None:
                labels = _request_labels(base, model, prompt_id, review, unit,
                                         [category], timeout, trace_path,
                                         strict_retry=True)
            if labels is None:
                raise ValueError(
                    f"{model} {prompt_id} unit {unit['unit_id']} category {category} "
                    "failed even after single-category fallback; inspect raw_responses.jsonl")
            all_labels.extend(labels)
        calls.append({"unit_id": unit["unit_id"], "categories": list(PILOT)})
    if len(all_labels) != len(review["units"]) * len(PILOT):
        raise ValueError("Incomplete clause-level model response")
    return {"labels": all_labels, "model_response": {"model": model, "calls": calls}}


def _request_labels(base: str, model: str, prompt_id: str, review: dict,
                    unit: dict, categories: list[str], timeout: int,
                    trace_path: Path | None, strict_retry: bool = False) -> list[dict] | None:
    # Narrow schema explicitly to the requested category set.
    item_schema = json.loads(json.dumps(ITEM_SCHEMA))
    item_schema["properties"]["emotion"]["enum"] = categories
    schema = {"type": "object", "additionalProperties": False,
              "properties": {"labels": {"type": "array", "items": item_schema}},
              "required": ["labels"]}
    user = ("RUBRIC:\n"
            + "\n".join(f"{e}: {RUBRIC[e]['definition']} EXCLUDE: {RUBRIC[e]['exclude']}"
                        for e in categories)
            + "\nFULL ORIGINAL REVIEW:\n" + review["text"]
            + "\nSINGLE TARGET CLAUSE:\n" + json.dumps(unit, ensure_ascii=False)
            + "\nOUTPUT EXACTLY " + str(len(categories))
            + " labels in labels array, one for each of: " + ", ".join(categories)
            + ". Every label MUST have unit_id=" + str(unit["unit_id"])
            + '. For not_relevant or uncertain: evidence_span must be the empty STRING "" '
              '(never "[]", "null", or a quoted placeholder); condition must be ""; '
              'strength, type and attribution must be JSON null; evidence_records must be JSON []. '
              'Do not invent any evidence phrase. Rationale must be one short sentence.')
    payload = {"model": model,
               "messages": [{"role": "system", "content": PROMPTS[prompt_id]},
                            {"role": "user", "content": user}],
               "stream": False, "format": schema,
               "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2048}}
    if model.lower().startswith("qwen3:"):
        payload["think"] = False
    if strict_retry:
        # Changed prompt, not changed evidence: ask for the EXACT allowed JSON types.
        payload["messages"][0]["content"] += (
            ' STRICT OUTPUT RETRY: "evidence_span" MUST be an actual empty string '
            'for not_relevant/uncertain, not the literal characters [] or null. '
            'Use concise rationales. Do not repeat phrases or generate filler.')
        payload["options"]["num_predict"] = 1024
    request = urllib.request.Request(
        base.rstrip("/") + "/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.load(response)
    raw = body.get("message", {}).get("content", "")
    record = {"place_id": review["place_id"], "review_index": review["review_index"],
              "source_sha256": review["source_sha256"], "unit_id": unit["unit_id"],
              "model": model, "prompt": prompt_id, "categories": categories,
              "strict_retry": strict_retry,
              "raw_content": raw, "done_reason": body.get("done_reason"),
              "prompt_eval_count": body.get("prompt_eval_count"),
              "eval_count": body.get("eval_count")}
    try:
        # A single-unit validated response must include every requested category
        # exactly once, and must preserve exact source evidence quotes.
        parsed = json.loads(raw)
        if not isinstance(parsed, dict) or set(parsed) != {"labels"} or not isinstance(parsed["labels"], list):
            raise ValueError("Invalid response envelope")
        if len(parsed["labels"]) != len(categories):
            raise ValueError(f"Expected {len(categories)} labels, got {len(parsed['labels'])}")
        expected = {(unit["unit_id"], e) for e in categories}
        actual = [(v.get("unit_id"), v.get("emotion")) for v in parsed["labels"]]
        if set(actual) != expected or len(actual) != len(expected):
            raise ValueError("Missing or duplicate target unit/emotion")
        labels = [validate_label(v, unit) for v in parsed["labels"]]
        record["validation"] = "valid"
    except (json.JSONDecodeError, ValueError, TypeError, KeyError, AttributeError) as exc:
        record["validation"] = "invalid"
        record["error"] = str(exc)
        labels = None
        print(f"{model} {prompt_id} unit {unit['unit_id']} {','.join(categories)} "
              f"invalid ({exc})", flush=True)
    finally:
        if trace_path is not None:
            with trace_path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(record, ensure_ascii=False) + "\n")
    return labels


def aggregate(votes: list[dict]) -> dict:
    """Three A-prompt annotation votes, no confidence/truth interpretation."""
    if len(votes) != 3:
        raise ValueError("Consensus requires exactly three independent annotators")
    labels = [v["relevance"] for v in votes]
    counts = collections.Counter(labels)
    majority, size = counts.most_common(1)[0]
    winner = majority if size >= 2 else "contested"
    d = {label: counts[label] / 3 for label in LABELS}
    type_votes = [v["type"] for v in votes if v["relevance"] in ("supports", "opposes", "mixed")
                  and v["type"] in TYPES]
    type_counts = collections.Counter(type_votes)
    return {"label": winner, "votes": labels, "distribution": d,
            "agreement": size / 3, "contested": size < 2,
            "type_distribution_given_evidence": ({k: type_counts[k] / len(type_votes) for k in TYPES}
                                                  if type_votes else None),
            "ambiguous_multispan": any(len(v["span_offsets"]) > 1 or
                                        any(len(x["span_offsets"]) > 1 for x in v["evidence_records"])
                                        for v in votes)}


def summarize(annotations: list[dict], *, allow_incomplete: bool = False, prompt_id: str = "A") -> dict:
    """Panel consensus on complete three-model prompt-A items only."""
    groups = collections.defaultdict(dict)
    for r in annotations:
        if r["prompt"] != prompt_id:
            continue
        key = (r["place_id"], r["review_index"], r["unit_id"], r["emotion"])
        if r["model"] in groups[key]:
            raise ValueError(f"Duplicate annotation for {key}, {r['model']}")
        groups[key][r["model"]] = r
    splits = collections.Counter()
    pairs, total = collections.Counter(), collections.Counter()
    rates = collections.defaultdict(collections.Counter)
    outcomes, incomplete = [], []
    all_models = sorted({r["model"] for r in annotations})
    for key, by_model in sorted(groups.items()):
        if len(by_model) != 3:
            incomplete.append({"place_id": key[0], "review_index": key[1],
                               "unit_id": key[2], "emotion": key[3],
                               "available_models": sorted(by_model),
                               "missing_models": sorted(set(all_models) - set(by_model))})
            if allow_incomplete:
                continue
            raise ValueError(f"Missing one of three model votes: {key}")
        ordered = sorted(by_model)
        votes = [by_model[m] for m in ordered]
        labels = [v["relevance"] for v in votes]
        splits[str(len(set(labels)))] += 1
        for i, m in enumerate(ordered):
            rates[m][labels[i]] += 1
            for j in range(i + 1, 3):
                pair = m + " | " + ordered[j]
                total[pair] += 1
                pairs[pair] += (labels[i] == labels[j])
        outcomes.append({"place_id": key[0], "review_index": key[1], "unit_id": key[2],
                         "emotion": key[3], "by_model": {m: by_model[m] for m in ordered},
                         "consensus": aggregate(votes)})
    return {"n_items": len(outcomes), "n_incomplete_units": len(incomplete),
            "incomplete_units": incomplete, "label_diversity_counts": dict(splits),
            "pairwise_agreement": {k: pairs[k] / total[k] for k in sorted(total)},
            "per_model_label_counts": {m: dict(x) for m, x in rates.items()},
            "consensus": outcomes}


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def completed_model_calls(annotations: list[dict], reviews: list[dict],
                          models: list[str], prompts: tuple[str, ...] = ("A", "B")) -> set[tuple]:
    """Only skip a saved model/prompt/review if all its source-grounded labels are valid."""
    known = {(r["place_id"], r["review_index"]): r for r in reviews}
    by_call = collections.defaultdict(list)
    for item in annotations:
        key = (item["place_id"], item["review_index"])
        if key not in known or item["model"] not in models or item["prompt"] not in prompts:
            raise ValueError(f"Unexpected saved annotation: {key}")
        review = known[key]
        if item["source_sha256"] != review["source_sha256"]:
            raise ValueError(f"Saved review hash mismatch: {key}")
        unit = {u["unit_id"]: u for u in review["units"]}.get(item["unit_id"])
        if unit is None:
            raise ValueError(f"Saved annotation references unknown clause: {key}")
        # Stored labels have source-offset metadata added *after* the original
        # model schema validation, including nested evidence_records[].span_offsets.
        # Reconstruct the original schema before validating, without modifying
        # or weakening the previously saved source-grounding checks.
        base = {k: item[k] for k in ITEM_SCHEMA["properties"]}
        base["evidence_records"] = [
            {k: record[k] for k in ITEM_SCHEMA["properties"]["evidence_records"]["items"]["properties"]}
            for record in base["evidence_records"]
        ]
        validated = validate_label(base, unit)
        if item.get("span_offsets") != validated["span_offsets"]:
            raise ValueError(f"Saved primary evidence offsets mismatch: {key}")
        for stored, checked in zip(item["evidence_records"], validated["evidence_records"]):
            if stored.get("span_offsets") != checked["span_offsets"]:
                raise ValueError(f"Saved sub-evidence offsets mismatch: {key}")
        by_call[(key[0], key[1], item["model"], item["prompt"])].append(item)
    done = set()
    for call, items in by_call.items():
        review = known[(call[0], call[1])]
        expected = {(u["unit_id"], e) for u in review["units"] for e in PILOT}
        actual = [(v["unit_id"], v["emotion"]) for v in items]
        if len(actual) != len(expected) or set(actual) != expected:
            raise ValueError(f"Incomplete/duplicate saved annotations: {call}")
        done.add(call)
    return done


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=ROOT / "data/processed/reviews.jsonl")
    p.add_argument("--output", type=Path, default=ROOT / "reports/stage1a_panel_pilot")
    p.add_argument("--max-reviews", type=int, default=12, help="0 means all reviews")
    p.add_argument("--sample-mode", choices=["first", "diverse"], default="first",
                   help="diverse samples at most one review per place before cycling")
    p.add_argument("--prepare-only", action="store_true")
    p.add_argument("--prompt-ids", nargs="+", choices=sorted(PROMPTS), default=["A", "B"],
                   help="Run only selected prompts; C tests evidence thresholds")
    p.add_argument("--place-ids-file", type=Path,
                   help="JSON list of exact place IDs to select from the real corpus")
    p.add_argument("--resume", action="store_true", help="Retry only missing model/prompt/review calls")
    p.add_argument("--finalize-only", action="store_true", help="Summarize saved annotations without Ollama")
    p.add_argument("--models", nargs=3, default=["qwen3:8b", "gemma3:4b", "llama3.1:8b"],
                   metavar=("QWEN", "GEMMA", "LLAMA"))
    p.add_argument("--ollama-url", default="http://localhost:11434")
    p.add_argument("--timeout", type=int, default=240)
    args = p.parse_args()
    if args.max_reviews < 0:
        p.error("--max-reviews must be >= 0")
    if len(set(args.models)) != 3:
        p.error("Three distinct model tags are required")
    if len(set(args.prompt_ids)) != len(args.prompt_ids):
        p.error("--prompt-ids must not contain duplicates")
    rows = load_real_reviews(args.input, 0 if args.sample_mode == "diverse" or args.place_ids_file else args.max_reviews)
    if args.place_ids_file:
        ids = json.loads(args.place_ids_file.read_text(encoding="utf-8"))
        if not isinstance(ids, list) or not ids or not all(isinstance(x, str) and x.startswith("ChIJ") for x in ids):
            p.error("--place-ids-file must contain a nonempty JSON array of place IDs")
        if len(ids) != len(set(ids)):
            p.error("--place-ids-file contains duplicate IDs")
        # Match the original diverse-mode baseline: FIRST source review per place.
        # A dict comprehension would silently choose the LAST review (index 4),
        # invalidating controlled prompt comparisons against baseline index 0.
        first = {}
        for row in rows:
            if row["place_id"] in ids:
                first.setdefault(row["place_id"], row)
        if set(ids) != set(first):
            p.error("--place-ids-file references place IDs missing from input")
        rows = [first[pid] for pid in ids]
        if args.max_reviews and len(rows) != args.max_reviews:
            p.error("--max-reviews must equal selected place ID count")
    if args.sample_mode == "diverse" and not args.place_ids_file:
        by_place = collections.defaultdict(list)
        for row in rows:
            by_place[row["place_id"]].append(row)
        chosen = []
        while by_place and (not args.max_reviews or len(chosen) < args.max_reviews):
            for place_id in list(by_place):
                chosen.append(by_place[place_id].pop(0))
                if not by_place[place_id]:
                    del by_place[place_id]
                if args.max_reviews and len(chosen) >= args.max_reviews:
                    break
        rows = chosen
    reviews = prepare(rows)
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {"version": VERSION, "pilot_categories": list(PILOT),
                "full_taxonomy_count": 11, "input": str(args.input),
                "n_reviews": len(reviews), "n_places": len({x["place_id"] for x in reviews}),
                "n_clauses": sum(len(x["units"]) for x in reviews),
                "models": args.models, "prompt_ids": args.prompt_ids,
                "place_ids": [r["place_id"] for r in reviews],
                "prompts_sha256": {k: sha256(PROMPTS[k]) for k in args.prompt_ids},
                "rubric_sha256": sha256(RUBRIC_TEXT),
                "validation": "LLM agreement/fidelity only; no human labels",
                "run_mode": "prepare_only" if args.prepare_only else "ollama_panel",
                "sample_mode": args.sample_mode}
    manifest_path = args.output / "manifest.json"
    if args.resume or args.finalize_only:
        if not manifest_path.exists():
            p.error("Cannot resume: existing manifest.json not found")
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        for field in ("pilot_categories", "models", "n_reviews", "n_clauses",
                      "sample_mode", "prompt_ids", "place_ids", "prompts_sha256", "rubric_sha256"):
            if old.get(field) != manifest.get(field):
                p.error(f"Resume blocked: manifest field {field} differs")
        old_clauses = read_jsonl(args.output / "clauses.jsonl")
        if [(x["place_id"], x["review_index"], x["source_sha256"], x["units"])
            for x in old_clauses] != [
            (x["place_id"], x["review_index"], x["source_sha256"], x["units"])
            for x in reviews]:
            p.error("Resume blocked: review corpus or clause segmentation differs")
    else:
        if (args.output / "annotations.jsonl").exists():
            p.error("Existing annotations detected. Use --resume or another --output")
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        write_jsonl(args.output / "clauses.jsonl", reviews)
    print("Prepared", len(reviews), "real reviews, with", manifest["n_clauses"], "clauses")
    if args.prepare_only:
        print("Inspect", args.output / "clauses.jsonl")
        return
    outputs = read_jsonl(args.output / "annotations.jsonl") if (args.resume or args.finalize_only) else []
    done = completed_model_calls(outputs, reviews, args.models, tuple(args.prompt_ids))
    errors = []
    trace = args.output / "raw_responses.jsonl"
    if not args.finalize_only:
        for review in reviews:
            for model in args.models:
                for prompt in args.prompt_ids:
                    key = (review["place_id"], review["review_index"], model, prompt)
                    if key in done:
                        print(*key, "SKIP (already validated)", flush=True)
                        continue
                    try:
                        resp = ollama_call(args.ollama_url, model, prompt, review, args.timeout, trace)
                        for item in resp["labels"]:
                            outputs.append({**item, "place_id": review["place_id"],
                                            "review_index": review["review_index"],
                                            "source_sha256": review["source_sha256"],
                                            "model": model, "prompt": prompt,
                                            "model_response": resp["model_response"]})
                        done.add(key)
                        print(*key, "OK", flush=True)
                    except (ValueError, OSError, KeyError, TypeError) as exc:
                        errors.append({"place_id": review["place_id"], "review_index": review["review_index"],
                                       "model": model, "prompt": prompt, "error": str(exc)})
                        print(*key, "ERROR:", str(exc), flush=True)
                    write_jsonl(args.output / "annotations.jsonl", outputs)
                    write_jsonl(args.output / "errors.jsonl", errors)
    report = summarize(outputs, allow_incomplete=True, prompt_id=args.prompt_ids[0])
    write_jsonl(args.output / "consensus.jsonl", report.pop("consensus"))
    expected_calls = {(r["place_id"], r["review_index"], m, q)
                      for r in reviews for m in args.models for q in args.prompt_ids}
    missing = sorted(expected_calls - done)
    report["completed_requests"] = len(done)
    report["requested_requests"] = len(expected_calls)
    report["missing_requests"] = [
        {"place_id": x[0], "review_index": x[1], "model": x[2], "prompt": x[3]}
        for x in missing
    ]
    report["complete_panel"] = not missing
    (args.output / "diagnostics.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if missing:
        print(f"PARTIAL PANEL: {len(done)}/{len(expected_calls)} requests completed; "
              "consensus includes only complete three-model items.", flush=True)
        if not args.finalize_only:
            raise SystemExit("Missing requests remain. Use --resume on the same folder")
    else:
        print("Completed. Agreement is not semantic accuracy.")


if __name__ == "__main__":
    main()
