#!/usr/bin/env python3
"""Research comparison: A direct NLI, B multiple hypotheses, C pretrained ABSA -> NLI.

Uses the 30 diagnostic real-review samples and provisional annotations from
scripts/stage1a_text_pilot.py. This is NOT a validated human benchmark.
Run: python scripts/stage1a_compare_abc.py --output reports/stage1a_abc
Requires: torch, transformers<5, sentencepiece, protobuf.
"""
import argparse
import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage1a_text_pilot import GOLD, CATS, HYPOTHESES, read_jsonl

# Prespecified exploratory hypotheses. Not calibrated / theory-validated.
HYPOTHESES_MULTI = {
 "calm": [
  "The location is peaceful and calm.",
  "The location is quiet, without disruptive noise.",
  "The location offers a relaxing atmosphere for visitors."
 ],
 "inviting": [
  "The location feels welcoming to visitors.",
  "The location offers comfortable places for people to spend time.",
  "The location encourages people to enter, stay, and enjoy the space."
 ],
 "safe": [
  "The location is physically safe for visitors.",
  "Visitors are protected from dangerous conditions at the location.",
  "Visitors can use the location without a substantial risk of physical injury."
 ]
}

LABEL_MAP = {"ENTAILMENT": "S", "CONTRADICTION": "C", "NEUTRAL": "U"}
def segments(text):
 """Sentence spans with original offsets, so aspects retain context."""
 spans=[]
 for match in re.finditer(r"[^.!?\n]+(?:[.!?]+|$)",text):
  s=match.group().strip()
  if s:spans.append((match.start(),match.end(),s))
 return spans or [(0,len(text),text)]

def pair_nli(tokenizer,model,premise,hypothesis,torch):
 encoded=tokenizer(premise,hypothesis,return_tensors="pt",truncation=True,max_length=512)
 with torch.inference_mode():
  logits=model(**encoded).logits[0]
 probs=torch.softmax(logits,dim=-1).tolist()
 result={LABEL_MAP.get(model.config.id2label[i].upper(),model.config.id2label[i].upper()):float(v)
         for i,v in enumerate(probs)}
 if set(result)!={"S","C","U"}:
  raise RuntimeError("Unexpected NLI label map: "+str(result))
 return result

def decide(probs):
 return max(("S","C","U"),key=lambda k:probs[k])
def mean_probs(items):
 return {k:sum(x[k] for x in items)/len(items) for k in ("S","C","U")}
def evaluate(rows,key):
 """All 3 classes, excluding X, plus support precision/recall and confusion."""
 out={}
 for emotion in CATS:
  eligible=[r for r in rows if r["gold"][emotion]!="X"]
  pair=[(r["gold"][emotion],r[key][emotion]["label"]) for r in eligible]
  byclass={}
  for label in ("S","C","U"):
   tp=sum(y==label and p==label for y,p in pair)
   fp=sum(y!=label and p==label for y,p in pair)
   fn=sum(y==label and p!=label for y,p in pair)
   precision=tp/(tp+fp) if tp+fp else 0.0
   recall=tp/(tp+fn) if tp+fn else 0.0
   byclass[label]={"precision":round(precision,3),"recall":round(recall,3),
      "f1":round(2*precision*recall/(precision+recall),3) if precision+recall else 0.0,
      "tp":tp,"fp":fp,"fn":fn}
  out[emotion]={
   "n":len(pair),
   "accuracy_all_3_classes":round(sum(y==p for y,p in pair)/len(pair),3),
   "macro_f1":round(sum(byclass[x]["f1"] for x in ("S","C","U"))/3,3),
   "by_class":byclass,
   "confusion":[{"gold":y,"pred":p,"count":n} for (y,p),n in sorted(collections.Counter(pair).items())]
  }
 return out

