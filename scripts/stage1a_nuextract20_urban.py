#!/usr/bin/env python3
"""NuExtract-2.0-2B official template-driven extraction on frozen original reviews.

Start with predeclared 8-sentence real-data pilot to validate CPU feasibility.
No in-context synthesized examples; deterministic decoding.
"""
import argparse,json,pathlib,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"scripts"))
from stage1a_absa_official_sentence_inference import load_cases
MODEL="numind/NuExtract-2.0-2B"
TEMPLATE={"observations":[{
 "physical_feature":"verbatim-string",
 "description":"verbatim-string",
 "felt_experience":"verbatim-string"
}]}
PILOT_INDICES=(0,2,5,10,18,24,36,50)
def main():
 p=argparse.ArgumentParser();p.add_argument("--output",type=pathlib.Path,required=True);a=p.parse_args()
 import torch
 from transformers import AutoProcessor,AutoModelForVision2Seq
 torch.set_num_threads(4)
 model=AutoModelForVision2Seq.from_pretrained(MODEL,torch_dtype=torch.float32,device_map="cpu",trust_remote_code=False).eval()
 processor=AutoProcessor.from_pretrained(MODEL,padding_side="left",use_fast=True)
 cases,_=load_cases();flat=[{"row":c["row"],"place_id":c["place_id"],"review_index":c["review_index"],**s} for c in cases for s in c["sentences"]]
 assert len(flat)==56
 inputs=[flat[i] for i in PILOT_INDICES]
 a.output.mkdir(parents=True,exist_ok=True)
 outputs=[]
 for j,s in enumerate(inputs):
  message=[{"role":"user","content":s["text"]}]
  prompt=processor.tokenizer.apply_chat_template(message,template=json.dumps(TEMPLATE),tokenize=False,add_generation_prompt=True)
  encoded=processor(text=[prompt],images=None,padding=True,return_tensors="pt")
  with torch.inference_mode():
   generated=model.generate(**encoded,do_sample=False,num_beams=1,max_new_tokens=256)
  response=processor.batch_decode([generated[0][len(encoded.input_ids[0]):]],skip_special_tokens=True,clean_up_tokenization_spaces=False)[0]
  try:structured=json.loads(response);status="valid_json"
  except Exception:structured=None;status="invalid_json"
  outputs.append({**s,"raw":response,"extraction":structured,"status":status})
  print("NuExtract complete original sentence",j+1,"/",len(inputs),"row",s["row"],"status",status,flush=True)
  (a.output/"predictions.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in outputs))
 summary={"checkpoint":MODEL,"protocol":"Official tokenizer.apply_chat_template(template=...), greedy generate; original unaltered sentence text",
 "pilot_sentence_indices":PILOT_INDICES,"attempted":len(inputs),"completed":len(outputs),"valid_json":sum(x["status"]=="valid_json" for x in outputs),
 "source_sentences_total":len(flat),"notes":"8-sentence predeclared real-data pilot for CPU feasibility; not full corpus evaluation; no gold accuracy."}
 (a.output/"summary.json").write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if __name__=="__main__":main()
