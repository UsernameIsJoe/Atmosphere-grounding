#!/usr/bin/env python3
"""Offline pre-gate diagnostic; pretrained models only, no fitting or LLM calls."""
import collections,hashlib,itertools,json,os,re,subprocess,time,unicodedata,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'research_audit/stage1a_pregate_three_checks_2026-11-18'
SOURCE=ROOT/'research_audit/stage1a_review_gate_v04_regression_qwen8b_2026-11-16/cases.jsonl'
GATE=ROOT/'research_audit/stage1a_gate_scenarios_v5_test_2026-11-17/decisions.jsonl'
CACHE=Path('/workspace/pretrained')
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def write(name,data):
    (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def rows(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def normalize(t):return ' '.join(unicodedata.normalize('NFKC',t).casefold().split())
def run():
    start=time.monotonic();OUT.mkdir(parents=True,exist_ok=True);CACHE.mkdir(exist_ok=True)
    data=rows(SOURCE);assert len(data)==36 and len({x['case_id'] for x in data})==36
    gate={x['review_id']:x for x in rows(GATE) if x['condition']=='v5_scenarios'}
    assert len(gate)==36
    for x in data:assert x['text']==gate[x['case_id']]['review_text']
    manifest={'status':'diagnostic_not_adopted','reviews':36,'input_sha256':sha(SOURCE),'runner_sha256':sha(Path(__file__)),'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'training':False,'llm_calls':0,'original_reviews_modified':False,'thresholds_predeclared':{'near_duplicate_jaccard':0.8,'language_uncertain_top_score_below':0.8,'toxicity_flag':0.5,'toxicity_sensitivity':[0.2,0.5,0.8]},'language_policy':'report top language and uncertainty; route rather than assume non-English is invalid','toxicity_policy':'main toxicity score >=0.5 is provisional flag, not calibrated rejection; all class scores saved','duplicate_policy':'exact raw and NFKC+casefold+whitespace normalized matching; all 630 pairs checked for exact word-trigram Jaccard >=0.8, >=5 words each; MinHash128 seed42 estimate recorded, not used to discard pairs','model_sources':{'fasttext':'https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin','detoxify':'https://github.com/unitaryai/detoxify/releases/download/v0.3-alpha/toxic_debiased-c7548aa0.ckpt','detoxify_implementation_commit':'7ef6576274b91bfc6e06a41f69ad41cc04eaccf1'},'long_review_policy':'Detoxify original whole-review predict if <=512 tokens including special tokens; otherwise overlapping 400-token windows stride272, per-label maximum; no tail discarded','gate_comparison':'join archived v5 decisions by review ID and identical text; do not rerun or modify gate'}
    write('manifest.json',manifest)
    from datasketch import MinHash
    normalized=[normalize(x['text']) for x in data]
    groups=[]
    for kind,texts in [('raw',[x['text'] for x in data]),('normalized',normalized)]:
        m=collections.defaultdict(list)
        for x,t in zip(data,texts):m[t].append(x['case_id'])
        groups.extend({'kind':kind,'review_ids':v} for v in m.values() if len(v)>1)
    tokens=[re.findall(r'\w+',t) for t in normalized]
    shingles=[set(' '.join(ts[i:i+3]) for i in range(len(ts)-2)) for ts in tokens]
    signatures=[]
    for ss in shingles:
        m=MinHash(num_perm=128,seed=42)
        for s in sorted(ss):m.update(s.encode())
        signatures.append(m)
    pairs=[]
    for i,j in itertools.combinations(range(36),2):
        u=shingles[i]|shingles[j];score=len(shingles[i]&shingles[j])/len(u) if u else 0.
        pairs.append({'a':data[i]['case_id'],'b':data[j]['case_id'],'word_trigram_jaccard':score,'minhash_estimate':signatures[i].jaccard(signatures[j]),'near_duplicate_flag':len(tokens[i])>=5 and len(tokens[j])>=5 and score>=0.8})
    pairs.sort(key=lambda x:x['word_trigram_jaccard'],reverse=True)
    write('duplicates.json',{'exact_groups':groups,'near_duplicate_pairs':[x for x in pairs if x['near_duplicate_flag']],'all_pairs':pairs})
    print('DUPLICATES_FINISHED',flush=True)
    import fasttext
    lidpath=CACHE/'lid.176.bin'
    if not lidpath.exists():urllib.request.urlretrieve(manifest['model_sources']['fasttext'],lidpath)
    lid=fasttext.load_model(str(lidpath))
    language={}
    for x in data:
        labels,probs=lid.predict(' '.join(x['text'].split()),k=3)
        top=[{'language':l.replace('__label__',''),'score':float(p)} for l,p in zip(labels,probs)]
        language[x['case_id']]={'top3':top,'non_english_flag':top[0]['language']!='en','uncertain_flag':top[0]['score']<0.8}
    write('language.json',language);print('LANGUAGE_FINISHED',flush=True)
    import torch
    from detoxify import Detoxify
    torch.set_num_threads(8);torch.set_num_interop_threads(1)
    model=Detoxify('unbiased',device='cpu')
    prediction=[]
    with (OUT/'predictions.jsonl').open('w') as f:
        for x in data:
            s=time.monotonic();ids=model.tokenizer.encode(x['text'],add_special_tokens=False)
            chunks=[x['text']] if len(ids)+model.tokenizer.num_special_tokens_to_add()<=512 else [model.tokenizer.decode(ids[i:i+400],skip_special_tokens=True) for i in range(0,len(ids),272)]
            per_window=[{k:float(v) for k,v in model.predict(chunk).items()} for chunk in chunks]
            scores={k:max(w[k] for w in per_window) for k in per_window[0]}
            rec={'review_id':x['case_id'],'place_id':x['place_id'],'review_text':x['text'],'review_sha256':hashlib.sha256(x['text'].encode()).hexdigest(),'language':language[x['case_id']],'detoxify':{'model':'unbiased','input_tokens_without_special':len(ids),'windows':len(chunks),'scores':scores,'window_scores':per_window,'flag_at_0_5':scores['toxicity']>=0.5,'seconds':time.monotonic()-s},'archived_v5_keep':gate[x['case_id']]['parsed']['keep']}
            prediction.append(rec);f.write(json.dumps(rec,ensure_ascii=False)+'\n');f.flush()
            print('SCORED',x['case_id'],round(scores['toxicity'],6),len(chunks),flush=True)
    ckpt=Path(torch.hub.get_dir())/'checkpoints/toxic_debiased-c7548aa0.ckpt'
    from importlib.metadata import version
    write('runtime.json',{'packages':{p:version(p) for p in ['torch','transformers','numpy','datasketch','fasttext-wheel','detoxify']},'python':subprocess.check_output(['python','--version'],text=True).strip(),'cpu':Path('/proc/cpuinfo').read_text().split('model name',1)[-1].splitlines()[0],'torch_threads':torch.get_num_threads(),'fasttext_model_sha256':sha(lidpath),'detoxify_checkpoint_sha256':sha(ckpt),'detoxify_tokenizer':model.tokenizer.name_or_path,'tokenizer_limit':model.tokenizer.model_max_length,'model_config':model.model.config.to_dict()})
    summary={'reviews':36,'completed':len(prediction),'duplicate_groups':groups,'near_duplicate_pairs':[p for p in pairs if p['near_duplicate_flag']],'largest_nonidentical_pair':next((p for p in pairs if p['word_trigram_jaccard']<1),None),'non_english':[k for k,v in language.items() if v['non_english_flag']],'language_uncertain':[k for k,v in language.items() if v['uncertain_flag']],'toxicity_flags':{str(t):[r['review_id'] for r in prediction if r['detoxify']['scores']['toxicity']>=t] for t in [0.2,0.5,0.8]},'toxicity_flagged_v5_keep':[r['review_id'] for r in prediction if r['detoxify']['flag_at_0_5'] and r['archived_v5_keep']],'top_toxicity':[{'review_id':r['review_id'],'scores':r['detoxify']['scores'],'v5_keep':r['archived_v5_keep']} for r in sorted(prediction,key=lambda r:r['detoxify']['scores']['toxicity'],reverse=True)[:10]],'N05':next(r for r in prediction if r['review_id']=='N05'),'multi_window_reviews':[r['review_id'] for r in prediction if r['detoxify']['windows']>1],'elapsed_seconds_including_model_downloads':time.monotonic()-start,'adopted':False,'new_gate_or_emotion_calls':0}
    write('summary.json',summary)
    subprocess.run(['python','-m','pip','freeze'],stdout=(OUT/'pip-freeze.txt').open('w'),check=True)
    write('hashes.json',{p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='hashes.json'})
    print('ALL_36_REVIEWS_FINISHED',flush=True)
if __name__=='__main__':run()
