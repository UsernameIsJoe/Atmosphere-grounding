#!/usr/bin/env python3
"""Compare aspect extraction methods on identical place reviews (no human labels).

Methods: joint DeBERTa ABSA (existing), published restaurant-domain SetFitABSA
(checkpoint transfer probe), and spaCy noun chunks (not sentiment ABSA).
Retains full source review, source offsets, and explicit unmatched text.
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

MODEL_IDS = {
    "deberta_absa": "yangheng/deberta-v3-base-end2end-absa",
    "setfit_absa": "tomaarsen/setfit-absa-bge-small-en-v1.5-restaurants-aspect + ...-polarity",
    "spacy_noun": "en_core_web_sm",
}
# Explicit synthetic assertions are *not* independent human ground truth.
CONTROLLED = [
    {"id":"negated_noise","text":"The park is not quiet; sirens make it stressful.","target_text":"sirens"},
    {"id":"non_noun_atmosphere","text":"It feels peaceful and calming here.","target_text":"peaceful"},
    {"id":"mixed_sensory","text":"The gardens are beautiful, but the traffic is deafening.","target_text":"traffic"},
    {"id":"reviewer_unrelated","text":"I was happy because I found my lost phone.","target_text":"phone"},
    {"id":"direct_welcome","text":"The friendly entrance welcomes every visitor.","target_text":"entrance"},
    {"id":"negative_safety","text":"Broken glass covers the sidewalk and makes it dangerous.","target_text":"glass"},
    {"id":"no_nominal_aspect","text":"Relaxing, quiet, and serene.","target_text":"serene"},
]


def sentences(text, nlp=None):
    if nlp is not None:
        doc=nlp(text)
        return [(s.start_char,s.end_char,s.text) for s in doc.sents]
    spans=[]
    for m in re.finditer(r"[^.!?\n]+(?:[.!?]+|$)", text):
        a,b=m.span()
        while a<b and text[a].isspace(): a+=1
        while b>a and text[b-1].isspace(): b-=1
        if b>a:spans.append((a,b,text[a:b]))
    return spans or [(0,len(text),text)]


def attach_sentences(text, spans, sentence_spans):
    items=[]
    for x in spans:
        a,b=x["start"],x["end"]
        if not isinstance(a,int) or not isinstance(b,int) or not (0<=a<b<=len(text)):
            raise ValueError(f"Invalid offset {a}:{b} for {x}")
        if text[a:b] != x["aspect"]:
            raise ValueError(f"Unverifiable aspect offset: {text[a:b]!r} != {x['aspect']!r}")
        context=next(({"start":i,"end":j,"text":sentence} for i,j,sentence in sentence_spans
                      if i<=a<j),None)
        items.append({**x,"context":context})
    return items


def align_setfit(text, predictions):
    """Align SetFit's string spans, recording ambiguity instead of inventing offsets."""
    out=[]
    usage=collections.Counter()
    for item in predictions:
        word=item.get("span","")
        if not word:continue
        matches=[m for m in re.finditer(re.escape(word),text,re.IGNORECASE)]
        if not matches:
            out.append({"aspect":word,"polarity":item.get("polarity"),"start":None,"end":None,
                        "alignment":"unmatched"})
            continue
        occurrence=usage[word.lower()]
        if occurrence >= len(matches):
            out.append({"aspect":word,"polarity":item.get("polarity"),"start":None,"end":None,
                        "alignment":"exhausted_ambiguous"})
            continue
        m=matches[occurrence]
        usage[word.lower()]+=1
        out.append({"aspect":text[m.start():m.end()],"polarity":item.get("polarity"),
                    "start":m.start(),"end":m.end(),
                    "alignment":"unique" if len(matches)==1 else "ambiguous_order_assumption"})
    return out


def extractor_for(method):
    if method=="deberta_absa":
        from transformers import AutoTokenizer,AutoModelForTokenClassification,pipeline
        name="yangheng/deberta-v3-base-end2end-absa"
        tok=AutoTokenizer.from_pretrained(name,use_fast=True)
        model=AutoModelForTokenClassification.from_pretrained(name).eval()
        pipe=pipeline("token-classification",model=model,tokenizer=tok,
                      aggregation_strategy="simple",device=-1)
        def extract(text):
            return [{"aspect":text[int(x["start"]):int(x["end"])],
                     "start":int(x["start"]),"end":int(x["end"]),
                     "polarity":x.get("entity_group"),"confidence":float(x.get("score",0)),
                     "alignment":"model_offsets"} for x in pipe(text)
                    if x.get("start") is not None and x.get("end") is not None
                    and int(x["end"])<=len(text) and int(x["start"])<int(x["end"])]
        return extract,None
    if method=="setfit_absa":
        from setfit import AbsaModel
        import spacy
        model=AbsaModel.from_pretrained(
            "tomaarsen/setfit-absa-bge-small-en-v1.5-restaurants-aspect",
            "tomaarsen/setfit-absa-bge-small-en-v1.5-restaurants-polarity",
            spacy_model="en_core_web_sm")
        nlp=spacy.load("en_core_web_sm")
        def extract(text):
            pred=model.predict(text)
            if isinstance(pred,list) and pred and isinstance(pred[0],list):
                pred=pred[0]
            return align_setfit(text,pred)
        return extract,nlp
    if method=="spacy_noun":
        import spacy
        nlp=spacy.load("en_core_web_sm")
        def extract(text):
            doc=nlp(text)
            return [{"aspect":chunk.text,"start":chunk.start_char,"end":chunk.end_char,
                     "polarity":None,"confidence":None,"alignment":"spacy_offsets"}
                    for chunk in doc.noun_chunks]
        return extract,nlp
    raise ValueError(method)


