#!/usr/bin/env python3
"""Stage 1A v0.5 12-case directional evidence benchmark; 2 models x 3 repeats.
No gate/cascade. Raw outputs and failures preserved. Do not rerun old conditions.
Run --stage prepare before leasing GPU; --stage run --model ... on remote.
"""
import argparse, collections, hashlib, json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import stage1a_runpod_firstlook_12reviews as original
import stage1a_codebook_v01_repeat_benchmark_20261116 as archival
import stage1a_stage2_reduced_20261113 as targeted

MODELS = ("qwen3.8:27b", "gemma4:31b-it-bf16")
MODEL_DIGESTS = {
    "qwen3.8:27b": "aaee06c39dcf2437cde036998d960e1fc1494b8191be7cc9657d01e509097813",
    "gemma4:31b-it-bf16": "df1661a2a6aaa94faf24bbaf23a691877a27d0e6052598f105a225618a079e76",
}
CATS = ("calm", "inviting", "safe")
DIRS = ("supports", "opposes")
TRACKS = ("E", "T")
OPTIONS = {"temperature": 0, "seed": 42, "num_ctx": 8192, "num_predict": 2048}
CODEBOOK = ROOT / "Docs/STAGE1A_PILOT_CODEBOOK_V0_5_2026-11-16.md"
PROMPT = ROOT / "Docs/STAGE1A_PILOT_PROMPT_V0_5_2026-11-16.md"
SCHEMA = ROOT / "configs/stage1a_pilot_directional_schema_v0_5.json"
OUT = ROOT / "reports/stage1a_codebook_v05_directional_2026-11-16"
# Researcher audit from current conversation, overriding earlier provisional labels.
AUDIT = {
    "K02:inviting": "uncertain", "K02:safe": "uncertain",
    "K03:inviting": "opposes", "K05:safe": "opposes",
    "U06:calm": "supports", "U06:inviting": "supports",
    "K01:calm": "none", "K01:inviting": "supports",
    "U05:inviting": "supports",
}

