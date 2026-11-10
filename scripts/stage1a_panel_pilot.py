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
                max_units_per_call: int = 2) -> dict:
    """Batch clause IDs in small requests while retaining the FULL review as context.

    Fail closed: never accept a truncated JSON response, missing labels or invented spans.
    """
    if max_units_per_call < 1:
        raise ValueError("max_units_per_call must be positive")
    all_labels = []
    call_metadata = []
    units = review["units"]
    for start in range(0, len(units), max_units_per_call):
        batch = units[start:start + max_units_per_call]
        user = ("RUBRIC:\n" + RUBRIC_TEXT + "\nFULL ORIGINAL REVIEW:\n"
                + review["text"] + "\nTARGET CLAUSES (only label these IDs):\n"
                + json.dumps(batch, ensure_ascii=False)
                + "\nReturn exactly one label for each target clause x " + ", ".join(PILOT) + ".")
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": PROMPTS[prompt_id]},
                         {"role": "user", "content": user}],
            "stream": False, "format": SCHEMA,
            "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 3072}
        }
        if model.lower().startswith("qwen3:"):
            payload["think"] = False
        req = urllib.request.Request(base.rstrip("/") + "/api/chat",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        # At most two tries: first full JSON schema, then same small batch with larger output cap.
        for attempt in range(2):
            if attempt:
                payload["options"]["num_predict"] = 6144
                req = urllib.request.Request(base.rstrip("/") + "/api/chat",
                    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                    headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = json.load(response)
            raw = body.get("message", {}).get("content", "")
            try:
                labels = validate_response(json.loads(raw), batch)
            except (json.JSONDecodeError, ValueError, TypeError) as exc:
                if attempt == 0:
                    print(f"{model} {prompt_id} units {start}:{start + len(batch)} "
                          f"JSON/schema invalid ({exc}); retrying batch", flush=True)
                    continue
                raise ValueError(
                    f"{model} {prompt_id} units {start}:{start + len(batch)} "
                    f"invalid JSON/schema after retry; done_reason={body.get('done_reason')}, "
                    f"content_length={len(raw)}; error={exc}") from exc
            all_labels.extend(labels)
            call_metadata.append({
                "model": body.get("model"), "done_reason": body.get("done_reason"),
                "prompt_eval_count": body.get("prompt_eval_count"),
                "eval_count": body.get("eval_count"),
                "batch_unit_ids": [u["unit_id"] for u in batch], "attempts": attempt + 1
            })
            break
    if len(all_labels) != len(units) * len(PILOT):
        raise ValueError("Incomplete batched annotation; no partial labels accepted")
    return {"labels": all_labels, "model_response": {"calls": call_metadata}}


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


def summarize(annotations: list[dict]) -> dict:
    """Diagnostics only: pairwise agreement and split patterns, never accuracy."""
    groups = collections.defaultdict(dict)
    for r in annotations:
        if r["prompt"] == "A":
            groups[(r["place_id"], r["review_index"], r["unit_id"], r["emotion"])][r["model"]] = r
    splits = collections.Counter()
    pairs = collections.Counter()
    total = collections.Counter()
    rates = collections.defaultdict(collections.Counter)
    outcomes = []
    for key, by_model in sorted(groups.items()):
        if len(by_model) != 3:
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
    return {"n_items": len(outcomes), "label_diversity_counts": dict(splits),
            "pairwise_agreement": {k: pairs[k] / total[k] for k in sorted(total)},
            "per_model_label_counts": {m: dict(x) for m, x in rates.items()},
            "consensus": outcomes}


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
    p.add_argument("--models", nargs=3, default=["qwen3:8b", "gemma3:4b", "llama3.1:8b"],
                   metavar=("QWEN", "GEMMA", "LLAMA"))
    p.add_argument("--ollama-url", default="http://localhost:11434")
    p.add_argument("--timeout", type=int, default=240)
    args = p.parse_args()
    if args.max_reviews < 0:
        p.error("--max-reviews must be >= 0")
    if len(set(args.models)) != 3:
        p.error("Three distinct model tags are required")
    rows = load_real_reviews(args.input, 0 if args.sample_mode == "diverse" else args.max_reviews)
    if args.sample_mode == "diverse":
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
                "models": args.models, "prompts_sha256": {k: sha256(v) for k, v in PROMPTS.items()},
                "rubric_sha256": sha256(RUBRIC_TEXT),
                "validation": "LLM agreement/fidelity only; no human labels",
                "run_mode": "prepare_only" if args.prepare_only else "ollama_panel",
                "sample_mode": args.sample_mode}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_jsonl(args.output / "clauses.jsonl", reviews)
    print("Prepared", len(reviews), "real reviews, with", manifest["n_clauses"], "clauses")
    if args.prepare_only:
        print("Inspect", args.output / "clauses.jsonl")
        return
    outputs = []
    errors = []
    for review in reviews:
        for model in args.models:
            for prompt in ("A", "B"):
                try:
                    resp = ollama_call(args.ollama_url, model, prompt, review, args.timeout)
                    for item in resp["labels"]:
                        outputs.append({**item, "place_id": review["place_id"],
                                        "review_index": review["review_index"],
                                        "source_sha256": review["source_sha256"],
                                        "model": model, "prompt": prompt,
                                        "model_response": resp["model_response"]})
                    print(review["place_id"], review["review_index"], model, prompt, "OK", flush=True)
                except (ValueError, OSError, KeyError, TypeError) as exc:
                    errors.append({"place_id": review["place_id"], "review_index": review["review_index"],
                                   "model": model, "prompt": prompt, "error": str(exc)})
                    print(review["place_id"], review["review_index"], model, prompt,
                          "ERROR:", str(exc), flush=True)
                # Save incremental results so a failed or interrupted panel remains inspectable.
                write_jsonl(args.output / "annotations.jsonl", outputs)
                write_jsonl(args.output / "errors.jsonl", errors)
    if errors:
        raise SystemExit(f"Panel incomplete: {len(errors)} request(s) failed; see errors.jsonl")
    # Publish majority results only for a complete panel; no silent missing votes.
    diagnostic = summarize(outputs)
    write_jsonl(args.output / "annotations.jsonl", outputs)
    write_jsonl(args.output / "consensus.jsonl", diagnostic.pop("consensus"))
    (args.output / "diagnostics.json").write_text(json.dumps(diagnostic, indent=2) + "\n", encoding="utf-8")
    print("Completed. Agreement is not semantic accuracy.")


if __name__ == "__main__":
    main()
