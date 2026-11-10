#!/usr/bin/env python3
"""Stage 1A v2: grounded Step A annotation + paired-hypothesis NLI Step B.

Real Google review text only. No paraphrased premises, synthetic test sentences,
or same-model verifier. Dev is the default; holdout requires --allow-holdout.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage1a_component1_ollama import call_ollama
from stage1a_relation_pilot import select_pilot
from stage1a_component3_real_google_diagnostic import select as earlier_nli_select

REVIEWS = ROOT / "data/processed/reviews.jsonl"
COLLECT = ROOT / "data/processed/collect_summary.json"
ARCHIVE = ROOT / "research_audit/stage1a_final_2026-11-10/results"
OUT = ROOT / "reports/stage1a_v2"
EMOTIONS = ("calm", "inviting", "safe")
RELEVANCE = ("supports", "opposes", "mixed", "not_relevant", "uncertain")
TYPES = ("explicit", "direct_indicator", "indirect")
ATTRIBUTIONS = ("first_person", "secondhand", "hedged", "general")
NLI_MODELS = (
    "facebook/bart-large-mnli",
    "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli",
)
PAIRED_HYPOTHESES = {
    "calm": {
        "positive": ["This place feels calm.", "The atmosphere here is peaceful and quiet.", "Visitors find this place relaxing."],
        "negative": ["This place feels hectic or stressful.", "The atmosphere here is noisy and chaotic.", "Visitors find this place tense."],
    },
    "inviting": {
        "positive": ["This place feels welcoming.", "The atmosphere here is inviting.", "Visitors want to come and stay here."],
        "negative": ["This place feels unwelcoming.", "The atmosphere here is off-putting.", "Visitors want to leave this place."],
    },
    "safe": {
        "positive": ["This place feels safe.", "Visitors feel secure here.", "This place feels protected."],
        "negative": ["This place feels unsafe.", "Visitors feel threatened here.", "This place feels dangerous."],
    },
}

STEP_A_SYSTEM = """You annotate one REAL Google review sentence for three place-atmosphere emotions: calm, inviting, safe.
Use only the supplied sentence and its full review context. Do not invent, paraphrase, or rewrite evidence.
For each emotion choose relevance: supports, opposes, mixed, not_relevant, or uncertain.
Use not_relevant by default for generic praise (great/nice/cute without emotion-specific meaning), bare location facts,
and complaints unrelated to the emotion such as food, service, or prices. Use uncertain only for genuinely ambiguous language or referents.
If relevance is supports/opposes/mixed, choose type: explicit when the sentence names the emotion or a clear synonym about the place;
direct_indicator for a concrete emotion-specific place condition (for example source-grounded police patrol is direct safety evidence)
that is not itself a report of felt emotion; indirect for an inferential link from a less specific fact such as off the beaten path for calm.
Choose attribution: first_person, secondhand, hedged, or general. Secondhand includes claims learned from other people's narratives.
Evidence_span must be the minimal exact contiguous substring of ORIGINAL SENTENCE that supports the label.
For not_relevant or uncertain use an empty evidence_span and null type. Return JSON only."""

STEP_A_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"emotions": {"type": "array", "minItems": 3, "maxItems": 3, "items": {
        "type": "object", "additionalProperties": False,
        "properties": {
            "emotion": {"type": "string", "enum": list(EMOTIONS)},
            "relevance": {"type": "string", "enum": list(RELEVANCE)},
            "type": {"type": ["string", "null"], "enum": [*TYPES, None]},
            "evidence_span": {"type": "string"},
            "attribution": {"type": "string", "enum": list(ATTRIBUTIONS)},
            "rationale": {"type": "string"},
        },
        "required": ["emotion", "relevance", "type", "evidence_span", "attribution", "rationale"],
    }}},
    "required": ["emotions"],
}

SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
CLAUSE_RE = re.compile(r"(?<=[,;:])\s+|\s+[—–]\s+")


def read_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf8"))


def read_jsonl(path: pathlib.Path):
    return [json.loads(x) for x in path.read_text(encoding="utf8").splitlines() if x.strip()]


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def source_data():
    raw = REVIEWS.read_bytes()
    reviews = read_jsonl(REVIEWS)
    collect = read_json(COLLECT)
    archived = read_json(ARCHIVE / "test3.json")
    expected_sha = archived["manifest"]["source_sha256"]
    if sha256_bytes(raw) != expected_sha:
        raise ValueError("data/processed/reviews.jsonl differs from the archived verified corpus")
    if collect.get("dry_run") is not False or collect.get("n_reviews") != len(reviews):
        raise ValueError("collect_summary.json does not verify a non-dry-run collection")
    for row, rev in enumerate(reviews):
        if not isinstance(rev.get("text"), str) or not str(rev.get("place_id", "")).startswith("ChIJ"):
            raise ValueError(f"row {row} is not a verified Google review record")
        if "review_index" not in rev:
            raise ValueError(f"row {row} missing review_index")
    exposed = set(select_pilot(reviews, 20))
    exposed.update(x["row"] for x in earlier_nli_select(reviews, 10)[0])
    final_cases = archived["manifest"]["cases"]
    exposed.update(x["row"] for x in final_cases)
    meta = {
        "source_file": "data/processed/reviews.jsonl",
        "source_sha256": expected_sha,
        "review_count": len(reviews),
        "place_count": collect["n_places"],
        "collector_dry_run": collect["dry_run"],
        "excluded_exposed_rows": sorted(exposed),
    }
    return reviews, final_cases, meta


def _sentences_for_review(row: int, review: dict):
    source = review["text"]
    loc = 0
    for sentence_index, part in enumerate(SPLIT_RE.split(source)):
        if not part.strip():
            continue
        start = source.find(part, loc)
        if start < 0:
            raise ValueError(f"cannot reconstruct sentence offsets for row {row}")
        end = start + len(part)
        loc = end
        if not 5 <= len(part.split()) <= 65:
            continue
        if source[start:end] != part:
            raise ValueError("sentence is not an exact review substring")
        yield {
            "row": row,
            "place_id": review["place_id"],
            "review_index": review["review_index"],
            "sentence_index": sentence_index,
            "start": start,
            "end": end,
            "sentence": part,
            "review_text": source,
            "review_sha256": sha256_bytes(source.encode("utf8")),
            "rating": review.get("rating"),
        }


def split_places(items: list[dict]):
    first_row = {}
    for x in items:
        first_row[x["place_id"]] = min(x["row"], first_row.get(x["place_id"], x["row"]))
    places = sorted(first_row, key=lambda p: (first_row[p], p))
    n_dev = max(1, round(0.30 * len(places)))
    indices = [(i * len(places)) // n_dev for i in range(n_dev)]
    dev = {places[i] for i in indices}
    return dev, set(places) - dev


def load_items(split: str):
    reviews, final_cases, meta = source_data()
    if split == "regression":
        items = []
        for case in final_cases:
            rev = reviews[case["row"]]
            if rev["text"][case["start"]:case["end"]] != case["text"]:
                raise ValueError("archived regression case no longer matches source")
            items.append({
                "row": case["row"], "place_id": case["place_id"], "review_index": case["review_index"],
                "sentence_index": case["sentence_index"], "start": case["start"], "end": case["end"],
                "sentence": case["text"], "review_text": rev["text"], "review_sha256": case["review_sha256"],
                "rating": rev.get("rating"),
            })
        return items, {**meta, "split": "regression", "items": len(items)}
    exposed = set(meta["excluded_exposed_rows"])
    eligible = [s for row, rev in enumerate(reviews) if row not in exposed for s in _sentences_for_review(row, rev)]
    dev_places, holdout_places = split_places(eligible)
    chosen_places = dev_places if split == "dev" else holdout_places
    items = [x for x in eligible if x["place_id"] in chosen_places]
    for x in items:
        if x["review_text"][x["start"]:x["end"]] != x["sentence"]:
            raise ValueError("load-time exact-source assertion failed")
    return items, {**meta, "split": split, "items": len(items),
                   "dev_places": sorted(dev_places), "holdout_places": sorted(holdout_places)}


def annotation_map(obj: dict, sentence: str):
    rows = obj.get("emotions")
    if not isinstance(rows, list) or len(rows) != 3:
        raise ValueError("Step A must return exactly three emotion annotations")
    if {x.get("emotion") for x in rows if isinstance(x, dict)} != set(EMOTIONS):
        raise ValueError("Step A emotion set is incomplete or duplicated")
    out = {}
    for item in rows:
        e = item["emotion"]
        relevance, typ, span = item["relevance"], item["type"], item["evidence_span"]
        flags = []
        exact = (span == "" or span in sentence)
        if span and not exact:
            flags.append("span_not_exact_substring")
        if relevance in ("supports", "opposes", "mixed"):
            if not span:
                flags.append("relevant_missing_span")
            if typ not in TYPES:
                flags.append("relevant_missing_type")
        else:
            if span:
                flags.append("nonrelevant_has_span")
            if typ is not None:
                flags.append("nonrelevant_has_type")
        if span == sentence and len(sentence.split()) > 15:
            flags.append("full_sentence_span_over_15_words")
        hard = {"span_not_exact_substring", "relevant_missing_span", "relevant_missing_type",
                "nonrelevant_has_span", "nonrelevant_has_type"}
        out[e] = {**item, "flags": flags, "valid_for_downstream": not bool(hard.intersection(flags))}
    return out


def run_step_a(args, items: list[dict], outdir: pathlib.Path):
    path = outdir / "step_a.jsonl"
    done = {}
    if path.exists() and args.resume:
        for r in read_jsonl(path):
            key = (r["source"]["row"], r["source"]["start"], r["source"]["end"])
            done[key] = r
    elif path.exists():
        raise ValueError(f"{path} exists; use --resume or remove it")
    with path.open("a" if args.resume else "w", encoding="utf8") as fh:
        for source in items:
            key = (source["row"], source["start"], source["end"])
            if key in done:
                continue
            payload, model_meta = call_ollama(
                args.url, args.model, STEP_A_SYSTEM,
                "FULL REVIEW CONTEXT:\n" + source["review_text"] +
                "\n\nORIGINAL SENTENCE:\n" + source["sentence"],
                STEP_A_SCHEMA, args.timeout, args.num_ctx, think=False, num_predict=1400,
            )
            emotions = annotation_map(payload, source["sentence"])
            record = {"source": source, "model": args.model, "model_meta": model_meta, "emotions": emotions}
            fh.write(json.dumps(record, ensure_ascii=False) + "\n"); fh.flush()
            done[key] = record
            print(f"STEP_A {len(done)}/{len(items)} row={source['row']} sentence={source['sentence_index']}", flush=True)
    return [done[(x["row"], x["start"], x["end"])] for x in items]


def clause_premise(sentence: str, span: str):
    if len(sentence.split()) <= 40:
        return sentence, "full_sentence"
    start = sentence.find(span)
    if start < 0:
        raise ValueError("cannot choose clause for a non-exact evidence span")
    pos = 0
    for part in CLAUSE_RE.split(sentence):
        a = sentence.find(part, pos)
        b = a + len(part)
        pos = b
        if a <= start < b and len(part.split()) >= 4 and part.strip() != span.strip():
            return part, "clause"
    return sentence, "full_sentence"


class NLIScorer:
    def __init__(self, model_name: str):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        self.torch = torch
        torch.set_num_threads(min(4, torch.get_num_threads()))
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name).eval()
        labels = {str(v).lower(): int(k) for k, v in self.model.config.id2label.items()}
        if set(labels) != {"entailment", "neutral", "contradiction"}:
            labels = {str(k).lower(): int(v) for k, v in self.model.config.label2id.items()}
        if set(labels) != {"entailment", "neutral", "contradiction"}:
            raise ValueError(f"unrecognized NLI label space for {model_name}: {labels}")
        self.labels = labels
        self.cache = {}

    def score(self, premise: str, hypothesis: str):
        key = (premise, hypothesis)
        if key in self.cache:
            return self.cache[key]
        full = self.tokenizer(premise, hypothesis, truncation=False)
        if len(full["input_ids"]) > 512:
            raise ValueError("NLI pair exceeds 512 tokens; refusing to truncate")
        tokens = self.tokenizer(premise, hypothesis, truncation=False, return_tensors="pt")
        with self.torch.inference_mode():
            probs = self.torch.softmax(self.model(**tokens).logits[0], dim=-1).tolist()
        dist = {name: float(probs[idx]) for name, idx in self.labels.items()}
        self.cache[key] = {"label": max(dist, key=dist.get), "probs": dist}
        return self.cache[key]


def _model_slug(name: str):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def run_step_b(args, step_a: list[dict], outdir: pathlib.Path, model_name: str):
    path = outdir / f"step_b_{_model_slug(model_name)}.jsonl"
    done = {}
    if path.exists() and args.resume:
        for r in read_jsonl(path):
            key = (r["source"]["row"], r["source"]["start"], r["source"]["end"])
            done[key] = r
    elif path.exists():
        raise ValueError(f"{path} exists; use --resume or remove it")
    scorer = NLIScorer(model_name)
    with path.open("a" if args.resume else "w", encoding="utf8") as fh:
        for record in step_a:
            source = record["source"]
            key = (source["row"], source["start"], source["end"])
            if key in done:
                continue
            out = {}
            for emotion in EMOTIONS:
                a = record["emotions"][emotion]
                if a["relevance"] not in ("supports", "opposes", "mixed") or not a["valid_for_downstream"]:
                    out[emotion] = {"skipped": True, "reason": "step_a_not_eligible"}
                    continue
                premise, kind = clause_premise(source["sentence"], a["evidence_span"])
                positive = [scorer.score(premise, h) for h in PAIRED_HYPOTHESES[emotion]["positive"]]
                negative = [scorer.score(premise, h) for h in PAIRED_HYPOTHESES[emotion]["negative"]]
                pos_mean = sum(x["probs"]["entailment"] for x in positive) / 3.0
                neg_mean = sum(x["probs"]["entailment"] for x in negative) / 3.0
                score = pos_mean - neg_mean
                disagree = ((score > 0 and a["relevance"] == "opposes") or
                            (score < 0 and a["relevance"] == "supports"))
                out[emotion] = {
                    "skipped": False, "premise": premise, "premise_kind": kind,
                    "positive": positive, "negative": negative,
                    "positive_entailment_mean": pos_mean, "negative_entailment_mean": neg_mean,
                    "s": score, "llm_nli_disagree": disagree,
                }
            r = {"source": source, "checkpoint": model_name, "emotions": out}
            fh.write(json.dumps(r, ensure_ascii=False) + "\n"); fh.flush()
            done[key] = r
            print(f"STEP_B {model_name} {len(done)}/{len(step_a)} row={source['row']}", flush=True)
    return [done[(r["source"]["row"], r["source"]["start"], r["source"]["end"])] for r in step_a]


def _old_summary(row: int):
    t1, t2, t3 = [read_json(ARCHIVE / f"test{i}.json") for i in (1, 2, 3)]
    r1 = next(x for x in t1["records"] if x["case"]["row"] == row)
    r2 = next(x for x in t2["records"] if x["case"]["row"] == row)
    r3 = next(x for x in t3["records"] if x["case"]["row"] == row)
    return {
        "claims": [x["claim"] for x in r1["output"]["observations"]],
        "component2": [{"claim": x["original_claim"],
                        "applicability": {a["emotion"]: a["status"] for a in x["decision"]["applicability"]}}
                       for x in r2["output"]["decisions"]],
        "nli": {e: {"whole_sentence": r3["output"][e]["original_nli"]["label"],
                    "selected": [(x["source_quote"], x["nli"]["label"]) for x in r3["output"][e]["selected_evidence"]]}
                for e in EMOTIONS},
    }


def regression_report(outdir: pathlib.Path, step_a: list[dict], step_bs: dict[str, list[dict]]):
    a_by_row = {r["source"]["row"]: r for r in step_a}
    b_by_model = {m: {r["source"]["row"]: r for r in rows} for m, rows in step_bs.items()}
    checks = {}
    for row in (13, 41, 52, 56, 70, 86, 92):
        a = a_by_row[row]
        ae = a["emotions"]
        if row == 13:
            fixed = all(ae[e]["relevance"] != "opposes" for e in EMOTIONS)
        elif row == 41:
            fixed = all(ae[e]["relevance"] != "uncertain" for e in EMOTIONS)
        elif row == 52:
            rel = [ae[e] for e in EMOTIONS if ae[e]["relevance"] in ("supports", "opposes", "mixed")]
            fixed = bool(rel) and all(x["attribution"] == "secondhand" for x in rel)
        elif row == 56:
            fixed = all((not ae[e]["evidence_span"] or ae[e]["evidence_span"] in a["source"]["sentence"]) for e in EMOTIONS)
        elif row == 70:
            fixed = ae["inviting"]["relevance"] == "opposes" and ae["safe"]["relevance"] == "opposes"
        elif row == 86:
            x = ae["safe"]
            fixed = x["relevance"] == "supports" and x["type"] == "explicit" and "safe" in x["evidence_span"].lower()
        else:
            fixed = True
            for model in NLI_MODELS:
                b = b_by_model[model][92]["emotions"]["calm"]
                fixed = fixed and (not b.get("skipped") and b["premise"] == a["source"]["sentence"])
        checks[row] = {
            "old": _old_summary(row),
            "new_step_a": ae,
            "new_step_b": {m: b_by_model[m][row]["emotions"] for m in NLI_MODELS},
            "documented_failure_fixed": fixed,
        }
        print(f"REGRESSION row {row}: {'FIXED' if fixed else 'NOT FIXED'}", flush=True)
    (outdir / "regression_report.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--split", choices=("dev", "holdout", "regression"), default="dev")
    p.add_argument("--stage", choices=("a", "b", "all"), default="all")
    p.add_argument("--model", default="qwen3:8b")
    p.add_argument("--url", default="http://127.0.0.1:11434")
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument("--num-ctx", type=int, default=8192)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--allow-holdout", action="store_true")
    p.add_argument("--check-only", action="store_true")
    args = p.parse_args()
    if args.split == "holdout" and not args.allow_holdout:
        p.error("holdout is locked; rerun with --allow-holdout only after the researcher confirms the gates")
    items, meta = load_items(args.split)
    outdir = OUT / args.split
    outdir.mkdir(parents=True, exist_ok=True)
    if args.check_only:
        print(json.dumps({k: v for k, v in meta.items() if k not in ("dev_places", "holdout_places", "excluded_exposed_rows")}, indent=2))
        return
    step_a_path = outdir / "step_a.jsonl"
    if args.stage in ("a", "all"):
        step_a = run_step_a(args, items, outdir)
    else:
        step_a = read_jsonl(step_a_path)
        if len(step_a) != len(items):
            raise ValueError("Step A is incomplete for this split")
    step_bs = {}
    if args.stage in ("b", "all"):
        for model_name in NLI_MODELS:
            step_bs[model_name] = run_step_b(args, step_a, outdir, model_name)
    if args.split == "regression" and args.stage == "all":
        regression_report(outdir, step_a, step_bs)


if __name__ == "__main__":
    main()
