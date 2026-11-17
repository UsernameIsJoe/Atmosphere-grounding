#!/usr/bin/env python3
"""Resume legacy emotion failures, then classify a shared fixed claim pool only."""
import argparse, collections, hashlib, json, sys, time, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import stage1a_codebook_v05_directional_benchmark_20261116 as old
BASE=ROOT/'research_audit/stage1a_v05_gate_passed_followup_live_2026-11-16/predictions.jsonl'
SEG=ROOT/'research_audit/stage1a_v05_gate_passed_followup_prepared_2026-11-16/segments.jsonl'
OUT=ROOT/'research_audit/stage1a_et_only_2026-11-17'
CB=ROOT/'Docs/STAGE1A_ET_CODEBOOK_V0_6_2026-11-17.md'
PROMPT=ROOT/'Docs/STAGE1A_ET_PROMPT_V0_6_2026-11-17.md'
def rows(p): return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []
def write(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def append(p,x):
    with p.open('a') as f: f.write(json.dumps(x,ensure_ascii=False)+'\n'); f.flush()
def request(endpoint,payload,timeout=300):
    req=urllib.request.Request('http://127.0.0.1:11434'+endpoint,json.dumps(payload).encode(),{'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as r:return json.load(r)
def warm(model):
    request('/api/generate',{'model':model,'keep_alive':'20m','stream':False},600)
def unload(model): request('/api/generate',{'model':model,'keep_alive':0,'stream':False})
def call(model,system,user,schema):
    start=time.monotonic(); rec={'model':model,'raw':'','parsed':None}
    try:
        reply=request('/api/chat',{'model':model,'messages':[{'role':'system','content':system},{'role':'user','content':json.dumps(user,ensure_ascii=False)}],'format':schema,'stream':False,'think':False,'options':old.OPTIONS,'keep_alive':'20m'})
        rec['raw']=reply['message']['content'];rec['parsed']=json.loads(rec['raw']);rec['metadata']={k:reply.get(k) for k in ('eval_count','prompt_eval_count','total_duration','done_reason')}
    except Exception as e:rec['exception']=repr(e)
    rec['seconds']=round(time.monotonic()-start,3);return rec
def pending(model,baseline,segments):
    valid={r['segment_id'] for r in baseline if r['model']==model and r['strict_valid']}
    return [s for s in segments if s['segment_id'] not in valid]
def pool(baseline,completed):
    result={}
    for phase,records in [('original',baseline),('completion',completed)]:
        for r in records:
            if not r['strict_valid']:continue
            for c in r['claims']:
                key=(r['segment_id'],c['emotion'],c['direction'],c['quote'])
                cid=hashlib.sha256(json.dumps(key,ensure_ascii=False).encode()).hexdigest()[:20]
                if cid not in result:result[cid]={'claim_id':cid,'segment_id':r['segment_id'],'emotion':c['emotion'],'direction':c['direction'],'quote':c['quote'],'cohort':phase,'provenance':[]}
                result[cid]['provenance'].append({'model':r['model'],'legacy_track':c['track'],'phase':phase})
    return list(result.values())
def validate(obj,claims):
    if not isinstance(obj,dict) or set(obj)!={'classifications'}:return ['structure']
    rr=obj['classifications']
    if not isinstance(rr,list) or len(rr)!=len(claims):return ['count']
    errors=[]
    for c,r in zip(claims,rr):
        if not isinstance(r,dict) or set(r)!={'claim_id','track','reason'}:errors.append('fields');continue
        if r['claim_id']!=c['claim_id']:errors.append('id_order')
        if r['track'] not in ('E','T'):errors.append('track')
        if not isinstance(r['reason'],str) or not r['reason'].strip():errors.append('reason')
    return errors
def prepare():
    b=rows(BASE);s=rows(SEG)
    assert len(s)==71 and len({x['segment_id'] for x in s})==71
    for r in s:assert r['full_review_context'][r['start']:r['end']]==r['target_segment']
    manifest={'protocol':'v0.6_ET_only_fixed_shared_claim_pool','models':old.MODEL_DIGESTS,'options':old.OPTIONS,'think':False,'legacy_completion_version':'0.5','no_retries':True,'stop_rule':'finish all planned requests; no 30-minute cutoff','files_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (BASE,SEG,CB,PROMPT)},'segments':len(s),'completion_calls':{m:len(pending(m,b,s)) for m in old.MODELS},'original_shared_pool_claims':len(pool(b,[])),'evaluation':'agreement and legacy track changes; no human accuracy claim'}
    OUT.mkdir(parents=True,exist_ok=True);write(OUT/'manifest.json',manifest)
    # Mechanical ID and immutable-claim checks, including rejected additions.
    cc=[{'claim_id':'a'}];assert not validate({'classifications':[{'claim_id':'a','track':'T','reason':'object'}]},cc)
    assert validate({'classifications':[{'claim_id':'b','track':'T','reason':'object'}]},cc)
    assert validate({'classifications':[{'claim_id':'a','track':'T','reason':'object','emotion':'safe'}]},cc)
    print(json.dumps(manifest),flush=True)
def run():
    prepare();b=rows(BASE);s=rows(SEG);system,schema=old.system_and_schema()
    for model in old.MODELS:
        actual=old.original.installed_digest('http://127.0.0.1:11434',model)
        assert actual==old.MODEL_DIGESTS[model],(model,actual)
        done={r['segment_id'] for r in rows(OUT/'emotion_completion.jsonl') if r['model']==model}
        warm(model)
        for seg in pending(model,b,s):
            if seg['segment_id'] in done:continue
            r={**seg,**call(model,system,{'target_segment':seg['target_segment'],'full_review_context':seg['full_review_context']},schema)}
            errs,claims=old.examine(r['parsed'],seg['target_segment']);r.update(validation_errors=errs,claims=claims,strict_valid=not errs,model_digest=actual)
            append(OUT/'emotion_completion.jsonl',r);print('EMOTION',model,seg['segment_id'],not errs,flush=True)
        unload(model)
    claims=pool(b,rows(OUT/'emotion_completion.jsonl'));write(OUT/'fixed_claim_pool.json',claims)
    etsystem=PROMPT.read_text()+'\n\n'+CB.read_text()
    ets={'type':'object','additionalProperties':False,'required':['classifications'],'properties':{'classifications':{'type':'array','items':{'type':'object','additionalProperties':False,'required':['claim_id','track','reason'],'properties':{'claim_id':{'type':'string'},'track':{'type':'string','enum':['E','T']},'reason':{'type':'string'}}}}}}
    for model in old.MODELS:
        done={r['segment_id'] for r in rows(OUT/'et_predictions.jsonl') if r['model']==model};warm(model)
        for seg in s:
            cc=[c for c in claims if c['segment_id']==seg['segment_id']]
            if not cc or seg['segment_id'] in done:continue
            user={'target_segment':seg['target_segment'],'full_review_context':seg['full_review_context'],'fixed_claims':[{k:c[k] for k in ('claim_id','emotion','direction','quote')} for c in cc]}
            r=call(model,etsystem,user,ets);errs=validate(r['parsed'],cc);r.update(segment_id=seg['segment_id'],input_claim_ids=[c['claim_id'] for c in cc],validation_errors=errs,strict_valid=not errs)
            append(OUT/'et_predictions.jsonl',r);print('ET',model,seg['segment_id'],not errs,flush=True)
        unload(model)
    report();print('ALL_PLANNED_REQUESTS_FINISHED',flush=True)
def report():
    b=rows(BASE);comp=rows(OUT/'emotion_completion.jsonl');claims=pool(b,comp);pred=rows(OUT/'et_predictions.jsonl');out={'emotion_completion':{},'ET':{},'no_human_accuracy_claim':True}
    maps={}
    for model in old.MODELS:
        originalvalid={r['segment_id'] for r in b if r['model']==model and r['strict_valid']};new=[r for r in comp if r['model']==model];valid=originalvalid|{r['segment_id'] for r in new if r['strict_valid']}
        out['emotion_completion'][model]={'completion_attempts':len(new),'completion_valid':sum(r['strict_valid'] for r in new),'total_valid_segments':len(valid),'total_segments':71,'invalid_completion':{r['segment_id']:r['validation_errors'] for r in new if not r['strict_valid']}}
        pp=[r for r in pred if r['model']==model];mapping={c['claim_id']:c for r in pp if r['strict_valid'] for c in r['parsed']['classifications']};maps[model]=mapping
        legacy=[(c,p) for c in claims for p in c['provenance'] if p['model']==model and p['phase']=='original' and c['claim_id'] in mapping]
        out['ET'][model]={'calls':len(pp),'valid_calls':sum(r['strict_valid'] for r in pp),'classified_claims':len(mapping),'tracks':dict(collections.Counter(c['track'] for c in mapping.values())),'legacy_original_claims_compared':len(legacy),'legacy_changed':sum(mapping[c['claim_id']]['track']!=p['legacy_track'] for c,p in legacy),'invalid_segments':[r['segment_id'] for r in pp if not r['strict_valid']]}
    shared=set(maps[old.MODELS[0]])&set(maps[old.MODELS[1]])
    for cohort in ('all','original','completion'):
        ids=[c['claim_id'] for c in claims if c['claim_id'] in shared and (cohort=='all' or c['cohort']==cohort)]
        out['agreement_'+cohort]={'shared_claims':len(ids),'agree':sum(maps[old.MODELS[0]][i]['track']==maps[old.MODELS[1]][i]['track'] for i in ids),'disagreement_ids':[i for i in ids if maps[old.MODELS[0]][i]['track']!=maps[old.MODELS[1]][i]['track']]}
    out['fixed_claims']=len(claims);write(OUT/'summary.json',out);print(json.dumps(out),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','run','report']);a=p.parse_args();globals()[a.stage]()
