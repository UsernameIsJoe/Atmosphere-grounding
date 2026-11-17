#!/usr/bin/env python3
"""Paired whole-review v0.4/v0.6 focus-first gate test, one unchanged gate model."""
import argparse,collections,hashlib,json,shutil,subprocess,time,urllib.request
from pathlib import Path
import stage1a_review_eligibility_gate_v04_20261116 as baseline
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'research_audit/stage1a_review_gate_v04_regression_qwen8b_2026-11-16'
OUT=ROOT/'research_audit/stage1a_gate_focus_v06_test_2026-11-17'
REV_PROMPT=ROOT/'Docs/STAGE1A_REVIEW_ELIGIBILITY_GATE_PROMPT_V0_6_FOCUS_DRAFT_2026-11-17.md'
REV_BOOK=ROOT/'Docs/STAGE1A_REVIEW_ELIGIBILITY_GATE_CODEBOOK_V0_6_FOCUS_DRAFT_2026-11-17.md'
MODEL='qwen3:8b'
OPTIONS={**baseline.OPTIONS,'num_thread':8}
EXPECTED_DIGEST='500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41'
CONDITIONS={'v04_control':(baseline.PROMPT,baseline.CODEBOOK),'v06_focus':(REV_PROMPT,REV_BOOK)}
def rows(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def system(p):
    fence=chr(96)*3
    return p.read_text().split('## Exact system message',1)[1].split(fence+'text',1)[1].split(fence,1)[0].strip()
def request(endpoint,payload=None,timeout=300):
    req=urllib.request.Request('http://127.0.0.1:11434'+endpoint,None if payload is None else json.dumps(payload).encode(),{'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as f:return json.load(f)
def prepare():
    data=list(baseline.rows(SOURCE/'cases.jsonl',0));assert len(data)==36
    old={r['review_id']:r for r in rows(SOURCE/'decisions.jsonl')}
    for x in data:assert x['text']==old[x['review_id']]['review_text']
    schema=json.loads(baseline.SCHEMA.read_text());assert set(schema['properties'])=={'keep','anchor_quote','reason'}
    assert 'review-focus-first eligibility gate' in system(REV_PROMPT)
    assert all(x not in system(REV_PROMPT) for x in ['T06','K01','State Park','Chelsea'])
    fs=json.loads((ROOT/'configs/stage1a_review_eligibility_gate_v0_6_focus_draft.json').read_text());assert set(fs['properties'])=={'review_focus','focus_summary','keep','anchor_quote','reason'}
    OUT.mkdir(parents=True,exist_ok=True)
    manifest={'protocol':'paired_gate_v04_vs_v06_focus','status':'experimental_not_adopted','model':MODEL,'expected_model_digest':EXPECTED_DIGEST,'options':OPTIONS,'think':False,'scope':'complete_original_review_before_segmentation','reviews':36,'planned_calls':72,'conditions':{k:{'prompt_path':str(p.relative_to(ROOT)),'prompt_sha256':baseline.filehash(p),'codebook_path':str(b.relative_to(ROOT)),'codebook_sha256':baseline.filehash(b),'system_sha256':hashlib.sha256(system(p).encode()).hexdigest()} for k,(p,b) in CONDITIONS.items()},'input_sha256':baseline.filehash(SOURCE/'cases.jsonl'),'schema_sha256':baseline.filehash(baseline.SCHEMA),'focus_schema_sha256':baseline.filehash(ROOT/'configs/stage1a_review_eligibility_gate_v0_6_focus_draft.json'),'runner_sha256':baseline.filehash(Path(__file__)),'no_retries':True,'codebook_runtime_role':'supporting specification; executable system message is standalone, as in v0.4','prior_verdicts_and_labels_in_input':False,'no_ratio_no_emotion_no_ET':True,'no_independent_accuracy_claim':True}
    write(OUT/'manifest.json',manifest)
    assert not examine({'review_focus':'place','focus_summary':'Place access','keep':True,'anchor_quote':'x','reason':'Access'},'x','v06_focus')
    assert 'encounter_keep_inconsistent' in examine({'review_focus':'encounter','focus_summary':'Event outcome','keep':True,'anchor_quote':'x','reason':'Outcome'},'x','v06_focus')
    assert 'nonexact_keep_quote' in examine({'review_focus':'place','focus_summary':'Place access','keep':True,'anchor_quote':'y','reason':'Access'},'x','v06_focus')
    print('PREPARED 36 reviews x 2 prompts = 72 calls',flush=True)
    return data,schema
def examine(obj,text,condition):
    if condition=='v04_control':return baseline.validate(obj,text)
    expected=['review_focus','focus_summary','keep','anchor_quote','reason']
    if not isinstance(obj,dict) or set(obj)!=set(expected):return ['structure']
    errs=baseline.validate({k:obj[k] for k in ['keep','anchor_quote','reason']},text)
    if obj['review_focus'] not in ('place','encounter','mixed'):errs.append('focus_enum')
    if not isinstance(obj['focus_summary'],str) or not obj['focus_summary'].strip():errs.append('focus_summary')
    if obj['review_focus']=='encounter' and obj['keep'] is True:errs.append('encounter_keep_inconsistent')
    if list(obj)[:2]!=expected[:2]:errs.append('focus_not_emitted_first')
    return errs

def run():
    data,schema=prepare();focus_schema=json.loads((ROOT/'configs/stage1a_review_eligibility_gate_v0_6_focus_draft.json').read_text());tags=request('/api/tags');tag=next(x for x in tags['models'] if x['name']==MODEL);assert tag['digest']==EXPECTED_DIGEST
    gpu=subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader'],text=True) if shutil.which('nvidia-smi') else None
    write(OUT/'runtime_environment.json',{'model':tag,'ollama':request('/api/version'),'gpu':gpu,'compute':'GPU' if gpu else 'CPU','cpu':Path('/proc/cpuinfo').read_text().split('model name',1)[-1].splitlines()[0].strip(),'python':subprocess.check_output(['python3','--version'],text=True),'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()})
    request('/api/generate',{'model':MODEL,'options':OPTIONS,'keep_alive':'20m','stream':False},600)
    done={(r['condition'],r['review_id']) for r in rows(OUT/'decisions.jsonl')}
    for condition,(prompt,book) in CONDITIONS.items():
        for x in data:
            if (condition,x['review_id']) in done:continue
            rec={'condition':condition,**{k:v for k,v in x.items() if k!='text'},'review_text':x['text'],'review_sha256':hashlib.sha256(x['text'].encode()).hexdigest(),'raw':'','parsed':None,'errors':[]};start=time.monotonic()
            try:
                reply=request('/api/chat',{'model':MODEL,'messages':[{'role':'system','content':system(prompt)},{'role':'user','content':json.dumps({'review_text':x['text']},ensure_ascii=False)}],'format':focus_schema if condition=='v06_focus' else schema,'stream':False,'think':False,'options':OPTIONS,'keep_alive':'20m'})
                rec['raw']=reply.get('message',{}).get('content','');rec['parsed']=json.loads(rec['raw']);rec['errors']=examine(rec['parsed'],x['text'],condition);rec['metadata']={k:reply.get(k) for k in ['eval_count','prompt_eval_count','total_duration','done_reason']}
            except Exception as ex:rec['errors']=[repr(ex)]
            rec['strict_valid']=not rec['errors'];rec['seconds']=round(time.monotonic()-start,3)
            with (OUT/'decisions.jsonl').open('a') as f:f.write(json.dumps(rec,ensure_ascii=False)+'\n');f.flush()
            print(condition,x['review_id'],rec['parsed'].get('keep') if isinstance(rec['parsed'],dict) else 'INVALID',rec['strict_valid'],rec['seconds'],flush=True)
    report();print('ALL_72_REQUESTS_FINISHED',flush=True)
def report():
    rr=rows(OUT/'decisions.jsonl');old={x['review_id']:x for x in rows(SOURCE/'decisions.jsonl')};maps={c:{r['review_id']:r for r in rr if r['condition']==c and isinstance(r['parsed'],dict) and type(r['parsed'].get('keep')) is bool} for c in CONDITIONS};summary={'planned_calls':72,'attempted':len(rr),'conditions':{},'historical_v04_keep':sum(x['parsed']['keep'] for x in old.values()),'no_accuracy_claim':True}
    for c,m in maps.items():
        cr=[x for x in rr if x['condition']==c];summary['conditions'][c]={'attempted':len(cr),'parseable_verdicts':len(m),'keep':sum(x['parsed']['keep'] for x in m.values()),'reject':sum(not x['parsed']['keep'] for x in m.values()),'strict_valid':sum(x['strict_valid'] for x in cr),'invalid':{x['review_id']:x['errors'] for x in cr if not x['strict_valid']},'unattempted':sorted(set(old)-{x['review_id'] for x in cr})}
    paired=set(maps['v04_control'])&set(maps['v06_focus']);comparison=[]
    for sid in old:
        a=maps['v04_control'].get(sid);b=maps['v06_focus'].get(sid)
        comparison.append({'review_id':sid,'historical_v04':old[sid]['parsed'],'v04_control':None if a is None else a['parsed'],'v06_focus':None if b is None else b['parsed'],'strict_valid_control':bool(a and a['strict_valid']),'strict_valid_revised':bool(b and b['strict_valid']),'review_text':old[sid]['review_text']})
    summary['paired_parseable']=len(paired);summary['paired_changed']=[sid for sid in old if sid in paired and maps['v04_control'][sid]['parsed']['keep']!=maps['v06_focus'][sid]['parsed']['keep']];summary['revised_vs_historical_changed']=[sid for sid in old if sid in maps['v06_focus'] and old[sid]['parsed']['keep']!=maps['v06_focus'][sid]['parsed']['keep']];summary['control_vs_historical_changed']=[sid for sid in old if sid in maps['v04_control'] and old[sid]['parsed']['keep']!=maps['v04_control'][sid]['parsed']['keep']]
    summary['focus_counts']=dict(collections.Counter(x['parsed'].get('review_focus','missing') for x in maps['v06_focus'].values()));summary['focus_keep_counts']=dict(collections.Counter(x['parsed'].get('review_focus','missing')+':'+str(x['parsed']['keep']) for x in maps['v06_focus'].values()));write(OUT/'summary.json',summary);write(OUT/'comparison.json',comparison);print(json.dumps(summary),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','run','report']);a=p.parse_args();globals()[a.stage]()
