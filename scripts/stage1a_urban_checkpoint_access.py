#!/usr/bin/env python3
"""Check public availability of Tas & Sanatani (2023) *urban-trained* checkpoint.
Do not conflate generic PyABSA LCF-ATEPC weights with authors' fine-tuned weights.
"""
import json, urllib.request, urllib.parse, pathlib, re, datetime
KEYS=["2312.12253","Geo-located Aspect Based Sentiment Analysis","demircantas","sanatani","urban park absa"]
HEAD={"User-Agent":"Atmosphere-grounding-availability-audit","Accept":"application/json"}
def get(url):
 try:
  req=urllib.request.Request(url,headers=HEAD)
  with urllib.request.urlopen(req,timeout=25) as resp: return json.load(resp),None
 except Exception as exc:return None,str(exc)
reports=[]
for phrase in KEYS:
 url="https://huggingface.co/api/models?search="+urllib.parse.quote(phrase)+"&limit=100"
 result,error=get(url)
 matches=[{"id":x.get("id"),"pipeline_tag":x.get("pipeline_tag")} for x in result] if isinstance(result,list) else []
 reports.append({"service":"huggingface_models","phrase":phrase,"count":len(matches),"matches":matches[:20],"error":error})
for phrase in ["2312.12253","Geo-located Aspect Based Sentiment Analysis","urban park absa LCF"]:
 url="https://api.github.com/search/repositories?q="+urllib.parse.quote(phrase)+"&per_page=100"
 result,error=get(url)
 repos=[{"full_name":x.get("full_name"),"html_url":x.get("html_url")} for x in result.get("items",[])] if isinstance(result,dict) else []
 reports.append({"service":"github_repository_search","phrase":phrase,"count":len(repos),"matches":repos[:20],"error":error})
for phrase in ["2312.12253","urban park ABSA","sanatani"]:
 url="https://huggingface.co/api/datasets?search="+urllib.parse.quote(phrase)+"&limit=100"
 result,error=get(url)
 ds=[{"id":x.get("id")} for x in result] if isinstance(result,list) else []
 reports.append({"service":"huggingface_datasets","phrase":phrase,"count":len(ds),"matches":ds[:20],"error":error})
# AATEPC versus ASTE are different tasks. No inference without specific checkpoint identifier.
out={"paper":"arxiv:2312.12253","authors":["Demircan Tas","Rohit Priyadarshi Sanatani"],
"verified_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
"checkpoint_id":None,"checkpoint_status":"not_verified_available",
"paper_training":"PyABSA LCF-ATEPC fine-tuned on 2250 annotated urban park reviews, 250 test reviews",
"not_equivalent":"PyABSA generic LCF-ATEPC or generic multilingual EMC-GCN are NOT the paper's fine-tuned checkpoint",
"searches":reports,
"interpretation":"No publicly identifiable specific checkpoint located via these queries. Absence from search is not proof private weights do not exist. Do not run substitute weights as if they were this model."}
path=pathlib.Path("reports/urban_checkpoint_access.json");path.parent.mkdir(exist_ok=True,parents=True)
path.write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