def annotate(text, extractor, nlp):
    raw=extractor(text)
    valid=[x for x in raw if isinstance(x.get("start"),int) and isinstance(x.get("end"),int)]
    unmatched=[x for x in raw if x not in valid]
    structured=attach_sentences(text,valid,sentences(text,nlp))
    retained={(x["context"]["start"],x["context"]["end"]) for x in structured if x["context"]}
    all_sentences=sentences(text,nlp)
    excluded=[{"start":a,"end":b,"text":s} for a,b,s in all_sentences if (a,b) not in retained]
    return {
        "aspects":structured,"unaligned_aspects":unmatched,
        "all_sentences":[{"start":a,"end":b,"text":s} for a,b,s in all_sentences],
        "sentences_with_aspects":len(retained),
        "total_sentences":len(all_sentences),
        "sentences_without_aspects":excluded,
    }


def summarize(rows,controls,method,elapsed):
    counts=[]
    total_sentences=0
    kept_sentences=0
    no_aspects=0
    unaligned=0
    aspects_by_review=[]
    for r in rows:
        a=r["extraction"]
        n=len(a["aspects"])
        counts.append(n)
        aspects_by_review.append({"row":r["row"],"n_aspects":n,
                                  "n_omitted_sentences":len(a["sentences_without_aspects"])})
        no_aspects+=int(n==0)
        total_sentences+=a["total_sentences"]
        kept_sentences+=a["sentences_with_aspects"]
        unaligned+=len(a["unaligned_aspects"])
    return {
        "method":method,"model":MODEL_IDS[method],"reviews":len(rows),
        "locations":len({x["place_id"] for x in rows}),
        "total_aspect_spans":sum(counts),"mean_spans_per_review":round(sum(counts)/len(rows),3),
        "reviews_without_spans":no_aspects,
        "total_sentences":total_sentences,"sentences_with_aspects":kept_sentences,
        "sentence_retention_fraction_if_hard_filtered":round(kept_sentences/total_sentences,4) if total_sentences else None,
        "unmatched_spans":unaligned,"runtime_seconds":round(elapsed,2),
        "controls":controls,"review_coverage":aspects_by_review,
        "interpretation_warnings":[
            "Noun chunks are candidate targets only; spaCy noun detection is NOT an ABSA model.",
            "SetFit weights are trained on restaurant reviews: transfer to outdoor/public-place texts is unvalidated.",
            "No independent reference spans or atmosphere labels; span counts and sentence retention are NOT precision, recall, or accuracy.",
            "Not all atmosphere observations are nominal aspects; missing an adjective-only sentence can be conceptually important.",
            "The full review is always saved. Dropped sentences are counterfactual for a filter, not discarded from experimental records.",
            "SetFit string-only spans with repeated occurrences use an explicit order assumption, never treated as verified unique offsets.",
            "Sentiment polarity is metadata and is NOT mapped to any atmosphere class.",
        ],
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--method",required=True,choices=tuple(MODEL_IDS))
    ap.add_argument("--limit",type=int,default=50)
    ap.add_argument("--output")
    args=ap.parse_args()
    if args.limit!=50:raise ValueError("This screening protocol requires exact prespecified 50-review sample")
    reviews=read_jsonl(ROOT/"data/processed/reviews.jsonl")
    indices=select_rows(reviews,50)
    output=ROOT/(args.output or f"reports/stage1a_absa_screen_{args.method}")
    output.mkdir(parents=True,exist_ok=True)
    manifest={
        "method":args.method,"model":MODEL_IDS[args.method],
        "review_rows":indices,
        "review_ids":[{"row":i,"place_id":reviews[i]["place_id"],"review_index":reviews[i]["review_index"]} for i in indices],
        "sample_hash":hashlib.sha256(json.dumps(indices).encode()).hexdigest(),
        "selection_source":"scripts/stage1a_nli_checkpoint_screen.py deterministic 50-row selector",
        "limitations":"Not independent ground truth; aspect discovery only; no NLI decisions in this experiment",
    }
    (output/"sample_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    extract,nlp=extractor_for(args.method)
    start=time.perf_counter()
    rows=[]
    with (output/"review_cases.jsonl").open("w",encoding="utf-8") as handle:
        for i in indices:
            r=reviews[i]
            record={"row":i,"place_id":r["place_id"],"review_index":r["review_index"],
                    "review":r["text"],"extraction":annotate(r["text"],extract,nlp)}
            rows.append(record)
            handle.write(json.dumps(record,ensure_ascii=False)+"\n")
            handle.flush()
            if len(rows)%10==0:print(f"Completed {len(rows)}/{len(indices)} reviews",flush=True)
    controls=[]
    for item in CONTROLLED:
        a=annotate(item["text"],extract,nlp)
        target=item["target_text"]
        controls.append({"id":item["id"],"text":item["text"],"diagnostic_target":target,
                         "target_found_as_span":any(target.casefold() in x["aspect"].casefold()
                                                    for x in a["aspects"]),
                         "extraction":a})
    (output/"controlled_cases.json").write_text(json.dumps(controls,indent=2),encoding="utf-8")
    summary=summarize(rows,[{"id":c["id"],"diagnostic_target":c["diagnostic_target"],
                              "target_found_as_span":c["target_found_as_span"]} for c in controls],
                      args.method,time.perf_counter()-start)
    (output/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps({k:summary[k] for k in (
        "method","reviews","locations","total_aspect_spans","reviews_without_spans",
        "sentence_retention_fraction_if_hard_filtered","unmatched_spans","runtime_seconds")},indent=2),flush=True)


if __name__=="__main__":main()