def sha(x):
    if not isinstance(x, str): x = json.dumps(x, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(x.encode("utf-8")).hexdigest()

def load():
    reviews = archival.load_cases()
    assert len(reviews) == 12
    assert len(targeted.TARGET) == 12
    return reviews

def system_and_schema():
    doc = PROMPT.read_text(encoding="utf-8")
    fence = chr(96) * 3
    system = doc.split("## Exact system prompt", 1)[1].split(fence + "text", 1)[1].split(fence, 1)[0].strip()
    assert system.count("{{CODEBOOK_TEXT}}") == 1
    codebook = CODEBOOK.read_text(encoding="utf-8")
    system = system.replace("{{CODEBOOK_TEXT}}", codebook)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["properties"]["codebook_version"]["const"] == "0.5"
    assert "claims" in str(schema) and "verdict" not in str(schema)
    return system, schema

def examine(obj, target):
    """Mechanical checks; keep parsed claims even when a case fails.
    Quotation validity does not guarantee semantic correctness.
    """
    errs = []
    claims = []
    if not isinstance(obj, dict) or set(obj) != {"codebook_version", "assessments"}:
        return ["top_level"], claims
    if obj["codebook_version"] != "0.5": errs.append("version")
    a = obj["assessments"]
    if not isinstance(a, list) or len(a) != 3: return errs + ["assessments_length"], claims
    for i, row in enumerate(a):
        if not isinstance(row, dict) or set(row) != {"emotion", "claims"}:
            errs.append("assessment_structure_" + str(i)); continue
        if row["emotion"] != CATS[i]:
            errs.append("category_order_" + str(i))
        if not isinstance(row["claims"], list):
            errs.append("claims_type_" + str(i)); continue
        for j, item in enumerate(row["claims"]):
            if not isinstance(item, dict) or set(item) != {"quote", "direction", "track", "referent", "reason"}:
                errs.append("claim_structure_" + str(i) + "_" + str(j)); continue
            if not all(isinstance(v, str) for v in item.values()):
                errs.append("claim_type_" + str(i) + "_" + str(j)); continue
            if item["direction"] not in DIRS or item["track"] not in TRACKS or item["referent"] not in original.REFERENTS or not item["reason"].strip():
                errs.append("claim_tags_" + str(i) + "_" + str(j))
            exact = bool(item["quote"]) and item["quote"] in target
            if not exact: errs.append("nonexact_quote_" + str(i) + "_" + str(j))
            claims.append({
                "emotion": row["emotion"], **item, "exact_target_quote": exact,
                "accepted_mechanically": exact and item["direction"] in DIRS and item["track"] in TRACKS
                and item["referent"] in original.REFERENTS and bool(item["reason"].strip())
            })
    return errs, claims

def file_for(model, rep):
    return OUT / (model.replace(":", "_") + "__repeat" + str(rep) + ".json")

def run(model, host):
    data = load()
    system, schema = system_and_schema()
    actual_digest = original.installed_digest(host, model)
    if actual_digest != MODEL_DIGESTS[model]:
        raise RuntimeError("MODEL DIGEST MISMATCH " + str((model, actual_digest)))
    manifest = {
        "protocol": "stage1a_v05_directional_matched_12", "model": model,
        "model_digest": actual_digest, "options": OPTIONS, "think": False, "keep_alive": "20m",
        "version": "0.5", "no_retries": True,
        "codebook_sha256": sha(CODEBOOK.read_text(encoding="utf-8")),
        "prompt_sha256": sha(PROMPT.read_text(encoding="utf-8")),
        "schema_sha256": sha(schema), "system_sha256": sha(system),
        "cases_sha256": sha(data), "targets_sha256": sha(targeted.TARGET),
        "evaluation_inputs": "same 12 real segments/reviews as v0.3",
        "pipeline": "no_gate_no_cascade",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    for repeat in (1, 2, 3):
        f = file_for(model, repeat)
        m = {**manifest, "repeat": repeat}
        if f.exists():
            old = json.loads(f.read_text(encoding="utf-8"))
            if old["manifest"] != m: raise RuntimeError("Manifest drift " + str(f))
            records = old["cases"]
        else: records = []
        seen = {r["case_id"] for r in records}
        for row in data:
            case = row["case_id"]
            if case in seen: continue
            target = targeted.TARGET[case]
            payload = {
                "model": model, "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": json.dumps({
                        "target_segment": target, "full_review_context": row["text"]}, ensure_ascii=False)},
                ],
                "format": schema, "stream": False, "think": False,
                "options": OPTIONS, "keep_alive": "20m",
            }
            start = time.monotonic()
            raw = ""; obj = None; errors = []; claims = []; meta = {}
            try:
                reply = original.request(host, "/api/chat", payload, timeout=300)
                raw = reply.get("message", {}).get("content", "")
                meta = {k: reply.get(k) for k in ("eval_count", "prompt_eval_count", "total_duration", "done_reason")}
                obj = json.loads(raw)
                errors, claims = examine(obj, target)
            except Exception as ex: errors = ["exception_" + repr(ex)]
            rec = {
                "case_id": case, "target": target, "raw": raw, "parsed": obj,
                "claims": claims, "validation_errors": errors,
                "strict_valid": len(errors) == 0,
                "seconds": round(time.monotonic() - start, 2), "metadata": meta,
            }
            records.append(rec)
            f.write_text(json.dumps({"manifest": m, "cases": records}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            print("CASE", model, repeat, case, "VALID" if not errors else ",".join(errors),
                  "claims", len(claims), "seconds", rec["seconds"], flush=True)
        if len(records) != 12: raise RuntimeError("Incomplete case count " + str(len(records)))
        print("REPEAT_COMPLETE", model, repeat,
              "strict_valid", sum(r["strict_valid"] for r in records), "of 12", flush=True)

def report():
    refs = archival.reference()
    refs.update(AUDIT)
    output = []
    all_detail = []
    for model in MODELS:
        repetitions = []
        for rep in (1, 2, 3):
            entries = json.loads(file_for(model, rep).read_text(encoding="utf-8"))["cases"]
            triples = {}
            for r in entries:
                grouped = {c: set() for c in CATS}
                for claim in r["claims"]:
                    if claim["accepted_mechanically"] and claim["emotion"] in CATS:
                        grouped[claim["emotion"]].add(claim["direction"])
                for emotion in CATS:
                    k = r["case_id"] + ":" + emotion
                    inferred = "/".join(sorted(grouped[emotion])) or "empty"
                    triples[k] = inferred
                    all_detail.append({
                        "model": model, "repeat": rep, "case_id": r["case_id"],
                        "emotion": emotion, "reference": refs.get(k), "claims_direction": inferred,
                        "case_strict_valid": r["strict_valid"],
                    })
            repetitions.append(triples)
            cnt = collections.Counter()
            for r in entries:
                cnt["calls"] += 1
                cnt["strict_valid"] += r["strict_valid"]
                cnt["invalid"] += not r["strict_valid"]
                cnt["all_claims"] += len(r["claims"])
                for c in r["claims"]:
                    cnt["quote_exact"] += c["exact_target_quote"]
                    cnt["nonexact_quote"] += not c["exact_target_quote"]
                    if c["accepted_mechanically"]:
                        cnt["mechanically_accepted_claims"] += 1
                        cnt["track_" + c["track"]] += 1
                        cnt["direction_" + c["direction"]] += 1
                cnt["total_emotion_slots"] += 3
                cnt["directional_emotion_slots"] += sum(bool(triples[r["case_id"] + ":" + e] != "empty") for e in CATS)
            usable = [
                x for x in all_detail
                if x["model"] == model and x["repeat"] == rep and x["case_strict_valid"]
                and x["reference"] in DIRS + ("none",)
            ]
            relevant = [x for x in usable if x["reference"] in DIRS]
            cnt["provisional_reference_slots"] = len(usable)
            cnt["provisional_directional_slots"] = len(relevant)
            cnt["provisional_recall_directional"] = sum(x["reference"] in x["claims_direction"].split("/") for x in relevant)
            cnt["provisional_nondirectional_slots"] = sum(x["reference"] == "none" for x in usable)
            cnt["provisional_nondirectional_empty"] = sum(x["reference"] == "none" and x["claims_direction"] == "empty" for x in usable)
            output.append({"model": model, "repeat": rep, "counts": dict(cnt),
                           "invalid_cases": {r["case_id"]: r["validation_errors"] for r in entries if not r["strict_valid"]}})
        same = [k for k in repetitions[0] if all(repetitions[j].get(k) is not None for j in (1, 2))]
        stable = [k for k in same if len({repetitions[j][k] for j in (0, 1, 2)}) == 1]
        output.append({"model": model, "repeatability": {
            "shared_slots": len(same), "stable_slot_directions": len(stable),
            "unstable": {k: [repetitions[j][k] for j in (0, 1, 2)] for k in same if k not in stable}}})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "claims_by_emotion.json").write_text(json.dumps(all_detail, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(output, indent=2, ensure_ascii=False))
    print("Provisional reference is NOT independent gold; no empirical precision without quote-level human audits.", flush=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("prepare", "run", "report"), required=True)
    parser.add_argument("--model", choices=MODELS, default=MODELS[0])
    parser.add_argument("--host", default="http://127.0.0.1:11434")
    a = parser.parse_args()
    if a.stage == "prepare":
        d = load(); system, schema = system_and_schema()
        for row in d: assert targeted.TARGET[row["case_id"]] in row["text"]
        print("READY", len(d), "reviews", "system_chars", len(system),
              "schema_hash", sha(schema), "model_digests", MODEL_DIGESTS)
        s = "The square was beautiful, but the staff told us we weren't allowed to stay."
        p = {"codebook_version":"0.5","assessments":[
            {"emotion":"calm","claims":[]},
            {"emotion":"inviting","claims":[
                {"quote":"The square was beautiful","direction":"supports","track":"E","referent":"place","reason":"Positive site appraisal"},
                {"quote":"the staff told us we weren't allowed to stay","direction":"opposes","track":"E","referent":"people","reason":"Visitor-facing exclusion"}]},
            {"emotion":"safe","claims":[]}
        ]}
        errors, claims = examine(p,s)
        assert not errors and len(claims) == 2
    elif a.stage == "run": run(a.model, a.host)
    else: report()

if __name__ == "__main__": main()
