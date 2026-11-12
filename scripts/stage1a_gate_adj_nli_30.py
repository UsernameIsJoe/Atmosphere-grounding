#!/usr/bin/env python3
"""Controlled local gate experiment: adjective POS vs 3 NLI models x 3 hypotheses.

No E/T classification, no hard gating of LLM inputs, no automatic accuracy claim.
Both Ollama models rate ALL sampled source segments under the SAME prompt.
Candidate routing rules are evaluated afterwards (including compute cost).
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import math
import random
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage1a_panel_pilot import load_real_reviews, segment_review

VERSION = "gate_adj_3nli_3hyp_2026_11_12_v1"
NLI_MODELS = {
    "bart": "facebook/bart-large-mnli",
    "deberta": "MoritzLaurer/deberta-v3-large-zeroshot-v2.0",
    "modernbert": "MoritzLaurer/ModernBERT-large-zeroshot-v2.0",
}
HYPOTHESES = [
    "This passage describes how the atmosphere of a place is experienced.",
    "The writer conveys a feeling or perception about spending time in this location.",
    "The text directly expresses an experiential quality or perceived character of the place.",
]
LLMS = ("qwen3:8b", "gemma3:4b")
CATEGORIES = ("calm", "inviting", "safe")
LLM_SYSTEM = """You are evaluating what a REAL visitor's text conveys about the atmosphere of a particular place.
Evaluate the HIGHLIGHTED TARGET SEGMENT for three qualities, independently:
- calm: peaceful, quiet, relaxing vs agitating, noisy, stressful;
- inviting: welcoming, approachable, comfortable to be in vs excluding, hostile, unwelcoming;
- safe: secure, protected, without felt risk vs unsafe, threatening, hazardous.
Return one verdict for EACH category: supports, opposes, mixed, none, or uncertain.
A verdict requires a defensible link to what the reviewer actually says about THIS place.
Physical hazards may directly oppose safety; direct descriptions of atmosphere can support a category.
Do not automatically translate nice/beautiful/good, trees/benches, activities, high ratings,
or any other generic positive feature into calm/inviting/safe.
Use the FULL REVIEW only to resolve subjects, references, scope, negation and contextual ambiguity.
The exact quoted evidence MUST appear character-for-character inside TARGET SEGMENT, NOT nearby context.
If the target provides no meaningful category information, use none and quote="".
Use uncertain when the link is plausible but insufficiently grounded; do not invent a feeling.
Do not assume any fixed evidence/inference partition. Judge the claim and its attribution.
Provide one short rationale about the actual text, not a generic definition.
Return JSON matching the schema, no commentary."""

# V2 changes the LLM methodology; never mix its outputs with the saved V1 verdicts.
LLM_SYSTEM_V2 = """Evaluate only the TARGET SEGMENT as evidence about how THIS PLACE feels
or is perceived by visitors. The FULL REVIEW is supplied only to resolve
references and place/person attribution. It is NOT additional evidence for the
target segment.

Independently rate each of three categories:
calm: peaceful/quiet/relaxing versus noisy/stressful/disturbing;
inviting: welcoming/comfortable/approachable versus excluding/unwelcoming;
safe: safe/protected/secure versus hazardous/threatening/unsafe.

Return EXACTLY ONE row for EACH category (calm, inviting, safe).
Each row has category, verdict, quote, attribution, reason.
Verdict must be supports, opposes, mixed, none or uncertain.

CRITICAL SOURCE BOUNDARY:
- A supports/opposes/mixed verdict MUST cite a literal, continuous substring
  copied CHARACTER FOR CHARACTER from TARGET SEGMENT.
- Do not take a quote or judgment about another sentence from FULL REVIEW.
- Do not add quotation marks around the copied text unless the quotation marks
  actually appear in TARGET SEGMENT.
- If the target lacks category evidence, verdict='none' and quote=''.
- If the target's implication is unclear, verdict='uncertain'; quote may be ''.
- Do not assign a category to generic praise, features, or reviewer activities
  without a defensible atmospheric connection within the target segment.
- Do not infer emotion about a wedding, visit, or person using adjectives from
  another sentence in the full review.
- If a target reads 'My husband and I got eloped here.' but another sentence
  says 'It was so stressful', DO NOT quote 'It was so stressful' for that target.
- If target is 'This is the place to come for making your day the best one.',
  a permissible copied quote is exactly
  'This is the place to come for making your day the best one.'
  (without the single quotes used to delimit this instruction).

