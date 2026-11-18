#!/usr/bin/env python3
"""Paired whole-review v5/v5.1-hostile-rant gate and latency test, one unchanged gate model."""
import argparse,hashlib,json,math,shutil,statistics,subprocess,time,urllib.request
from pathlib import Path
import stage1a_review_eligibility_gate_v04_20261116 as baseline
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'research_audit/stage1a_review_gate_v04_regression_qwen8b_2026-11-16'
OUT=ROOT/'research_audit/stage1a_gate_rant_v51_test_2026-11-18'
REV_PROMPT=ROOT/'Docs/STAGE1A_REVIEW_ELIGIBILITY_GATE_PROMPT_V0_5_1_RANT_DRAFT_2026-11-18.md'
REV_BOOK=ROOT/'Docs/STAGE1A_REVIEW_ELIGIBILITY_GATE_CODEBOOK_V0_5_1_RANT_DRAFT_2026-11-18.md'
MODEL='qwen3:8b'
OPTIONS={**baseline.OPTIONS,'num_thread':8}
EXPECTED_DIGEST='500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41'
CONDITIONS={'v5_control':(ROOT/'Docs/STAGE1A_REVIEW_ELIGIBILITY_GATE_PROMPT_V0_5_SCENARIOS_DRAFT_2026-11-17.md',ROOT/'Docs/STAGE1A_REVIEW_ELIGIBILITY_GATE_CODEBOOK_V0_5_SCENARIOS_DRAFT_2026-11-17.md'),'v51_rant':(REV_PROMPT,REV_BOOK)}
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
    assert 'COMMON FALSE-POSITIVE SCENARIOS' in system(REV_PROMPT) and 'EXCEPTIONS' in system(REV_PROMPT)
    config=json.loads((ROOT/'configs/stage1a_review_eligibility_gate_v051_rant_draft.json').read_text())
    assert baseline.filehash(REV_PROMPT)==config['prompt_sha256'] and baseline.filehash(REV_BOOK)==config['codebook_sha256']
    assert baseline.filehash(ROOT/config['front_runner_config'])==config['front_runner_config_sha256']
    assert all(x not in system(REV_PROMPT) for x in ['T06','K01','State Park','Chelsea'])
    OUT.mkdir(parents=True,exist_ok=True)
    manifest={'protocol':'paired_gate_v5_vs_v51_rant','status':'experimental_not_adopted','model':MODEL,'expected_model_digest':EXPECTED_DIGEST,'options':OPTIONS,'think':False,'scope':'complete_original_review_before_segmentation','reviews':36,'planned_calls':72,'conditions':{k:{'prompt_path':str(p.relative_to(ROOT)),'prompt_sha256':baseline.filehash(p),'codebook_path':str(b.relative_to(ROOT)),'codebook_sha256':baseline.filehash(b),'system_sha256':hashlib.sha256(system(p).encode()).hexdigest()} for k,(p,b) in CONDITIONS.items()},'input_sha256':baseline.filehash(SOURCE/'cases.jsonl'),'schema_sha256':baseline.filehash(baseline.SCHEMA),'runner_sha256':baseline.filehash(Path(__file__)),'no_retries':True,'codebook_runtime_role':'supporting specification; executable system message is standalone, as in v0.4','prior_verdicts_and_labels_in_input':False,'no_ratio_no_emotion_no_ET':True,'no_independent_accuracy_claim':True,'latency_protocol':'one sequential block per condition; full batch plus warm 35-case comparison excluding K01 from both; fixed order and unequal generated lengths limit generalization','example_inventory_change':'none versus tested v5; v5.1 adds only whole-review hostile-rant exclusion and safeguards; no spam/duplicate filter added'}
    write(OUT/'manifest.json',manifest)
    print('PREPARED 36 reviews x 2 prompts = 72 calls',flush=True)
    return data,schema
