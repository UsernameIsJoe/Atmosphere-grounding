#!/usr/bin/env python3
"""Stage 1A M1: source-grounded aspect--opinion relation extraction pilot.

Compare a pretrained generative aspect/opinion/sentiment triplet checkpoint
against a transparent dependency-rule baseline. No NLI, emotional scoring,
or independently validated accuracy. Generated phrases must match exact
source spans to count as grounded relations.
"""
import argparse
import collections
import hashlib
import json
import pathlib
import re
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage1a_nli_checkpoint_screen import read_jsonl, select_rows

MODEL = "tafseer-nayeem/aspect-opinion-sentiment_AOS-triplet"
INSTRUCTION = (
    "Definition: The output will be the aspects (both implicit and explicit), "
    "the corresponding opinion/describing terms, and the sentiment polarity (positive, negative, neutral). "
    "Use the format aspect:opinion:sentiment.\n\n"
    "Example 1-\ninput: Free Wi-Fi throughout the hotel\n"
    "output: wi-fi:free:positive\n\n"
    "Now complete the following example-\ninput: "
)
# Registered before M1 model output is seen; prioritize prior known failure cases.
DIAGNOSTIC_ROWS = (55, 74, 97, 113, 123, 139, 181, 187)
SYNTHETIC = (
    ("two_targets", "The gardens are beautiful, but the traffic is deafening."),
    ("negation", "The park is not quiet; sirens make the atmosphere stressful."),
    ("safety", "Broken glass covers the sidewalk and makes the path dangerous."),
    ("welcoming", "The welcoming entrance makes the plaza inviting."),
    ("mixed", "The benches are comfortable but the lighting is harsh."),
    ("subjective", "I felt happy because I found my lost phone."),
    ("implicit", "Relaxing, quiet, and serene."),
    ("scope", "The trees are beautiful, but the park is noisy at night."),
)


def select_pilot(reviews, n=20):
    if n < len(DIAGNOSTIC_ROWS):
        raise ValueError("Sample size too small for preregistered diagnostic rows")
    screen = select_rows(reviews, 50)
    selected = list(DIAGNOSTIC_ROWS)
    selected += [i for i in screen if i not in selected][: n - len(selected)]
    if len(selected) != n:
        raise RuntimeError("Pilot sample unexpectedly short")
    return selected


def exact_occurrences(text, fragment):
    if not isinstance(fragment, str) or not fragment.strip():
        return []
    # Exact case-insensitive literal matching; never silently substitute words.
    return [(m.start(), m.end()) for m in re.finditer(re.escape(fragment.strip()), text, re.I)]


def locate(text, phrase):
    matches = exact_occurrences(text, phrase)
    if len(matches) == 1:
        a, b = matches[0]
        return {"text": text[a:b], "start": a, "end": b, "status": "unique"}
    return {"text": phrase, "start": None, "end": None,
            "status": "missing" if not matches else "ambiguous_multiple_occurrences",
            "matches": len(matches)}


def make_relation(text, aspect, opinion, polarity, method, raw=None):
    a, o = locate(text, aspect), locate(text, opinion)
    return {
        "aspect": a, "opinion": o, "polarity": polarity,
        "method": method,
        "grounded": a["status"] == "unique" and o["status"] == "unique",
        "raw": raw,
    }


def parse_triplets(raw):
    """Accept only an explicitly structured array or a clearly delimited list.
    Malformed generations are saved, never hallucinated into valid relations.
    """
    raw = raw.strip()
    try:
        obj = json.loads(raw)
    except (ValueError, TypeError):
        # Model-card prompt also uses the aspect:opinion:sentiment format.
        # Parse complete and polarity-labeled lines only.
        triples=[]
        for line in raw.splitlines():
            parts=[x.strip() for x in line.strip().split(":")]
            if len(parts)==3 and all(parts) and parts[2].lower() in ("positive","negative","neutral"):
                triples.append(tuple(parts))
        return triples, "parsed_colon_triplets" if triples else "unparsed_generation"
    if isinstance(obj, dict):
        obj = obj.get("triplets", obj.get("results"))
    if not isinstance(obj, list):
        return [], "not_triplet_list"
    pairs = []
    for item in obj:
        if isinstance(item, (list, tuple)) and len(item) >= 3:
            a, o, p = item[:3]
        elif isinstance(item, dict):
            a = item.get("aspect")
            o = item.get("opinion")
            p = item.get("sentiment", item.get("polarity"))
        else:
            continue
        if isinstance(a, str) and isinstance(o, str) and isinstance(p, str):
            pairs.append((a.strip(), o.strip(), p.strip()))
    return pairs, "parsed" if pairs or not obj else "no_valid_triplets"