Use full-review context for reference resolution only. One short reason per
category. Reply with valid schema JSON and no outside commentary."""

ITEM_FIELDS = {
    "category": {"type": "string", "enum": list(CATEGORIES)},
    "verdict": {"type": "string", "enum": ["supports", "opposes", "mixed", "none", "uncertain"]},
    "quote": {"type": "string"},
    "attribution": {"type": "string", "enum": ["place", "person", "other", "ambiguous"]},
    "reason": {"type": "string"},
}
LLM_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"ratings": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "properties": ITEM_FIELDS, "required": list(ITEM_FIELDS)}}},
    "required": ["ratings"],
}


def sha(obj: object) -> str:
    if isinstance(obj, bytes):
        raw = obj
    elif isinstance(obj, str):
        raw = obj.encode("utf-8")
    else:
        raw = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_jsonl(path: Path, item: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    columns = list(rows[0])
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def choose_reviews(rows: list[dict], count: int, seed: int) -> list[dict]:
    """One randomly selected real review per distinct place for diagnostic breadth."""
    grouped = collections.defaultdict(list)
    for review in rows:
        grouped[review["place_id"]].append(review)
    if count > len(grouped):
        raise ValueError(f"Request at most {len(grouped)} reviews for unique-place sampling")
    rng = random.Random(seed)
    places = sorted(grouped)
    rng.shuffle(places)
    return [rng.choice(sorted(grouped[p], key=lambda r: r["review_index"])) for p in places[:count]]


def make_segments(reviews: list[dict]) -> list[dict]:
    units = []
    for review in reviews:
        source = review["text"]
        rid = sha([review["place_id"], review["review_index"], source])[:20]
        for u in segment_review(source):
            units.append({
                "review_id": rid, "segment_id": u["unit_id"],
                "place_id": review["place_id"], "review_index": review["review_index"],
                "source_sha256": sha(source), "start": u["start"], "end": u["end"],
                "segment": u["text"], "full_review": source,
            })
    return units


def key(segment: dict) -> str:
    return f'{segment["review_id"]}:{segment["segment_id"]}'


def prepare(args) -> tuple[dict, list[dict]]:
    if "fixtures" in args.input.parts or args.input.name != "reviews.jsonl":
        raise ValueError("Source must be real data/processed/reviews.jsonl")
    rows = load_real_reviews(args.input, 0)
    selected = choose_reviews(rows, args.reviews, args.seed)
    units = make_segments(selected)
    if not units:
        raise ValueError("No segments")
    manifest = {
        "version": VERSION, "source_file_sha256": sha(args.input.read_bytes()),
        "selection": "one seeded random review from each of 30 seeded unique places",
        "seed": args.seed, "reviews": len(selected), "places": len({r["place_id"] for r in selected}),
        "n_segments": len(units), "segments_sha256": sha(units),
        "sample_keys": [[r["place_id"], r["review_index"], sha(r["text"])] for r in selected],
        "nli_models": NLI_MODELS, "hypotheses": HYPOTHESES,
        "pos_tagger": "spaCy en_core_web_sm, token.pos_ == ADJ",
        "llms": list(LLMS), "llm_prompt_sha256": sha(LLM_SYSTEM),
        "llm_schema_sha256": sha(LLM_SCHEMA),
        "warning": "Gates are candidates, not accuracy labels or calibrated NLI probabilities",
    }
    saved = args.output / "input/manifest.json"
    if saved.exists():
        if json.loads(saved.read_text(encoding="utf-8")) != manifest:
            raise ValueError("Experiment manifest changed. Use a fresh --output path.")
        if sha(read_jsonl(args.output / "input/segments.jsonl")) != sha(units):
            raise ValueError("Stored segments mismatch original corpus")
    else:
        if any(args.output.iterdir()) if args.output.exists() else False:
            raise ValueError("Nonempty output directory without manifest; use fresh --output")
        write_json(saved, manifest)
        path = args.output / "input/segments.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for item in units:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"PREPARED {len(selected)} real reviews from {manifest['places']} places; "
          f"{len(units)} segments", flush=True)
    return manifest, units


class ProgressBar:
    """Dependency-free terminal progress; handles already-completed resume records."""

    def __init__(self, label: str, total: int, completed: int = 0) -> None:
        self.label = label
        self.total = total
        self.tty = sys.stdout.isatty()
        self.last_bucket = -1
        self.update(completed, initial=True)

    def update(self, completed: int, failures: int = 0, initial: bool = False) -> None:
        completed = min(self.total, max(0, completed))
        portion = completed / self.total if self.total else 1.0
        width = 22
        filled = round(width * portion)
        bar = "#" * filled + "-" * (width - filled)
        line = (f"{self.label:<18} [{bar}] {completed}/{self.total} "
                f"({portion:.0%})" + (f" | failed: {failures}" if failures else ""))
        if self.tty:
            print("\r" + line.ljust(100), end="\n" if completed == self.total else "",
                  flush=True)
        else:
            bucket = int(portion * 10)
            if initial or completed == self.total or bucket > self.last_bucket:
                print(line, flush=True)
            self.last_bucket = bucket


def adjective_gate(units: list[dict], out: Path, limit: int = 0) -> None:
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm", disable=["parser", "ner", "lemmatizer"])
    except (ImportError, OSError) as exc:
        raise RuntimeError(
            "Install spaCy and the English tagger: pip install spacy; "
            "python -m spacy download en_core_web_sm") from exc
    rows = read_jsonl(out)
    done = {r["key"] for r in rows}
    subset = units[:limit or None]
    completed = sum(key(s) in done for s in subset)
    progress = ProgressBar("POS adjectives", len(subset), completed)
    for s in subset:
        if key(s) in done:
            continue
        doc = nlp(s["segment"])
        adjectives = [{"text": tok.text, "start": tok.idx + s["start"],
                       "end": tok.idx + len(tok.text) + s["start"]}
                      for tok in doc if tok.pos_ == "ADJ"]
        append_jsonl(out, {"key": key(s), "adjective_present": bool(adjectives),
                           "adjectives": adjectives})
        completed += 1
        progress.update(completed)
    print(f"POS SAVED {out}", flush=True)


def native_labels(model) -> tuple[dict[int, str], str]:
    mapping = {int(i): str(v).lower().replace("-", "_").replace(" ", "_")
               for i, v in model.config.id2label.items()}
    vals = set(mapping.values())
    if vals == {"entailment", "neutral", "contradiction"}:
        return mapping, "three_way"
    if vals == {"entailment", "not_entailment"}:
        return mapping, "binary"
    raise ValueError(f"Unrecognized NLI label space: {mapping}")


def nli_score(units: list[dict], out: Path, alias: str, batch: int, limit: int = 0,
              max_length: int = 512) -> None:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    model_id = NLI_MODELS[alias]
    # Only one checkpoint in RAM at a time, even though all 3 hypotheses
    # are compared on the same inputs within each checkpoint.
    torch.set_num_threads(min(4, torch.get_num_threads()))
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"NLI {alias}: downloading/loading {model_id} on {device}", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForSequenceClassification.from_pretrained(model_id).to(device).eval()
    labels, label_space = native_labels(model)
    outrows = read_jsonl(out)
    done = {r["key"] for r in outrows}
    subset = units[:limit or None]
    completed = sum(key(u) in done for u in subset)
    progress = ProgressBar(f"NLI {alias}", len(subset), completed)
    for u in subset:
        if key(u) in done:
            continue
        start = time.perf_counter()
        # IMPORTANT: premise is ONLY segment. NLI never sees other model ratings.
        premises = [u["segment"]] * len(HYPOTHESES)
        encoded = tokenizer(premises, HYPOTHESES, truncation=True,
                            padding=True, max_length=max_length, return_tensors="pt")
        with torch.inference_mode():
            logits = model(**{k: v.to(device) for k, v in encoded.items()}).logits
        probs = torch.softmax(logits.float(), dim=-1).cpu().tolist()
        scores = [{k: float(vec[idx]) for idx, k in labels.items()} for vec in probs]
        if not all("entailment" in v and math.isfinite(v["entailment"]) for v in scores):
            raise ValueError("NLI model has missing/non-finite entailment score")
        values = [v["entailment"] for v in scores]
        append_jsonl(out, {
            "key": key(u), "checkpoint": model_id, "label_space": label_space,
            "hypotheses": [{"id": j + 1, "text": HYPOTHESES[j],
                            "probabilities": scores[j],
                            "predicted_label": max(scores[j], key=scores[j].get)}
                           for j in range(len(HYPOTHESES))],
            "mean_entailment": statistics.mean(values),
            "entailment_range": max(values) - min(values),
            "duration_s": round(time.perf_counter() - start, 4),
        })
        completed += 1
        progress.update(completed)
    print(f"NLI {alias} SAVED {completed}/{len(subset)}", flush=True)
    del model
    if device == "cuda":
        torch.cuda.empty_cache()


def llm_payload(model: str, u: dict, feedback: str = "",
                version: str = "v1") -> dict:
    request = {
        "model": model,
        "messages": [
            {"role": "system", "content": LLM_SYSTEM_V2 if version == "v2" else LLM_SYSTEM},
            {"role": "user", "content": json.dumps({
                "target_segment": u["segment"],
                "full_original_review_for_context": u["full_review"],
                "instruction": ("ONLY the target_segment may supply category evidence or quotes. "
                                "The full review is for reference resolution; not classification evidence."),
            }, ensure_ascii=False)},
        ],
        "format": LLM_SCHEMA, "stream": False,
        "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 1350},
    }
    if feedback:
        request["messages"].append({"role": "user", "content": feedback})
    if model.lower().startswith("qwen3:"):
        request["think"] = False
    return request


def validate_llm(obj: object, u: dict, strict_quotes: bool = False) -> list[dict]:
    if not isinstance(obj, dict) or set(obj) != {"ratings"} or not isinstance(obj["ratings"], list):
        raise ValueError("Wrong output envelope")
    ratings = obj["ratings"]
    if len(ratings) != len(CATEGORIES):
        raise ValueError("Exactly one rating per category required")
    categories = []
    clean = []
    for r in ratings:
        if not isinstance(r, dict) or set(r) != set(ITEM_FIELDS):
            raise ValueError("Wrong rating fields")
        for field, spec in ITEM_FIELDS.items():
            if not isinstance(r[field], str) or ("enum" in spec and r[field] not in spec["enum"]):
                raise ValueError(f"Invalid {field}")
        categories.append(r["category"])
        original_quote = r["quote"]
        quote = original_quote
        quote_normalization = "none"
        # One harmless presentation error can be repaired deterministically:
        # the model sometimes adds literal quote wrappers not present in source.
        # Preserve the raw string; NEVER fuzzy-match, paraphrase or search
        # elsewhere in the full review to manufacture target evidence.
        if quote and quote not in u["segment"]:
            for left, right in (('"', '"'), ("'", "'"), ("“", "”"), ("‘", "’")):
                if quote.startswith(left) and quote.endswith(right) and len(quote) > 2:
                    candidate = quote[len(left):len(quote)-len(right)]
                    if candidate in u["segment"]:
                        quote = candidate
                        quote_normalization = "removed_outer_quote_marks"
                        break
        offsets, pos = [], 0
        if quote:
            while (index := u["segment"].find(quote, pos)) != -1:
                offsets.append({"start": u["start"] + index, "end": u["start"] + index + len(quote)})
                pos = index + 1
        verdict = r["verdict"]
        if verdict == "none":
            status = "not_required"
        elif verdict == "uncertain":
            status = ("verified" if offsets else "optional_unverified" if quote
                      else "not_required")
        else:
            status = "verified" if offsets else "unverified" if quote else "not_provided"
        if strict_quotes and status in ("unverified", "not_provided"):
            leakage = bool(original_quote) and original_quote in u["full_review"]
            raise ValueError(
                f"{r['category']}={verdict}: source quote absent from target "
                f"({'appears elsewhere in FULL REVIEW: context leakage' if leakage else 'not source-exact'}); "
                f"quote={original_quote[:75]!r}; target={u['segment'][:100]!r}"
            )
        clean.append({**r, "quote": quote, "quote_raw": original_quote,
                      "quote_normalization": quote_normalization,
                      "quote_offsets": offsets, "quote_status": status,
                      "extraneous_quote_for_none": bool(original_quote) and verdict == "none"})
    if set(categories) != set(CATEGORIES) or len(set(categories)) != len(categories):
        raise ValueError("Missing/duplicate category")
    return sorted(clean, key=lambda x: CATEGORIES.index(x["category"]))


def ollama_call(base: str, payload: dict, timeout: int) -> tuple[str, dict]:
    request = urllib.request.Request(
        base.rstrip("/") + "/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        out = json.load(response)
    return out.get("message", {}).get("content", ""), {
        "model": out.get("model"), "done_reason": out.get("done_reason"),
        "prompt_eval_count": out.get("prompt_eval_count"), "eval_count": out.get("eval_count")}


def check_ollama(base: str, timeout: int) -> dict:
    with urllib.request.urlopen(base.rstrip("/") + "/api/tags", timeout=min(timeout, 20)) as f:
        models = json.load(f).get("models", [])
    installed = {m.get("name"): m.get("digest") for m in models}
    missing = [m for m in LLMS if m not in installed]
    if missing:
        raise RuntimeError(f"Missing Ollama models: {missing}. Run ollama pull for each.")
    return {m: installed[m] for m in LLMS}


def llm_score(units: list[dict], out: Path, base: str, timeout: int,
              limit: int = 0, version: str = "v1") -> None:
    digests = check_ollama(base, timeout)
    if version == "v2":
        # Preserve all V1 outputs. The v2 prompt/validator has separate files,
        # an immutable protocol manifest and distinct report output.
        protocol_path = out / "protocol_v2.json"
        expected = {"version": "v2", "prompt_sha256": sha(LLM_SYSTEM_V2),
                    "schema_sha256": sha(LLM_SCHEMA),
                    "source_segments_sha256": sha(units),
                    "validation": "literal-target-only-with-outer-quote-normalization"}
        if protocol_path.exists():
            if json.loads(protocol_path.read_text(encoding="utf-8")) != expected:
                raise ValueError("LLM v2 protocol changed; choose a new output directory")
        else:
            if out.exists() and any(out.iterdir()):
                raise ValueError("LLM v2 output exists without protocol; choose a fresh directory")
            write_json(protocol_path, expected)
    digest_path = out / "llm_model_digests.json"
    if digest_path.exists():
        if json.loads(digest_path.read_text(encoding="utf-8")) != digests:
            raise ValueError("Ollama model checkpoint changed: use new --output")
    else:
        write_json(digest_path, digests)
    for model in LLMS:
        folder = out / model.replace(":", "_")
        rows_file = folder / "ratings.jsonl"
        raw_file = folder / "raw_responses.jsonl"
        failures_file = folder / "errors.jsonl"
        done = {r["key"] for r in read_jsonl(rows_file)}
        all_keys = {key(s) for s in units}
        if not done <= all_keys:
            raise ValueError("Unexpected saved LLM result")
        subset = units[:limit or None]
        completed = sum(key(u) in done for u in subset)
        progress = ProgressBar(f"LLM {model}", len(subset), completed)
        failures = 0
        consecutive_failures = 0
        quote_warnings_shown = 0
        for u in subset:
            if key(u) in done:
                continue
            prior_error = ""
            success = False
            for attempt in (1, 2, 3):
                feedback = ""
                if attempt > 1:
                    feedback = ("Previous response failed the strict source/schema validator: "
                                + prior_error[:140] + ". Re-evaluate the SOURCE and quote ONLY "
                                "literal substrings of target_segment. Include all 3 category rows; "
                                "when in doubt use none/uncertain rather than inventing a quotation.")
                raw, info, error = "", {}, None
                started = time.perf_counter()
                try:
                    raw, info = ollama_call(base, llm_payload(model, u, feedback, version), timeout)
                    cleaned = validate_llm(json.loads(raw), u, strict_quotes=(version == "v2"))
                    success = True
                except (ValueError, KeyError, TypeError, urllib.error.URLError, TimeoutError) as exc:
                    error = f"{type(exc).__name__}: {exc}"
                    if isinstance(exc, urllib.error.HTTPError):
                        try:
                            detail = exc.read(2048).decode("utf-8", errors="replace")
                            error += f" | Ollama response: {detail}"
                        except OSError:
                            pass
                    # Show diagnostic immediately; don't force a full 123-case run
                    # merely to discover the first failure's cause.
                    print(f"\nLLM {model} {key(u)} attempt {attempt}/3 FAILED: "
                          f"{error[:300]}", flush=True)
                append_jsonl(raw_file, {"key": key(u), "attempt": attempt, "raw": raw,
                                        "metadata": info, "error": error,
                                        "duration_s": round(time.perf_counter()-started, 4)})
                if success:
                    questionable = [v["category"] for v in cleaned
                                    if v["quote_status"] in ("unverified", "not_provided")]
                    append_jsonl(rows_file, {"key": key(u), "ratings": cleaned,
                                            "segment_sha256": sha(u["segment"]),
                                            "model": model})
                    if questionable:
                        print(f"\nLLM {model} {key(u)}: source quotations NOT VERIFIED "
                              f"for nonempty verdicts: {', '.join(questionable)}", flush=True)
                        if quote_warnings_shown < 3:
                            for rating in cleaned:
                                if rating["quote_status"] in ("unverified", "not_provided"):
                                    print(f"  {rating['category']}={rating['verdict']}; "
                                          f"quote={rating['quote'][:100]!r}; "
                                          f"target={u['segment'][:160]!r}", flush=True)
                            quote_warnings_shown += 1
                    done.add(key(u))
                    consecutive_failures = 0
                    break
                prior_error = error or ""
            if not success:
                append_jsonl(failures_file, {"key": key(u), "error": prior_error})
                failures += 1
                consecutive_failures += 1
            completed += 1
            progress.update(completed, failures)
            if version == "v2" and consecutive_failures >= 3:
                raise RuntimeError(
                    f"{model}: three consecutive segments failed even after retries. "
                    f"Stopped to avoid wasting inference; inspect {failures_file} "
                    f"and {raw_file}."
                )
        print(f"LLM {model} FINISHED {completed}/{len(subset)} examined; "
              f"{failures} new failures logged", flush=True)
        # Important: records from a run before this fix may have old status
        # annotations. Diagnose stage recomputes them without changing data.
        diagnose_saved(units, out, model, max_examples=0)


def diagnose_saved(units: list[dict], out: Path, model: str,
                   max_examples: int = 5) -> dict:
    """Read existing predictions; recompute quote status without rewriting a byte.

    This also diagnoses pre-patch saved rows whose quote_status was misleading.
    No model calls, no gate re-inference, no change to the frozen manifest.
    """
    path = out / model.replace(":", "_") / "ratings.jsonl"
    rows = read_jsonl(path)
    source = {key(u): u for u in units}
    verdicts, status_counts = collections.Counter(), collections.Counter()
    mismatch_examples, extraneous_examples, extra_none = [], [], 0
    for row in rows:
        if row["key"] not in source:
            raise ValueError(f"Saved LLM result not in source manifest: {row['key']}")
        segment = source[row["key"]]
        clean = validate_llm(
            {"ratings": [{field: rating[field] for field in ITEM_FIELDS}
                         for rating in row["ratings"]]}, segment)
        for rating in clean:
            verdicts[rating["verdict"]] += 1
            status_counts[rating["quote_status"]] += 1
            extra_none += int(rating["extraneous_quote_for_none"])
            if rating["extraneous_quote_for_none"] and len(extraneous_examples) < max_examples:
                extraneous_examples.append({
                    "key": row["key"], "category": rating["category"],
                    "verdict": "none", "unnecessary_quote": rating["quote"],
                    "target_segment": segment["segment"],
                })
            if rating["quote_status"] in ("unverified", "not_provided") and len(mismatch_examples) < max_examples:
                mismatch_examples.append({
                    "key": row["key"], "category": rating["category"],
                    "verdict": rating["verdict"],
                    "quote": rating["quote"], "target_segment": segment["segment"],
                    "quote_exists_elsewhere_in_full_review": (
                        bool(rating["quote"]) and rating["quote"] in segment["full_review"]
                    ),
                })
    summary = {
        "model": model, "saved_segments": len(rows),
        "verdicts": dict(verdicts),
        "quote_status_recomputed": dict(status_counts),
        "extraneous_quotes_for_none": extra_none,
    }
    print("DIAGNOSE", json.dumps(summary, ensure_ascii=False), flush=True)
    for example in mismatch_examples:
        print("UNSUPPORTED_VERDICT_QUOTE", json.dumps(example, ensure_ascii=False), flush=True)
    for example in extraneous_examples:
        print("UNNECESSARY_NONE_QUOTE", json.dumps(example, ensure_ascii=False), flush=True)
    return summary


def as_keyed(items: list[dict]) -> dict:
    result = {}
    for r in items:
        if r["key"] in result:
            raise ValueError("Duplicate saved segment key")
        result[r["key"]] = r
    return result


def summarize(args, units: list[dict], limit: int = 0) -> dict:
    subset = units[:limit or None]
    version = getattr(args, "llm_version", "v1")
    llm_dir = args.output / ("llm_v2" if version == "v2" else "llm")
    report_dir = args.output / ("comparison_v2" if version == "v2" else "comparison")
    adjective = as_keyed(read_jsonl(args.output / "gates/pos.jsonl"))
    nli = {name: as_keyed(read_jsonl(args.output / f"gates/nli_{name}.jsonl"))
           for name in NLI_MODELS}
    llm = {model: as_keyed(read_jsonl(llm_dir / model.replace(":", "_") / "ratings.jsonl"))
           for model in LLMS}
    # Older stored rows may carry the pre-fix quote_status. Recompute
    # annotations from the immutable model strings and original segments.
    sources = {key(u): u for u in units}
    for model in LLMS:
        for k, saved in llm[model].items():
            if k not in sources:
                raise ValueError(f"Unknown saved LLM key: {k}")
            saved["ratings"] = validate_llm(
                {"ratings": [{field: rating[field] for field in ITEM_FIELDS}
                             for rating in saved["ratings"]]}, sources[k])
    rows = []
    for u in subset:
        k = key(u)
        adj = adjective.get(k, {}).get("adjective_present")
        entail = [nli[name].get(k, {}).get("mean_entailment") for name in NLI_MODELS]
        available = [v for v in entail if v is not None]
        score = statistics.median(available) if len(available) == len(NLI_MODELS) else None
        ranges = [nli[name][k]["entailment_range"] for name in NLI_MODELS if k in nli[name]]
        predictions = [llm[model].get(k) for model in LLMS]
        disagreement = None
        if all(p is not None for p in predictions):
            a, b = (p["ratings"] for p in predictions)
            disagreement = any(x["verdict"] != y["verdict"] for x, y in zip(a, b))
        all_phrases = [p["hypotheses"][j]["probabilities"]["entailment"]
                       for name in NLI_MODELS if k in nli[name]
                       for p in [nli[name][k]] for j in range(3)]
        rows.append({
            "key": k, "place_id": u["place_id"], "review_index": u["review_index"],
            "segment_id": u["segment_id"], "segment": u["segment"],
            "adjective": adj,
            "adj_words": ", ".join(x["text"] for x in adjective.get(k, {}).get("adjectives", [])),
            "nli_bart": entail[0], "nli_deberta": entail[1], "nli_modernbert": entail[2],
            "nli_median": score, "nli_hypothesis_max_range": max(ranges) if ranges else None,
            "nli_all9_range": max(all_phrases)-min(all_phrases) if len(all_phrases)==9 else None,
            "qwen": " | ".join(f'{v["category"]}:{v["verdict"]}' for v in predictions[0]["ratings"])
                    if predictions[0] else "",
            "gemma": " | ".join(f'{v["category"]}:{v["verdict"]}' for v in predictions[1]["ratings"])
                    if predictions[1] else "",
            "llm_disagreement": disagreement,
            "qwen_unverified_quotes": sum(v.get("quote_status") in ("unverified", "not_provided")
                                          for v in predictions[0]["ratings"]) if predictions[0] else None,
            "gemma_unverified_quotes": sum(v.get("quote_status") in ("unverified", "not_provided")
                                           for v in predictions[1]["ratings"]) if predictions[1] else None,
            "qwen_extraneous_none_quotes": sum(bool(v.get("extraneous_quote_for_none"))
                                               for v in predictions[0]["ratings"]) if predictions[0] else None,
            "gemma_extraneous_none_quotes": sum(bool(v.get("extraneous_quote_for_none"))
                                                for v in predictions[1]["ratings"]) if predictions[1] else None,
        })
    write_csv(report_dir / "segment_gate_comparison.csv", rows)
    ready = [r for r in rows if r["adjective"] is not None and r["nli_median"] is not None]
    with_models = [r for r in ready if r["llm_disagreement"] is not None]
    proposals = {
        "adjective": lambda r: bool(r["adjective"]),
        "nli_median_0.4": lambda r: r["nli_median"] >= .4,
        "nli_median_0.6": lambda r: r["nli_median"] >= .6,
        "nli_median_0.8": lambda r: r["nli_median"] >= .8,
        "adj_or_nli_0.6": lambda r: r["adjective"] or r["nli_median"] >= .6,
        "adj_and_nli_0.6": lambda r: r["adjective"] and r["nli_median"] >= .6,
    }
    routing = {}
    for name, predicate in proposals.items():
        simple = [r for r in ready if predicate(r)]
        complex_ = [r for r in ready if not predicate(r)]
        inferred_calls = len(ready) + len(complex_)
        observed = [r for r in with_models if predicate(r)]
        routing[name] = {
            "easy_segments": len(simple), "hard_segments": len(complex_),
            "estimated_two_model_calls": inferred_calls,
            "compared_to_two_models_everywhere": 2 * len(ready),
            "estimated_call_savings_fraction":
                round((2*len(ready)-inferred_calls)/(2*len(ready)), 3) if ready else None,
            "llm_disagreement_on_easy_candidates":
                round(sum(bool(r["llm_disagreement"]) for r in observed)/len(observed), 3)
                if observed else None,
            "easy_with_independent_second_model_observed": len(observed),
        }
    # Audit packet intentionally includes gate conflict and model-disagreement cases.
    rng = random.Random(args.seed + 299)
    categories = [
        ("adj_vs_nli_conflict", [r for r in with_models if r["adjective"] != (r["nli_median"] >= .6)]),
        ("llm_disagreement", [r for r in with_models if r["llm_disagreement"]]),
        ("nli_wording_sensitive", [r for r in with_models if (r["nli_hypothesis_max_range"] or 0) >= .35]),
        ("agreed_early_candidate", [r for r in with_models if r["adjective"] and r["nli_median"] >= .6
                                     and not r["llm_disagreement"]]),
        ("unselected_random", with_models),
    ]
    audit, picked = [], set()
    for group, source in categories:
        pool = list(source)
        rng.shuffle(pool)
        for row in pool:
            if len([x for x in audit if x["sampling_reason"] == group]) >= 5:
                break
            if row["key"] in picked:
                continue
            picked.add(row["key"])
            audit.append({
                "key": row["key"], "reason": group, "place_id": row["place_id"],
                "segment": row["segment"],
                "full_review": next(x["full_review"] for x in units if key(x) == row["key"]),
                "human_atmosphere_category_or_none": "",
                "human_direction_or_unknown": "",
                "human_easy_for_one_model_yes_no": "",
                "human_comments": "",
            } | {"sampling_reason": group})
    write_csv(report_dir / "human_audit_blind.csv", audit)
    summary = {
        "segments_requested": len(subset), "gate_complete_segments": len(ready),
        "llm_double_rated_segments": len(with_models),
        "unverified_quote_counts_by_model": {
            model: sum(v.get("quote_status") in ("unverified", "not_provided")
                       for row in llm[model].values() for v in row["ratings"])
            for model in LLMS
        },
        "extraneous_none_quote_counts_by_model": {
            model: sum(bool(v.get("extraneous_quote_for_none"))
                       for row in llm[model].values() for v in row["ratings"])
            for model in LLMS
        },
        "overall_llm_disagreement_rate":
            round(sum(bool(r["llm_disagreement"]) for r in with_models)/len(with_models), 3)
            if with_models else None,
        "routing_simulations_NOT_accuracy": routing,
        "human_audit_packet_size": len(audit),
        "model_names": list(NLI_MODELS), "hypotheses": HYPOTHESES,
        "limitations": [
            "Candidate routing decisions are hypotheses, not validated optimal thresholds.",
            "NLI softmax is not a calibrated chance of real emotional relevance.",
            "LLM agreement is NOT ground truth; human source audit needed for gate accuracy.",
            "NLI meta-hypotheses have failed some explicit cases in this project's prior five-review test.",
            "Inference times and model loading/downloads must be considered before claiming savings.",
            "Full-review context is supplied to both LLMs to hold LLM task constant.",
        ],
    }
    write_json(report_dir / "summary.json", summary)
    return summary


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", choices=["prepare", "adj", "nli", "llm", "report", "diagnose", "all"], default="all")
    p.add_argument("--llm-version", choices=["v1", "v2"], default="v2",
                   help="v2 improves target-only grounding and saves independently of old v1 results")
    p.add_argument("--input", type=Path, default=ROOT / "data/processed/reviews.jsonl")
    p.add_argument("--output", type=Path, default=ROOT / "reports/stage1a_gate_adj_nli_30_2026-11-12")
    p.add_argument("--reviews", type=int, default=30)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--nli", choices=["all", *NLI_MODELS], default="all")
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--base", default="http://127.0.0.1:11434")
    p.add_argument("--timeout", type=int, default=480)
    p.add_argument("--limit-segments", type=int, default=0, help="Smoke test; omission resumes full sample")
    args = p.parse_args()
    if args.reviews < 1 or args.limit_segments < 0 or args.timeout < 1:
        p.error("Invalid counts")
    _, units = prepare(args)
    if args.stage in ("adj", "all"):
        adjective_gate(units, args.output / "gates/pos.jsonl", args.limit_segments)
    if args.stage in ("nli", "all"):
        for name in ([args.nli] if args.nli != "all" else NLI_MODELS):
            nli_score(units, args.output / f"gates/nli_{name}.jsonl", name, args.batch_size,
                      args.limit_segments)
    if args.stage in ("llm", "all"):
        llm_score(units, args.output / ("llm_v2" if args.llm_version == "v2" else "llm"),
                  args.base, args.timeout, args.limit_segments, version=args.llm_version)
    if args.stage == "diagnose":
        for name in LLMS:
            diagnose_saved(units, args.output / ("llm_v2" if args.llm_version == "v2" else "llm"), name)
    if args.stage in ("report", "all"):
        summary = summarize(args, units, args.limit_segments)
        print("REPORT", json.dumps({k: v for k, v in summary.items() if k != "routing_simulations_NOT_accuracy"},
                                   ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
