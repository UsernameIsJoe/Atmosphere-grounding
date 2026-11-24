#!/usr/bin/env python3
"""Fixed real-review embedding audit. Run from repository root; writes audit outputs."""
import os,json,re,hashlib,sys,time,platform,subprocess,importlib.metadata,random,collections
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from scipy.stats import spearmanr
from sentence_transformers import SentenceTransformer
from huggingface_hub import model_info
sys.path.insert(0,str(Path(__file__).parent))
from stage1a_panel_pilot import segment_review
OUT=Path('research_audit/embedding_representativeness_2026-11-24');OUT.mkdir(parents=True,exist_ok=True)
SOURCE=Path('data/processed/reviews.jsonl')
INSTRUCTION='Represent the topics and aspects of the place experience described in this text, focusing on what is discussed rather than whether the opinion is positive or negative.'
rows=[json.loads(x) for x in SOURCE.read_text().splitlines() if x.strip()]
# Deduplicate exact text within place, retain source indices and original offsets.
rng=random.Random(20261124)
groups=collections.defaultdict(list)
for i,r in enumerate(rows): groups[r['place_id']].append(i)
place_order=sorted(groups);rng.shuffle(place_order)
for ids in groups.values(): rng.shuffle(ids)
selected=[]
while len(selected)<100:
 for place in place_order:
  if groups[place] and len(selected)<100: selected.append(groups[place].pop())
selected=set(selected)
seen=set();reviews=[];units=[]
for source_id,r in enumerate(rows):
 if source_id not in selected:continue
 source_id=r.get('source_id',source_id)
 key=(r['place_id'],r['text'])
 if key in seen or not r['text'].strip():continue
 seen.add(key); r={**r,'source_id':source_id};reviews.append(r)
 segs=segment_review(r['text'])
 for j,s in enumerate(segs):
  units.append({**s,'source_id':source_id,'place_id':r['place_id'],'full_review':r['text'],'n_segments':len(segs),'position':j/max(1,len(segs)-1),'words':len(s['text'].split()),'remainder':(r['text'][:s['start']]+' '+r['text'][s['end']:]).strip()})
df=pd.DataFrame(units); df.to_json(OUT/'input_segments.jsonl',orient='records',lines=True,force_ascii=False)
meta={'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'source_reviews':len(rows),'sampling_seed':20261124,'sampling':'place-balanced round-robin after seeded shuffling; source IDs preserved','reviews':len(reviews),'places':len(set(r['place_id'] for r in reviews)),'segments':len(df),'instruction':INSTRUCTION,'weight_rule':'max(cosine,0) / sum(max(cosine,0)) within review; uniform if all zero; single-segment weight=1','gpu':torch.cuda.get_device_name(),'python':platform.python_version(),'libraries':{k:importlib.metadata.version(k) for k in ['torch','transformers','sentence-transformers','numpy','pandas','scipy']},'models':{}}
summary={}
for name,model_id in [('mpnet','sentence-transformers/all-mpnet-base-v2'),('qwen','Qwen/Qwen3-Embedding-8B')]:
 revision={'mpnet':'e8c3b32edf5434bc2275fc9bab85f82640a19130','qwen':'1d8ad4ca9b3dd8059ad90a75d4983776a23d44af'}[name]
 kwargs={'torch_dtype':torch.bfloat16,'attn_implementation':'sdpa'} if name=='qwen' else {}
 model=SentenceTransformer(model_id,revision=revision,device='cuda',model_kwargs=kwargs,tokenizer_kwargs={'padding_side':'left'} if name=='qwen' else {})
 prompt='Instruct: '+INSTRUCTION+'\nQuery: ' if name=='qwen' else ''
 texts=list(dict.fromkeys(df.text.tolist()+df.full_review.tolist()+df.remainder.tolist()+['staff were rude','staff were lovely','the building has a brick facade','the staff were unhelpful','staff were friendly']))
 lengths=[len(model.tokenizer(prompt+t,add_special_tokens=True,truncation=False)['input_ids']) for t in texts]
 limit=model.max_seq_length
 meta['models'][name]={'id':model_id,'revision':revision,'max_seq_length':limit,'max_observed_tokens':max(lengths),'over_limit_unique_texts':sum(n>limit for n in lengths),'dtype':str(next(model.parameters()).dtype)}
 # Never silently truncate: omit over-limit text for this model; cross-model analysis uses shared eligible reviews.
 valid=[t for t,n in zip(texts,lengths) if n<=limit]
 print(name,'encoding',len(valid),'texts; over limit',sum(n>limit for n in lengths),flush=True)
 vec=model.encode(valid,batch_size=8 if name=='qwen' else 32,prompt=prompt,normalize_embeddings=True,show_progress_bar=True,convert_to_numpy=True)
 lookup=dict(zip(valid,vec))
 def cosine(a,b):return float(lookup[a]@lookup[b]) if a in lookup and b in lookup else np.nan
 df[name+'_cosine']=[cosine(s,r) for s,r in zip(df.text,df.full_review)]
 df[name+'_loo']=[cosine(s,r) if r else np.nan for s,r in zip(df.text,df.remainder)]
 def weights(g):
  if g.isna().any():return pd.Series(np.nan,index=g.index)
  v=g.clip(lower=0);return v/v.sum() if v.sum()>0 else v*0+1/len(v)
 df[name+'_weight']=df.groupby('source_id')[name+'_cosine'].transform(weights)
 df[name+'_loo_weight']=df.groupby('source_id')[name+'_loo'].transform(weights)
 summary[name]={'sanity_rude_lovely_cosine':cosine('staff were rude','staff were lovely'),'sanity_rude_unhelpful_cosine':cosine('staff were rude','the staff were unhelpful'),'sanity_rude_building_cosine':cosine('staff were rude','the building has a brick facade')}
 # Deterministic review-order reversal isolates location-in-context from segment wording.
 rev={r['source_id']:' '.join(s['text'] for s in reversed(segment_review(r['text']))) for r in reviews}
 elig=[(rid,t) for rid,t in rev.items() if len(model.tokenizer(prompt+t,truncation=False)['input_ids'])<=limit]
 vv=model.encode([t for _,t in elig],batch_size=8 if name=='qwen' else 32,prompt=prompt,normalize_embeddings=True,show_progress_bar=False)
 rv=dict(zip([rid for rid,_ in elig],vv))
 df[name+'_reversed_cosine']=[float(lookup[s]@rv[rid]) if s in lookup and rid in rv else np.nan for s,rid in zip(df.text,df.source_id)]
 df.to_csv(OUT/'segment_scores.csv',index=False)
 (OUT/'manifest.json').write_text(json.dumps(meta,indent=2));(OUT/'sanity_checks.json').write_text(json.dumps(summary,indent=2))
 del model,lookup,vec;import gc;gc.collect();torch.cuda.empty_cache()
print('DONE',flush=True)
