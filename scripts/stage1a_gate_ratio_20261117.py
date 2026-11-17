#!/usr/bin/env python3
"""Single gate relevance pass; fixed offline proportion thresholds. Stdlib only."""
import argparse,collections,csv,hashlib,json,re,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'research_audit/stage1a_review_gate_v04_regression_qwen8b_2026-11-16'
OUT=ROOT/'research_audit/stage1a_gate_ratio_2026-11-17'
PROMPT=ROOT/'Docs/STAGE1A_GATE_RATIO_PROMPT_V0_5_2026-11-17.txt'
PROTOCOL=ROOT/'Docs/STAGE1A_GATE_RATIO_V0_5_EXPERIMENT_2026-11-17.md'
MODEL='qwen3:8b'
OPTIONS={'temperature':0,'seed':42,'num_ctx':8192,'num_predict':4096}
THRESHOLDS=(25,50,75)
def rows(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def split(text):
    boundaries=[0]+[m.end() for m in re.finditer(r'(?<=[.!?;])\s+|\n+|(?<=,)\s+(?=(?:but|yet|however)\b)',text,flags=re.I)]+[len(text)]
    units=[]
    for a,b in zip(boundaries,boundaries[1:]):
        while a<b and text[a].isspace():a+=1
        while b>a and text[b-1].isspace():b-=1
        if a<b:units.append({'unit_id':len(units)+1,'start':a,'end':b,'text':text[a:b],'words':len(re.findall(r'\b[\w]+(?:[’\x27-][\w]+)*\b',text[a:b]))})
    cursor=0
    for u in units:
        assert not text[cursor:u['start']].strip();assert text[u['start']:u['end']]==u['text'];cursor=u['end']
    assert not text[cursor:].strip()
    return units
def validate(obj,units):
    if not isinstance(obj,dict) or set(obj)!={'labels'}:return ['structure']
    ll=obj['labels']
    if not isinstance(ll,list) or len(ll)!=len(units):return ['count']
    errors=[]
    for u,x in zip(units,ll):
        if not isinstance(x,dict) or set(x)!={'unit_id','label','reason'}:errors.append('fields');continue
        if type(x['unit_id']) is not int or x['unit_id']!=u['unit_id']:errors.append('id_order')
        if x['label'] not in ('relevant','other','boilerplate'):errors.append('label')
        if not isinstance(x['reason'],str) or not x['reason'].strip():errors.append('reason')
    return errors
def request(endpoint,payload=None,timeout=300):
    data=None if payload is None else json.dumps(payload).encode()
    req=urllib.request.Request('http://127.0.0.1:11434'+endpoint,data,{'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as r:return json.load(r)
def prepare():
    cases=rows(SOURCE/'cases.jsonl');assert len(cases)==36
    data=[{**x,'review_sha256':hashlib.sha256(x['text'].encode()).hexdigest(),'units':split(x['text'])} for x in cases]
    assert len({x['case_id'] for x in data})==36
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'inputs.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in data))
    manifest={'protocol':'gate_ratio_v05_experimental_not_adopted','model':MODEL,'options':OPTIONS,'think':False,'thresholds_percent':THRESHOLDS,'comparison_control':'any_relevant_unit','no_retries':True,'planned_calls':36,'units':sum(len(x['units']) for x in data),'emotion_calls':0,'files_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [SOURCE/'cases.jsonl',SOURCE/'decisions.jsonl',PROMPT,PROTOCOL,OUT/'inputs.jsonl',Path(__file__)]},'baseline_weight_digest_not_recorded':True,'zero_denominator':'REJECT','ratio_denominator':'relevant + other; boilerplate excluded','holdout':False}
    write(OUT/'manifest.json',manifest)
    sample=split('A place. Another assertion, but a contrasting assertion; Last one!')
    assert len(sample)==4
    assert not validate({'labels':[{'unit_id':u['unit_id'],'label':'other','reason':'test'} for u in sample]},sample)
    assert validate({'labels':[]},sample)
    print('PREPARED',len(data),'reviews',manifest['units'],'units',flush=True)
    return data
def schema(units):
    return {'type':'object','additionalProperties':False,'required':['labels'],'properties':{'labels':{'type':'array','minItems':len(units),'maxItems':len(units),'items':{'type':'object','additionalProperties':False,'required':['unit_id','label','reason'],'properties':{'unit_id':{'type':'integer','enum':[u['unit_id'] for u in units]},'label':{'type':'string','enum':['relevant','other','boilerplate']},'reason':{'type':'string'}}}}}}
def run():
    data=prepare();tags=request('/api/tags');tag=next(x for x in tags['models'] if x['name']==MODEL)
    write(OUT/'model_identity.json',{'model':tag,'ollama_version':request('/api/version')})
    request('/api/generate',{'model':MODEL,'options':OPTIONS,'keep_alive':'20m','stream':False},600)
    done={x['case_id'] for x in rows(OUT/'predictions.jsonl')}
    for row in data:
        if row['case_id'] in done:continue
        start=time.monotonic();rec={'case_id':row['case_id'],'raw':'','parsed':None,'model_digest':tag['digest']}
        try:
            user={'full_review':row['text'],'units':[{'unit_id':u['unit_id'],'text':u['text']} for u in row['units']]}
            reply=request('/api/chat',{'model':MODEL,'messages':[{'role':'system','content':PROMPT.read_text()},{'role':'user','content':json.dumps(user,ensure_ascii=False)}],'format':schema(row['units']),'stream':False,'think':False,'options':OPTIONS,'keep_alive':'20m'})
            rec['raw']=reply['message']['content'];rec['parsed']=json.loads(rec['raw']);rec['metadata']={k:reply.get(k) for k in ['eval_count','prompt_eval_count','total_duration','done_reason']}
        except Exception as ex:rec['exception']=repr(ex)
        rec['validation_errors']=validate(rec['parsed'],row['units']);rec['strict_valid']=not rec['validation_errors'];rec['seconds']=round(time.monotonic()-start,3)
        with (OUT/'predictions.jsonl').open('a') as f:f.write(json.dumps(rec,ensure_ascii=False)+'\n');f.flush()
        print('CASE',row['case_id'],rec['strict_valid'],rec['seconds'],flush=True)
    report();print('ALL_36_REVIEWS_ATTEMPTED',flush=True)
def report():
    inputs={x['case_id']:x for x in rows(OUT/'inputs.jsonl')};base={x['review_id']:x for x in rows(SOURCE/'decisions.jsonl')};records=rows(OUT/'predictions.jsonl');detail=[];units=[]
    for r in records:
        if not r['strict_valid']:continue
        row=inputs[r['case_id']];counts=collections.Counter(x['label'] for x in r['parsed']['labels']);den=counts['relevant']+counts['other'];num=counts['relevant'];wn=wd=0
        for u,label in zip(row['units'],r['parsed']['labels']):
            units.append({'case_id':r['case_id'],**u,**label});wn+=u['words']*(label['label']=='relevant');wd+=u['words']*(label['label']!='boilerplate')
        detail.append({'case_id':r['case_id'],'baseline_keep':base[r['case_id']]['parsed']['keep'],'counts':dict(counts),'relevant':num,'substantive':den,'ratio':num/den if den else 0,'word_ratio':wn/wd if wd else 0,'any_keep':num>0,**{'keep_'+str(t):bool(num and 100*num>=t*den) for t in THRESHOLDS},**{'word_keep_'+str(t):bool(wn and 100*wn>=t*wd) for t in THRESHOLDS}})
    summary={'attempted':len(records),'valid':len(detail),'invalid':{x['case_id']:x['validation_errors'] for x in records if not x['strict_valid']},'unattempted':sorted(set(inputs)-{x['case_id'] for x in records}),'old_keep_all_36':sum(x['parsed']['keep'] for x in base.values()),'old_keep_matched_valid':sum(x['baseline_keep'] for x in detail),'any_relevant_keep':sum(x['any_keep'] for x in detail),'thresholds':{},'accuracy_claim':False}
    for t in THRESHOLDS:
        k='keep_'+str(t);summary['thresholds'][str(t)]={'keep':sum(x[k] for x in detail),'reject':sum(not x[k] for x in detail),'newly_rejected_vs_old':[x['case_id'] for x in detail if x['baseline_keep'] and not x[k]],'newly_kept_vs_old':[x['case_id'] for x in detail if not x['baseline_keep'] and x[k]],'rejected_vs_any_control':[x['case_id'] for x in detail if x['any_keep'] and not x[k]],'word_weighted_keep':sum(x['word_keep_'+str(t)] for x in detail)}
    write(OUT/'summary.json',summary);write(OUT/'review_comparison.json',detail)
    with (OUT/'unit_labels.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=['case_id','unit_id','start','end','text','words','label','reason']);w.writeheader();w.writerows(units)
    print(json.dumps(summary),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','run','report']);a=p.parse_args();globals()[a.stage]()
