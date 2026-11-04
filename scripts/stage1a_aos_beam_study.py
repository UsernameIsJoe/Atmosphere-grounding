#!/usr/bin/env python3
"""Controlled AOS beam variation over exactly the same original sentences."""
import argparse,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"scripts"))
from stage1a_absa_official_sentence_inference import load_cases,rebase_relation
from stage1a_relation_pilot import MODEL,INSTRUCTION,parse_triplets,make_relation
def main():
 p=argparse.ArgumentParser();p.add_argument("--beams",type=int,choices=(1,3,5),required=True);p.add_argument("--output",type=pathlib.Path,required=True);a=p.parse_args()
 import torch
 from transformers import AutoTokenizer,AutoModelForSeq2SeqLM
 torch.set_num_threads(4)
 tok=AutoTokenizer.from_pretrained(MODEL);model=AutoModelForSeq2SeqLM.from_pretrained(MODEL).eval()
 cases,_=load_cases()
 for c in cases:
  all_rel=[]
  for s in c["sentences"]:
   txt=s["text"];encoded=tok(INSTRUCTION+txt+" \noutput:",return_tensors="pt",truncation=False)
   if encoded["input_ids"].shape[1]>512:raise ValueError("Long input: refusing truncation")
   with torch.inference_mode():ids=model.generate(**encoded,max_new_tokens=250,num_beams=a.beams,do_sample=False)
   raw=tok.decode(ids[0],skip_special_tokens=True)
   triples,status=parse_triplets(raw)
   relations=[rebase_relation(make_relation(txt,asp,op,pol,"aos_t5",raw={"generation":raw}),s["start"],c["review"]) for asp,op,pol in triples]
   s["extraction"]={"relations":relations,"raw_generation":raw,"parse_status":status,"input_truncated":False}
   all_rel.extend(relations)
  c["extraction"]={"relations":all_rel}
  print("beam",a.beams,"row",c["row"],"relations",len(all_rel),flush=True)
 a.output.mkdir(parents=True,exist_ok=True)
 (a.output/"review_cases.jsonl").write_text("".join(json.dumps(c,ensure_ascii=False)+"\n" for c in cases))
 sentences=[s for c in cases for s in c["sentences"]];rels=[r for c in cases for r in c["extraction"]["relations"]]
 result={"beam":a.beams,"reviews":len(cases),"sentences":len(sentences),"relations":len(rels),"source_grounded_relations":sum(x.get("grounded",False) for x in rels),"unparsed_sentences":sum(s["extraction"]["parse_status"]=="unparsed_generation" for s in sentences),"interpretation":"operational diagnostics, not accuracy"}
 (a.output/"summary.json").write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=="__main__":main()
