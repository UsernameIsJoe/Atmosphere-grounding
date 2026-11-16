#!/usr/bin/env python3
"""Full-REVIEW v0.3 place-level eligibility gate before segmentation.
No topic classification, emotion inference, segmentation, or cascade.
Python standard library; Ollama /api/chat when explicitly --stage run.

Examples:
  python scripts/stage1a_review_eligibility_gate_v03_20261116.py --stage prepare
  python scripts/stage1a_review_eligibility_gate_v03_20261116.py --stage run --model qwen3.8:27b --limit 12
  python scripts/stage1a_review_eligibility_gate_v03_20261116.py --stage report
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PROMPT = ROOT / "Docs/STAGE1A_REVIEW_ELIGIBILITY_GATE_PROMPT_V0_3_2026-11-16.md"
SCHEMA = ROOT / "configs/stage1a_review_eligibility_gate_v01.json"
CODEBOOK = ROOT / "Docs/STAGE1A_REVIEW_ELIGIBILITY_GATE_CODEBOOK_V0_3_2026-11-16.md"
DEFAULT_INPUT = ROOT / "research_audit/stage1a_runpod_12review_firstlook_2026-11-13/cases.jsonl"
DEFAULT_OUTPUT = ROOT / "reports/stage1a_review_eligibility_gate_v03_2026-11-16"
OPTIONS = {"temperature": 0, "seed": 42, "num_ctx": 8192, "num_predict": 512}
PLACEHOLDER = "<original complete review text>"

def filehash(path):
    return sha256(Path(path).read_bytes()).hexdigest()

def parse_prompt():
    doc = PROMPT.read_text(encoding="utf-8")
    fence = chr(96) * 3
    prompt = doc.split("## Exact system message", 1)[1].split(fence + "text", 1)[1].split(fence, 1)[0].strip()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert "strict but recall-conscious eligibility gate" in prompt and "anchor_quote" in schema["properties"]
    assert not any(k in schema["properties"] for k in ("category", "emotion", "track", "verdict"))
    return prompt, schema

def rows(path, limit):
    seen = set()
    n = 0
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip(): continue
            obj = json.loads(line)
            if not isinstance(obj, dict) or not isinstance(obj.get("text"), str) or not obj["text"].strip():
                raise ValueError(f"Invalid text at line {line_no}")
            if "case_id" in obj:
                rid = str(obj["case_id"])
            elif "place_id" in obj and "review_index" in obj:
                rid = str(obj["place_id"]) + "::" + str(obj["review_index"])
            else:
                raise ValueError(f"Missing stable case_id or place_id + review_index at line {line_no}")
            if rid in seen: raise ValueError("Duplicate review id " + rid)
            seen.add(rid)
            yield {"review_id": rid, "text": obj["text"], "source_line": line_no,
                   "place_id": obj.get("place_id"), "review_index": obj.get("review_index")}
            n += 1
            if limit and n >= limit: break

def validate(answer, text):
    if not isinstance(answer, dict) or set(answer) != {"keep", "anchor_quote", "reason"}:
        return ["structure"]
    errs = []
    if type(answer["keep"]) is not bool: errs.append("keep_type")
    if not isinstance(answer["reason"], str) or not answer["reason"].strip(): errs.append("reason")
    if not isinstance(answer["anchor_quote"], str): errs.append("quote_type")
    elif answer["keep"] is True and (not answer["anchor_quote"] or answer["anchor_quote"] not in text):
        errs.append("nonexact_keep_quote")
    elif answer["keep"] is False and answer["anchor_quote"] != "": errs.append("reject_must_have_empty_quote")
    return errs

def chat(host, payload, timeout=180):
    url = host.rstrip("/") + "/api/chat"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(url, data, headers={"Content-Type":"application/json"}, method="POST")
    with urlopen(req, timeout=timeout) as res: return json.load(res)

def read_jsonl(path):
    if not path.exists(): return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def run(args):
    sys_prompt, schema = parse_prompt()
    originals = list(rows(args.input, args.limit))
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "protocol":"stage1a_full_review_gate_v03", "input":str(args.input),
        "input_sha256":filehash(args.input), "prompt_sha256":filehash(PROMPT),
        "schema_sha256":filehash(SCHEMA), "codebook_sha256":filehash(CODEBOOK), "model":args.model, "host":args.host,
        "options":OPTIONS, "limit":args.limit, "scope":"full_review_before_segmentation",
        "no_retry":True, "gate_status":"experimental_unvalidated",
    }
    mp = args.output / "manifest.json"
    if mp.exists() and json.loads(mp.read_text(encoding="utf-8")) != manifest:
        raise ValueError("Existing manifest differs; choose a fresh output directory")
    if not mp.exists(): mp.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    fp = args.output / "decisions.jsonl"
    done = {r["review_id"] for r in read_jsonl(fp)}
    for entry in originals:
        if entry["review_id"] in done: continue
        start = time.monotonic()
        raw = ""; parsed = None; errors = []; meta = {}
        try:
            response = chat(args.host, {
                "model":args.model, "messages":[
                    {"role":"system","content":sys_prompt},
                    {"role":"user","content":json.dumps({"review_text":entry["text"]},ensure_ascii=False)},
                ],"format":schema, "stream":False, "think":False, "options":OPTIONS,
            }, timeout=args.timeout)
            raw = response.get("message",{}).get("content","")
            meta = {k:response.get(k) for k in ("prompt_eval_count","eval_count","total_duration","done_reason")}
            parsed = json.loads(raw)
            errors = validate(parsed,entry["text"])
        except Exception as ex: errors = [repr(ex)]
        record = {**{k:v for k,v in entry.items() if k != "text"},
                  "review_sha256":sha256(entry["text"].encode("utf-8")).hexdigest(),
                  "review_text":entry["text"],"raw":raw,"parsed":parsed,
                  "errors":errors,"strict_valid":not errors,
                  "seconds":round(time.monotonic()-start,2),"metadata":meta}
        with fp.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record,ensure_ascii=False) + "\n")
        label = "INVALID" if errors else "KEEP" if parsed["keep"] else "REJECT"
        print(entry["review_id"],label, "elapsed",record["seconds"],flush=True)
    print("Archived decisions to",fp)

def report(args):
    result = read_jsonl(args.output / "decisions.jsonl")
    print(json.dumps({
        "total":len(result),
        "valid":sum(x["strict_valid"] for x in result),
        "keep":sum(x["strict_valid"] and x["parsed"]["keep"] for x in result),
        "reject":sum(x["strict_valid"] and not x["parsed"]["keep"] for x in result),
        "invalid":sum(not x["strict_valid"] for x in result),
        "note":"This is not a semantic performance assessment; no human review-level labels are available.",
    },indent=2))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stage",required=True,choices=("prepare","run","report"))
    p.add_argument("--input",type=Path,default=DEFAULT_INPUT)
    p.add_argument("--output",type=Path,default=DEFAULT_OUTPUT)
    p.add_argument("--model",default="qwen3:8b")
    p.add_argument("--host",default="http://127.0.0.1:11434")
    p.add_argument("--limit",type=int,default=0,help="0 = all reviews")
    p.add_argument("--timeout",type=int,default=180)
    args=p.parse_args()
    if args.limit < 0: p.error("--limit must be nonnegative")
    if args.stage=="prepare":
        prompt,schema=parse_prompt()
        source=list(rows(args.input,args.limit))
        print(json.dumps({"reviews":len(source),"prompt_chars":len(prompt),
            "prompt_sha256":filehash(PROMPT),"schema_sha256":filehash(SCHEMA),"codebook_sha256":filehash(CODEBOOK),
            "input_sha256":filehash(args.input),"schema_keys":list(schema["properties"]),
            "example_review_ids":[x["review_id"] for x in source[:5]]},indent=2))
    elif args.stage=="run":run(args)
    else:report(args)

if __name__=="__main__": main()
