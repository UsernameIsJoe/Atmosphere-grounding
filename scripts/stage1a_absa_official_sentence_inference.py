#!/usr/bin/env python3
"""Run existing ABSA relationship extractors on ORIGINAL review sentences.

No invented review text or synthetic controls. Original source offsets are
retained. One model-facing sentence per call. This is inference validation,
not independent model accuracy or a new NLI experiment.
"""
import argparse
import collections
import hashlib
import json
import pathlib
import sys
import time

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from stage1a_nli_checkpoint_screen import read_jsonl
from stage1a_relation_pilot import select_pilot, parse_triplets, make_relation, rule_extract, MODEL, INSTRUCTION
from stage1a_gts_joint_aste_probe import make_predictor, standardize

METHODS=("aos_t5","gts_joint_aste","dependency")


def source_sentences(reviews, indices, nlp):
    items=[]
    for row in indices:
        review=reviews[row]
        source=review["text"]
        segments=[]
        for sent in nlp(source).sents:
            a,b=sent.start_char,sent.end_char
            if not (0<=a<b<=len(source)) or source[a:b]!=sent.text:
                raise ValueError(f"Unverifiable sentence offset for review {row}")
            segments.append({"sentence_index":len(segments),"start":a,"end":b,"text":sent.text})
        if not segments and source.strip():
            raise ValueError(f"Nonempty review {row} produced no sentences")
        items.append({"row":row,"place_id":review["place_id"],
                      "review_index":review["review_index"],
                      "review":source,"sentences":segments})
    return items


def load_cases():
    import spacy
    nlp=spacy.load("en_core_web_sm")
    reviews=read_jsonl(ROOT/"data/processed/reviews.jsonl")
    rows=select_pilot(reviews,20)
    cases=source_sentences(reviews,rows,nlp)
    if len(cases)!=20 or len({x["row"] for x in cases})!=20:
        raise ValueError("Expected 20 fixed original reviews")
    return cases,nlp


def build_extractor(method,nlp):
    if method=="dependency":
        return lambda text: {"relations":rule_extract(text,nlp),
                             "parse_status":"dependency_rules",
                             "raw_generation":None,"token_count":None,
                             "input_truncated":False}
    if method=="gts_joint_aste":
        from transformers import AutoTokenizer
        tokenizer=AutoTokenizer.from_pretrained("gauneg/bert-gts-absa-triple")
        predict=make_predictor()
        def extract(text):
            tokens=tokenizer(text,add_special_tokens=True,truncation=False)["input_ids"]
            raw=predict(text)
            return {"relations":standardize(text,raw),
                    "parse_status":"gts_checkpoint_decoder",
                    "raw_generation":raw,"token_count":len(tokens),
                    "input_truncated":len(tokens)>128}
        return extract
    if method=="aos_t5":
        import torch
        from transformers import AutoTokenizer,AutoModelForSeq2SeqLM
        torch.set_num_threads(min(4,torch.get_num_threads()))
        tokenizer=AutoTokenizer.from_pretrained(MODEL)
        model=AutoModelForSeq2SeqLM.from_pretrained(MODEL).eval()
        def extract(text):
            prompt=INSTRUCTION+text+" \noutput:"
            tokens=tokenizer(prompt,return_tensors="pt",truncation=False)
            n_tokens=len(tokens["input_ids"][0])
            if n_tokens>512:
                # Fail explicitly instead of pretending a truncated passage was processed.
                return {"relations":[],"parse_status":"skipped_input_too_long",
                        "raw_generation":None,"token_count":n_tokens,"input_truncated":True}
            with torch.inference_mode():
                ids=model.generate(**tokens,max_new_tokens=250,num_beams=1,do_sample=False)
            raw=tokenizer.decode(ids[0],skip_special_tokens=True)
            pairs,status=parse_triplets(raw)
            return {"relations":[make_relation(text,a,o,p,"aos_t5",
                    raw={"generation":raw}) for a,o,p in pairs],
                    "parse_status":status,"raw_generation":raw,
                    "token_count":n_tokens,"input_truncated":False}
        return extract
    raise ValueError(method)


def rebase_relation(rel,offset,source):
    result=json.loads(json.dumps(rel,ensure_ascii=False))
    for part in ("aspect","opinion"):
        span=result[part]
        if isinstance(span.get("start"),int) and isinstance(span.get("end"),int):
            span["start"]+=offset
            span["end"]+=offset
            if source[span["start"]:span["end"]]!=span["text"]:
                raise ValueError("Incorrect rebased original-review aspect/opinion span")
    return result


def evaluate(method,cases,extract):
    output=[]
    for count,case in enumerate(cases,1):
        rels=[]
        sentences=[]
        for s in case["sentences"]:
            pred=extract(s["text"])
            offset=s["start"]
            adjusted=[rebase_relation(r,offset,case["review"]) for r in pred["relations"]]
            rels.extend(adjusted)
            sentences.append({**s,"extraction":{**pred,"relations":adjusted}})
        output.append({**{k:v for k,v in case.items() if k!="sentences"},
                       "sentences":sentences,
                       "extraction":{"relations":rels,
                                     "parse_status":"assembled_source_sentences"}})
        print(f"{method}: {count}/{len(cases)} original reviews",flush=True)
    return output


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--method",choices=METHODS,required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    cases,nlp=load_cases()
    extract=build_extractor(args.method,nlp)
    started=time.monotonic()
    outputs=evaluate(args.method,cases,extract)
    dest=pathlib.Path(args.output)
    dest.mkdir(parents=True,exist_ok=True)
    with (dest/"review_cases.jsonl").open("w",encoding="utf-8") as handle:
        for item in outputs:
            handle.write(json.dumps(item,ensure_ascii=False)+"\n")
    summary={
        "method":args.method,
        "sample_rows":[c["row"] for c in cases],
        "sample_sha256":hashlib.sha256(json.dumps([c["row"] for c in cases]).encode()).hexdigest(),
        "reviews":len(cases),
        "original_sentences":sum(len(c["sentences"]) for c in cases),
        "relationship_count":sum(len(c["extraction"]["relations"]) for c in outputs),
        "grounded_relationship_count":sum(r.get("grounded",False) for c in outputs for r in c["extraction"]["relations"]),
        "sentences_with_output":sum(bool(s["extraction"]["relations"]) for c in outputs for s in c["sentences"]),
        "sentences_input_truncated":sum(s["extraction"]["input_truncated"] for c in outputs for s in c["sentences"]),
        "sentences_unparsed":sum(s["extraction"]["parse_status"]=="unparsed_generation" for c in outputs for s in c["sentences"]),
        "wall_seconds":round(time.monotonic()-started,2),
        "input_protocol":"verbatim spaCy en_core_web_sm sentence spans; single sentence per model call; original offset rebasing",
        "source":"data/processed/reviews.jsonl using the fixed 20 review row selector from prior experiment",
        "caveat":"No synthesized review content; source-offset match is not semantic precision; no independently annotated accuracy",
    }
    (dest/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,indent=2))


if __name__=="__main__":
    main()