def rule_extract(text, nlp):
    """Transparent high-precision-ish baseline; NOT full ASTE.
    Links adjectival predicate to subject, adjectival noun modifier to head,
    and descriptive verb/copula complements. No free-text generation.
    """
    doc = nlp(text)
    output = []
    seen = set()

    def add(noun, opinion, rule):
        if noun is None or opinion is None:
            return
        if noun.pos_ not in ("NOUN", "PROPN") or opinion.pos_ not in ("ADJ", "VERB"):
            return
        key = (noun.idx, opinion.idx)
        if key in seen:
            return
        seen.add(key)
        a = text[noun.idx:noun.idx+len(noun)]
        # Include explicit negator only when adjoining and modifying opinion.
        candidates = [c for c in opinion.children if c.dep_ == "neg" or c.lower_ == "not"]
        start = min([opinion.idx] + [c.idx for c in candidates])
        end = opinion.idx+len(opinion)
        o = text[start:end]
        result=make_relation(text,a,o,None,"spacy_dependency",raw={"rule":rule})
        # Exact token offset is authoritative even if repeated token strings occur.
        result["aspect"]={"text":a,"start":noun.idx,"end":noun.idx+len(noun),"status":"token_offset"}
        result["opinion"]={"text":o,"start":start,"end":end,"status":"token_offset"}
        result["grounded"]=True
        output.append(result)

    for token in doc:
        if token.pos_ == "ADJ" and token.dep_ == "amod":
            add(token.head, token, "amod")
        if token.pos_ == "ADJ" and token.dep_ in ("acomp", "attr", "ROOT", "conj"):
            candidate = next((c for c in token.head.children if c.dep_ in ("nsubj", "nsubjpass")), None)
            if candidate is None and token.head.pos_ in ("NOUN", "PROPN"):
                candidate = token.head
            if candidate is None and token.dep_ == "conj":
                parent=token.head
                candidate=next((c for c in parent.head.children if c.dep_ in ("nsubj", "nsubjpass")),None)
            add(candidate, token, "predicate")
        if token.pos_ == "VERB":
            subject=next((c for c in token.children if c.dep_ in ("nsubj","nsubjpass")), None)
            if subject:
                add(subject, token, "verb_subject")
    return output


def generative_extractor():
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    import torch
    torch.set_num_threads(min(4, torch.get_num_threads()))
    tok=AutoTokenizer.from_pretrained(MODEL)
    model=AutoModelForSeq2SeqLM.from_pretrained(MODEL).eval()
    def extract(text):
        encoded=tok(INSTRUCTION + text + " \noutput:",return_tensors="pt",truncation=True,max_length=512)
        with torch.inference_mode():
            ids=model.generate(**encoded,max_new_tokens=180,num_beams=1,do_sample=False)
        raw=tok.decode(ids[0],skip_special_tokens=True)
        pairs,reason=parse_triplets(raw)
        return {
            "relations":[make_relation(text,a,o,p,"aos_t5",raw={"generation":raw}) for a,o,p in pairs],
            "generation":raw,
            "parse_status":reason,
        }
    return extract


def run():
    ap=argparse.ArgumentParser()
    ap.add_argument("--method",choices=("aos_t5","dependency"),required=True)
    ap.add_argument("--output",default=None)
    ap.add_argument("--n",type=int,default=20)
    args=ap.parse_args()
    if args.n!=20: raise ValueError("Pilot is preregistered for n=20")
    reviews=read_jsonl(ROOT/"data/processed/reviews.jsonl")
    selected=select_pilot(reviews,args.n)
    dest=ROOT/(args.output or f"reports/stage1a_relation_pilot_{args.method}")
    dest.mkdir(parents=True,exist_ok=True)
    manifest={
        "method":args.method,
        "model_or_parser":MODEL if args.method=="aos_t5" else "spacy/en_core_web_sm",
        "rows":selected,
        "sample_sha256":hashlib.sha256(json.dumps(selected).encode()).hexdigest(),
        "n_reviews":len(selected),
        "n_locations":len({reviews[i]["place_id"] for i in selected}),
        "synthetic_ids":[x[0] for x in SYNTHETIC],
        "selection":"8 preselected BART/ABSA difficult cases then 12 from deterministic 50-review screening set",
        "caveat":"No human gold labels; model-generated triplets are not accepted as grounded unless exact source strings match uniquely",
    }
    (dest/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    if args.method=="aos_t5":
        extract=generative_extractor()
    else:
        import spacy
        nlp=spacy.load("en_core_web_sm")
        extract=lambda text: {"relations":rule_extract(text,nlp),"generation":None,"parse_status":"dependency_rules"}
    start=time.monotonic()
    records=[]
    with (dest/"review_cases.jsonl").open("w",encoding="utf-8") as handle:
        for i,idx in enumerate(selected,1):
            review=reviews[idx]
            entry={"row":idx,"place_id":review["place_id"],
                   "review_index":review["review_index"],"review":review["text"],
                   "extraction":extract(review["text"])}
            records.append(entry)
            handle.write(json.dumps(entry,ensure_ascii=False)+"\n")
            handle.flush()
            print(f"Completed {i}/{len(selected)}",flush=True)
    controls=[]
    for name, sentence in SYNTHETIC:
        controls.append({"id":name,"text":sentence,"extraction":extract(sentence)})
    (dest/"controlled_cases.json").write_text(json.dumps(controls,ensure_ascii=False,indent=2),encoding="utf-8")
    relations=[rel for record in records for rel in record["extraction"]["relations"]]
    summary={
        **manifest,
        "n_relations":len(relations),
        "n_grounded":sum(rel["grounded"] for rel in relations),
        "n_ungrounded":sum(not rel["grounded"] for rel in relations),
        "n_reviews_without_relations":sum(not r["extraction"]["relations"] for r in records),
        "parse_status_counts":dict(collections.Counter(r["extraction"]["parse_status"] for r in records)),
        "elapsed_seconds":round(time.monotonic()-start,2),
        "caveats":[
            "Automatic parsing or grammatical-rule outputs are not accuracy against human reference.",
            "String matching verifies literal grounding only, not correctness of aspect-to-opinion relation.",
            "Generative checkpoint is domain-mismatched; it may normalize or invent words, flagged not repaired.",
            "Rules may extract non-atmospheric target/opinion pairs; no emotion scoring or NLI performed.",
            "Missing adjective-only implicit observations are expected for nominal aspect methods.",
        ],
    }
    (dest/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps({k:summary[k] for k in ("method","n_reviews","n_relations","n_grounded","n_ungrounded","n_reviews_without_relations","elapsed_seconds")},indent=2),flush=True)


if __name__=="__main__":
    run()