def extract_absa(extractor,text):
 """Pretrained joint aspect+polarity token model; returns spans and original sentences."""
 raw=extractor(text,truncation=True,max_length=512)
 spans=segments(text)
 found=[]
 seen=set()
 for item in raw:
  start,end=item.get("start"),item.get("end")
  if start is None or end is None:continue
  context=next((s for a,b,s in spans if a<=start<b),None)
  if not context:continue
  key=(start,end)
  if key in seen:continue
  seen.add(key)
  found.append({"aspect":text[start:end],"start":int(start),"end":int(end),
   "polarity":item.get("entity_group"),"confidence":float(item.get("score",0)),
   "sentence":context})
 return found

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--output",default="reports/stage1a_abc")
 parser.add_argument("--limit",type=int,default=30)
 args=parser.parse_args()
 if not 1<=args.limit<=len(GOLD):raise ValueError("limit out of range")
 import torch
 from transformers import (AutoModelForSequenceClassification,AutoModelForTokenClassification,
    AutoTokenizer,pipeline)
 nli_name="facebook/bart-large-mnli"
 absa_name="yangheng/deberta-v3-base-end2end-absa"
 nli_tok=AutoTokenizer.from_pretrained(nli_name)
 nli_model=AutoModelForSequenceClassification.from_pretrained(nli_name).eval()
 print("NLI checkpoint loaded successfully",flush=True)
 aspect_tok=AutoTokenizer.from_pretrained(absa_name,use_fast=True)
 aspect_model=AutoModelForTokenClassification.from_pretrained(absa_name).eval()
 print("ABSA checkpoint and matching tokenizer loaded successfully",flush=True)
 extractor=pipeline(task="token-classification",model=aspect_model,tokenizer=aspect_tok,
                    aggregation_strategy="simple",device=-1)
 reviews=read_jsonl(ROOT/"data/processed/reviews.jsonl")
 output=[]
 for row_idx in list(GOLD)[:args.limit]:
  review=reviews[row_idx]
  text=review["text"]
  aspects=extract_absa(extractor,text)
  # Preserve extracted span and polarity but pass text context, not polarity as
  # emotion evidence. Dedup contexts; one ABSA sentence may contain many aspects.
  contexts=list(dict.fromkeys(a["sentence"] for a in aspects))
  rec={"row":row_idx,"place_id":review["place_id"],"review_index":review["review_index"],
   "review":text,"gold":dict(zip(CATS,GOLD[row_idx])),"aspects":aspects,
   "approach_c_contexts":contexts,"approach_c_no_aspects":not bool(contexts)}
  for approach in ("A","B","C"):rec[approach]={}
  for e in CATS:
   # A: exact previous experiment hypothesis
   a=pair_nli(nli_tok,nli_model,text,HYPOTHESES[e],torch)
   rec["A"][e]={"label":decide(a),"probs":a}
   # B: equal-weight average across multiple preregistered hypotheses.
   # Avoid optimistic max-over-hypotheses cherry picking.
   b=mean_probs([pair_nli(nli_tok,nli_model,text,h,torch)
                 for h in HYPOTHESES_MULTI[e]])
   rec["B"][e]={"label":decide(b),"probs":b}
   # C: pretrained ABSA aspect extraction (with sentiment metadata), then
   # each aspect sentence evaluated via NLI against SAME single hypothesis as A.
   # C differs from A only by ABSA-driven sentence selection, not target phrasing.
   if contexts:
    c=mean_probs([pair_nli(nli_tok,nli_model,ctx,HYPOTHESES[e],torch) for ctx in contexts])
    rec["C"][e]={"label":decide(c),"probs":c}
   else:
    # Missing aspect evidence -> insufficient evidence; record coverage explicitly.
    rec["C"][e]={"label":"U","probs":None}
  output.append(rec)
  print(f"Completed {len(output)}/{args.limit}: row {row_idx}",flush=True)
 dest=ROOT/args.output;dest.mkdir(parents=True,exist_ok=True)
 with (dest/"review_cases.jsonl").open("w",encoding="utf-8") as f:
  for r in output:f.write(json.dumps(r,ensure_ascii=False)+"\n")
 summary={
  "scope":{"rows":len(output),"locations":len(set(r["place_id"] for r in output)),
           "emotions":list(CATS),"provisional_labels":True},
  "model_ids":{"nli":nli_name,"absa_extractor":absa_name,
               "absa_tokenizer":absa_name},
  "hypotheses":{"A":HYPOTHESES,"B":HYPOTHESES_MULTI,"C":HYPOTHESES},
  "aggregation":"A argmax; B mean probability across hypotheses; C mean probability across aspect-bearing sentences; C no aspects -> U",
  "coverage":{"C_reviews_without_aspects":sum(r["approach_c_no_aspects"] for r in output),
              "C_mean_aspects":round(sum(len(r["aspects"]) for r in output)/len(output),2)},
  "results":{approach:evaluate(output,approach) for approach in ("A","B","C")},
  "caveats":[
   "Provisional, single-analyst labels; small nonrandom sample, not independent validation.",
   "ABSA may identify generic product-related aspects and miss atmospheric evidence.",
   "ABSA polarity is diagnostic only; it is NOT substituted for emotion entailment.",
   "NLI probabilities are not calibrated strength scores.",
   "No inference of image-emotion relationship performed."
  ]}
 (dest/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
 print(json.dumps({"coverage":summary["coverage"],
    "overview":{a:{e:summary["results"][a][e]["macro_f1"] for e in CATS} for a in ("A","B","C")}},indent=2))
if __name__=="__main__":main()
