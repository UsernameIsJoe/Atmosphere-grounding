#!/usr/bin/env python3
"""Stage 1A pilot: compare existing extraction, pretrained NLI, aspects, embeddings.
Usage:
  python scripts/stage1a_text_pilot.py --mode baseline
  pip install transformers torch sentence-transformers
  python scripts/stage1a_text_pilot.py --mode full
Data: existing data/processed/reviews.jsonl and mentions.jsonl.
No dataset modification. Outputs to reports/stage1a_pilot (gitignored or local).
"""
import argparse, collections, csv, json, math, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parents[1]
CATS = ('calm', 'inviting', 'safe')
HYPOTHESES = {
 'calm': 'This location has a peaceful, quiet, relaxing atmosphere.',
 'inviting': 'This location has a welcoming and inviting atmosphere.',
 'safe': 'This location feels physically safe for visitors.'
}
# Transparent pilot gold: provisional reviewer interpretation; NOT independent multiple-rater truth.
# Values: S=support, C=contradict, U=unknown, X=off-topic. Selected from first 35 real review rows.
GOLD = {
 0:('U','U','S'),1:('U','U','U'),2:('C','U','U'),5:('U','U','U'),
 6:('S','U','U'),9:('U','C','U'),10:('S','S','U'),11:('C','U','U'),
 13:('X','X','X'),14:('U','C','U'),15:('C','C','C'),16:('U','S','U'),
 17:('U','S','U'),18:('U','S','U'),19:('U','C','U'),20:('S','S','S'),
 21:('U','S','U'),22:('U','U','U'),23:('S','U','U'),24:('U','U','S'),
 25:('U','S','U'),26:('U','C','U'),27:('S','U','U'),28:('S','U','U'),
 29:('S','U','U'),30:('U','S','U'),31:('U','S','U'),32:('U','C','U'),
 33:('U','C','C'),34:('C','C','C')
}
# Not an ABSA model: transparent keyword baseline to sanity-check direction.
ASPECTS = {
 'noise':(r'\\b(noisy|noise|loud|sirens|quiet|peaceful|calming|calm)\\b',),
 'crowding':(r'\\b(crowded|crowd|busy|packed)\\b',),
 'comfort':(r'\\b(shade|shaded|benches|seating|rest|relax|unwind|comfy)\\b',),
 'risk':(r'\\b(dangerous|slippery|burned|safe|secure|protected|locked gate|far enough from the street)\\b',),
 'access':(r'\\b(welcoming|inviting|parking|playground|entrance|accessible)\\b',),
}
def read_jsonl(path):
 with open(path,encoding='utf-8') as f:
  return [json.loads(x) for x in f if x.strip()]
def aspect_proxy(text):
 out=[]
 for name,patterns in ASPECTS.items():
  for pattern in patterns:
   for m in re.finditer(pattern,text,flags=re.I):
    out.append({'aspect':name,'evidence':m.group(0)})
 return out
def old_scores(rows,mentions):
 pairs={(x['place_id'],x['review_index']) for x in rows}
 tags=collections.defaultdict(set)
 for m in mentions:
  key=m['place_id'],m['review_index']
  if key in pairs and m.get('atmosphere') in CATS:tags[key].add(m['atmosphere'])
 return tags
def evaluate(data,field,positive_only=False):
 # Ignore unknowns; report S/C separately, not calibrated intensities.
 outcome={}
 for k in CATS:
  pairs=[(r['gold'][k],r[field][k]) for r in data if r['gold'][k] in ('S','C')]
  correct=sum(y==p for y,p in pairs)
  outcome[k]={'n_observed':len(pairs),'accuracy_on_observed':round(correct/len(pairs),3) if pairs else None}
 return outcome
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['baseline','full'],default='baseline')
 ap.add_argument('--output',default='reports/stage1a_pilot');args=ap.parse_args()
 reviews=read_jsonl(ROOT/'data/processed/reviews.jsonl')
 mentions=read_jsonl(ROOT/'data/processed/mentions.jsonl')
 if len(reviews)<35:raise RuntimeError('Expected at least 35 real reviews')
 selected=[(i,reviews[i]) for i in GOLD]
 tags=old_scores([r for _,r in selected],mentions)
 nli=None;embedding=None
 if args.mode=='full':
  try:
   from transformers import pipeline
   nli=pipeline('text-classification',model='facebook/bart-large-mnli',top_k=None)
   from sentence_transformers import SentenceTransformer,util
   embedding=(SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'),util)
  except Exception as e:
   raise RuntimeError('Cannot load actual pretrained NLI/embedding models. Install dependencies and download weights; no surrogate scores produced.') from e
 out=[]
 for i,r in selected:
  t=r['text'];key=(r['place_id'],r['review_index'])
  old=tags[key];rec={'row':i,'place_id':key[0],'review_index':key[1],
    'review':t,'gold':dict(zip(CATS,GOLD[i])),
    'old':{k:('S' if k in old else 'U') for k in CATS},
    'aspects_proxy':aspect_proxy(t)}
  if nli:
   rec['nli']={};rec['embedding_similarity']={}
   for k,h in HYPOTHESES.items():
    # Explicitly score premise + hypothesis; labels from model, not a measured emotion intensity.
    res=nli({'text':t,'text_pair':h},truncation=True)
    if isinstance(res,list) and res and isinstance(res[0],list):res=res[0]
    probs={e['label'].lower():e['score'] for e in res}
    lab=max(probs,key=probs.get)
    rec['nli'][k]={'label':{'entailment':'S','contradiction':'C','neutral':'U'}.get(lab,lab),'probabilities':probs}
    model,util=embedding
    emb=model.encode([t,h],convert_to_tensor=True)
    rec['embedding_similarity'][k]=round(float(util.cos_sim(emb[0],emb[1]).item()),4)
  out.append(rec)
 dest=ROOT/args.output;dest.mkdir(parents=True,exist_ok=True)
 with open(dest/'review_cases.jsonl','w',encoding='utf-8') as f:
  for a in out:f.write(json.dumps(a,ensure_ascii=False)+'\n')
 summary={'sample_rows':len(out),'n_locations':len(set(x['place_id'] for x in out)),
          'gold_counts':{k:dict(collections.Counter(x['gold'][k] for x in out)) for k in CATS},
          'old_label_counts':{k:sum(x['old'][k]=='S' for x in out) for k in CATS},
          'old_vs_provisional_gold':evaluate(out,'old'),
          'aspect_proxy_note':'Lexical aspect indicators only; not trained ABSA'}
 if nli:
  for x in out:x['nli_label']={k:x['nli'][k]['label'] for k in CATS}
  summary['nli_vs_provisional_gold']=evaluate(out,'nli_label')
  summary['model_names']=['facebook/bart-large-mnli','sentence-transformers/all-MiniLM-L6-v2']
 else:summary['model_status']='NOT RUN: baseline mode, NLI and sentence embeddings not evaluated'
 (dest/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
