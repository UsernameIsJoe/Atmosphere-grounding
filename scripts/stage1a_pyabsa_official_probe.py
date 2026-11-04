#!/usr/bin/env python3
"""Official PyABSA ASTE inference probe on real review sentences, no synthetic text.

Checkpoint selection and API follow PyABSA ASTE documentation; no output
schema is guessed into aspect/opinion spans. Raw predictions are retained.
"""
import argparse,json,pathlib,sys,traceback
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from stage1a_absa_official_sentence_inference import load_cases
def main():
 p=argparse.ArgumentParser();p.add_argument("--output",type=pathlib.Path,required=True);p.add_argument("--checkpoint",default="multilingual");a=p.parse_args()
 a.output.mkdir(parents=True,exist_ok=True)
 cases,_=load_cases()
 from pyabsa import AspectSentimentTripletExtraction as ASTE
 extractor=ASTE.AspectSentimentTripletExtractor(checkpoint=a.checkpoint)
 output=[]
 for c in cases:
  entries=[]
  for s in c["sentences"]:
   pred=extractor.predict(s["text"],print_result=False,ignore_error=False)
   entries.append({"sentence_index":s["sentence_index"],"start":s["start"],"end":s["end"],"text":s["text"],"raw_prediction":pred})
  output.append({"row":c["row"],"place_id":c["place_id"],"review":c["review"],"sentences":entries})
  print("pyabsa real review",c["row"],flush=True)
 (a.output/"raw_results.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False,default=str)+"\n" for x in output))
 (a.output/"summary.json").write_text(json.dumps({"checkpoint":a.checkpoint,"reviews":len(output),"sentences":sum(len(x["sentences"]) for x in output),"protocol":"PyABSA documented ASTE.AspectSentimentTripletExtractor(checkpoint=multilingual).predict(single_sentence)","note":"Raw author-output retained, semantic scoring pending full independently adjudicated gold."},indent=2))
 print("PyABSA inference succeeded on original real-review sentences")
if __name__=="__main__":main()