def run():
    data,schema=prepare();tags=request('/api/tags');tag=next(x for x in tags['models'] if x['name']==MODEL);assert tag['digest']==EXPECTED_DIGEST
    gpu=subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader'],text=True) if shutil.which('nvidia-smi') else None
    write(OUT/'runtime_environment.json',{'model':tag,'ollama':request('/api/version'),'gpu':gpu,'compute':'GPU' if gpu else 'CPU','cpu':Path('/proc/cpuinfo').read_text().split('model name',1)[-1].splitlines()[0].strip(),'python':subprocess.check_output(['python3','--version'],text=True),'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()})
    request('/api/generate',{'model':MODEL,'options':OPTIONS,'keep_alive':'20m','stream':False},600)
    done={(r['condition'],r['review_id']) for r in rows(OUT/'decisions.jsonl')}
    for condition,(prompt,book) in CONDITIONS.items():
        for x in data:
            if (condition,x['review_id']) in done:continue
            rec={'condition':condition,**{k:v for k,v in x.items() if k!='text'},'review_text':x['text'],'review_sha256':hashlib.sha256(x['text'].encode()).hexdigest(),'raw':'','parsed':None,'errors':[]};start=time.monotonic()
            try:
                reply=request('/api/chat',{'model':MODEL,'messages':[{'role':'system','content':system(prompt)},{'role':'user','content':json.dumps({'review_text':x['text']},ensure_ascii=False)}],'format':schema,'stream':False,'think':False,'options':OPTIONS,'keep_alive':'20m'})
                rec['raw']=reply.get('message',{}).get('content','');rec['parsed']=json.loads(rec['raw']);rec['errors']=baseline.validate(rec['parsed'],x['text']);rec['metadata']={k:reply.get(k) for k in ['eval_count','prompt_eval_count','load_duration','prompt_eval_duration','eval_duration','total_duration','done_reason']}
            except Exception as ex:rec['errors']=[repr(ex)]
            rec['strict_valid']=not rec['errors'];rec['seconds']=round(time.monotonic()-start,3)
            with (OUT/'decisions.jsonl').open('a') as f:f.write(json.dumps(rec,ensure_ascii=False)+'\n');f.flush()
            print(condition,x['review_id'],rec['parsed'].get('keep') if isinstance(rec['parsed'],dict) else 'INVALID',rec['strict_valid'],rec['seconds'],flush=True)
    report();print('ALL_72_REQUESTS_FINISHED',flush=True)
def report():
    rr=rows(OUT/'decisions.jsonl');old={x['review_id']:x for x in rows(SOURCE/'decisions.jsonl')};maps={c:{r['review_id']:r for r in rr if r['condition']==c and isinstance(r['parsed'],dict) and type(r['parsed'].get('keep')) is bool} for c in CONDITIONS};summary={'planned_calls':72,'attempted':len(rr),'conditions':{},'historical_v04_keep':sum(x['parsed']['keep'] for x in old.values()),'no_accuracy_claim':True}
    for c,m in maps.items():
        cr=[x for x in rr if x['condition']==c];summary['conditions'][c]={'attempted':len(cr),'parseable_verdicts':len(m),'keep':sum(x['parsed']['keep'] for x in m.values()),'reject':sum(not x['parsed']['keep'] for x in m.values()),'strict_valid':sum(x['strict_valid'] for x in cr),'invalid':{x['review_id']:x['errors'] for x in cr if not x['strict_valid']},'unattempted':sorted(set(old)-{x['review_id'] for x in cr})}
    paired=set(maps['v5_control'])&set(maps['v51_rant']);comparison=[]
    for sid in old:
        a=maps['v5_control'].get(sid);b=maps['v51_rant'].get(sid)
        comparison.append({'review_id':sid,'historical_v04':old[sid]['parsed'],'v5_control':None if a is None else a['parsed'],'v51_rant':None if b is None else b['parsed'],'strict_valid_control':bool(a and a['strict_valid']),'strict_valid_revised':bool(b and b['strict_valid']),'review_text':old[sid]['review_text']})
    summary['paired_parseable']=len(paired);summary['paired_changed']=[sid for sid in old if sid in paired and maps['v5_control'][sid]['parsed']['keep']!=maps['v51_rant'][sid]['parsed']['keep']];summary['revised_vs_historical_changed']=[sid for sid in old if sid in maps['v51_rant'] and old[sid]['parsed']['keep']!=maps['v51_rant'][sid]['parsed']['keep']];summary['control_vs_historical_changed']=[sid for sid in old if sid in maps['v5_control'] and old[sid]['parsed']['keep']!=maps['v5_control'][sid]['parsed']['keep']]
    speed={}
    for condition in CONDITIONS:
        all_calls=[x for x in rr if x['condition']==condition]
        warm=[x for x in all_calls if x['review_id']!='K01' and isinstance(x.get('parsed'),dict)]
        elapsed=sorted(x['seconds'] for x in warm)
        speed[condition]={'calls':len(all_calls),'warm_calls':len(warm),'batch_seconds':round(sum(x['seconds'] for x in all_calls),3),'warm_median_seconds':statistics.median(elapsed) if elapsed else None,'warm_p90_seconds':elapsed[math.ceil(.9*len(elapsed))-1] if elapsed else None,'median_output_tokens':statistics.median(x.get('metadata',{}).get('eval_count',0) or 0 for x in warm) if warm else None,'median_input_eval_seconds':statistics.median((x.get('metadata',{}).get('prompt_eval_duration',0) or 0)/1e9 for x in warm) if warm else None,'median_generation_seconds':statistics.median((x.get('metadata',{}).get('eval_duration',0) or 0)/1e9 for x in warm) if warm else None}
    if all(speed[k]['warm_median_seconds'] for k in CONDITIONS):speed['median_latency_change_percent']=round((speed['v51_rant']['warm_median_seconds']/speed['v5_control']['warm_median_seconds']-1)*100,2)
    speed['note']='CPU8, one pass, fixed block order, prompt-cache reuse within each block; K01 excluded from warmed medians in both conditions. Output lengths differ. Not a GPU, uncached or repeated-load benchmark.'
    summary['speed']=speed
    write(OUT/'summary.json',summary);write(OUT/'comparison.json',comparison);print(json.dumps(summary),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','run','report']);a=p.parse_args();globals()[a.stage]()
