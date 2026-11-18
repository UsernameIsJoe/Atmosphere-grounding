#!/usr/bin/env python3
"""Paired model-size test; same frozen v5 system prompt, inputs and generation settings."""
import hashlib,json,statistics,subprocess,time
from pathlib import Path
import stage1a_review_eligibility_gate_v04_20261116 as base
import stage1a_gate_scenarios_v5_test_20261117 as util
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'research_audit/stage1a_gate_v5_qwen14b_test_2026-11-18'
SOURCE=util.SOURCE
PROMPT=util.REV_PROMPT
BOOK=util.REV_BOOK
OPTIONS={**base.OPTIONS,'num_thread':8}
MODELS=['qwen3:8b','qwen3:14b']
EXPECTED={'qwen3:8b':'500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41','qwen3:14b':'bdbd181c33f2'}
def run():
    OUT.mkdir(parents=True,exist_ok=True)
    assert not (OUT/'decisions.jsonl').exists(),'Do not overwrite or duplicate a run.'
    data=list(base.rows(SOURCE/'cases.jsonl',0));assert len(data)==36
    ref={r['review_id']:r for r in util.rows(ROOT/'research_audit/stage1a_gate_scenarios_v5_test_2026-11-17/decisions.jsonl') if r['condition']=='v5_scenarios'}
    for r in data:assert r['text']==ref[r['review_id']]['review_text']
    assert base.filehash(PROMPT)=='6df94563003405f8e5097be4174eb56725aeef8427c79a105230f45d3839395f'
    assert base.filehash(BOOK)=='e335b11e2805304f27540a65f94dc6ac392c3859775658d5b1cab221bc90bcd6'
    schema=json.loads(base.SCHEMA.read_text());system=util.system(PROMPT)
    tags={x['name']:x for x in util.request('/api/tags')['models']}
    for name in MODELS:
        assert tags[name]['digest'].startswith(EXPECTED[name]),(name,tags[name])
        assert tags[name]['details']['quantization_level']=='Q4_K_M'
    util.write(OUT/'manifest.json',{'reviews':36,'planned_calls':72,'models':{m:tags[m] for m in MODELS},'options':OPTIONS,'think':False,'prompt_path':str(PROMPT.relative_to(ROOT)),'prompt_sha256':base.filehash(PROMPT),'system_sha256':hashlib.sha256(system.encode()).hexdigest(),'codebook_sha256':base.filehash(BOOK),'input_sha256':base.filehash(SOURCE/'cases.jsonl'),'schema_sha256':base.filehash(base.SCHEMA),'runner_sha256':base.filehash(Path(__file__)),'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'scope':'entire original review, before segmentation','no_retries':True,'prompt_and_codebook_unchanged':True,'prior_labels_or_verdicts_in_model_input':False,'status':'experimental_not_adopted','codebook_runtime_role':'supporting specification, standalone prompt only as in tested v5','confounds':'Model-size comparison also changes trained checkpoint; one fixed block order, quantized GPU run, no general latency or accuracy claim.'})
    util.write(OUT/'runtime.json',{'ollama':util.request('/api/version'),'gpu':subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader'],text=True),'python':subprocess.check_output(['python3','--version'],text=True)})
    print('PREPARED 36 REVIEWS X 2 MODELS = 72 CALLS',flush=True)
    residency={}
    for model in MODELS:
        util.request('/api/generate',{'model':model,'options':OPTIONS,'keep_alive':'20m','stream':False},600)
        ps=util.request('/api/ps');residency[model]=ps;util.write(OUT/'gpu_residency.json',residency)
        assert any(m.get('size_vram',0)>0 and m.get('name')==model for m in ps['models']),'GPU residency missing'
        for x in data:
            rec={'model':model,**{k:v for k,v in x.items() if k!='text'},'review_text':x['text'],'review_sha256':hashlib.sha256(x['text'].encode()).hexdigest(),'raw':'','parsed':None,'errors':[]};start=time.monotonic()
            try:
                reply=util.request('/api/chat',{'model':model,'messages':[{'role':'system','content':system},{'role':'user','content':json.dumps({'review_text':x['text']},ensure_ascii=False)}],'format':schema,'stream':False,'think':False,'options':OPTIONS,'keep_alive':'20m'},300)
                rec['raw']=reply.get('message',{}).get('content','');rec['parsed']=json.loads(rec['raw']);rec['errors']=base.validate(rec['parsed'],x['text']);rec['metadata']={k:reply.get(k) for k in ['eval_count','prompt_eval_count','load_duration','prompt_eval_duration','eval_duration','total_duration','done_reason']}
            except Exception as e:rec['errors']=[repr(e)]
            rec['strict_valid']=not rec['errors'];rec['seconds']=round(time.monotonic()-start,3)
            with (OUT/'decisions.jsonl').open('a') as f:f.write(json.dumps(rec,ensure_ascii=False)+'\n');f.flush()
            print(model,x['review_id'],rec['parsed'].get('keep') if isinstance(rec['parsed'],dict) else 'INVALID',rec['strict_valid'],rec['seconds'],flush=True)
        util.request('/api/generate',{'model':model,'keep_alive':0,'stream':False},60)
    rr=util.rows(OUT/'decisions.jsonl');mm={m:{r['review_id']:r for r in rr if r['model']==m} for m in MODELS};summary={'planned_calls':72,'attempted':len(rr),'models':{}}
    for m,rows in mm.items():
        valid=[r for r in rows.values() if isinstance(r['parsed'],dict) and type(r['parsed'].get('keep')) is bool]
        summary['models'][m]={'attempted':len(rows),'parseable_verdicts':len(valid),'keep':sum(r['parsed']['keep'] for r in valid),'reject':sum(not r['parsed']['keep'] for r in valid),'strict_valid':sum(r['strict_valid'] for r in rows.values()),'invalid':{r['review_id']:r['errors'] for r in rows.values() if not r['strict_valid']},'batch_seconds':round(sum(r['seconds'] for r in rows.values()),3),'warm_median_seconds':statistics.median(r['seconds'] for r in rows.values() if r['review_id']!='K01')}
    comp=[]
    for x in data:
        sid=x['review_id'];a=mm[MODELS[0]][sid];b=mm[MODELS[1]][sid]
        comp.append({'review_id':sid,'review_text':x['text'],'archived_8b':ref[sid]['parsed'],'fresh_8b':a['parsed'],'qwen14b':b['parsed'],'strict_8b':a['strict_valid'],'strict_14b':b['strict_valid']})
    complete=[r for r in comp if isinstance(r['fresh_8b'],dict) and isinstance(r['qwen14b'],dict)]
    summary['changed_vs_fresh_8b']=[r['review_id'] for r in complete if r['fresh_8b']['keep']!=r['qwen14b']['keep']]
    summary['fresh_8b_vs_archived_changed']=[r['review_id'] for r in complete if r['fresh_8b']['keep']!=r['archived_8b']['keep']]
    summary['q14_vs_archived_changed']=[r['review_id'] for r in complete if r['qwen14b']['keep']!=r['archived_8b']['keep']]
    labels={'U01':False,'U02':True,'N05':False}
    summary['current_three_review_human_audit']={m:{'agreements':sum(mm[m][sid]['parsed']['keep']==expected for sid,expected in labels.items() if isinstance(mm[m][sid]['parsed'],dict)),'scope':labels} for m in MODELS}
    summary['not_full_cohort_accuracy']=True
    util.write(OUT/'comparison.json',comp);util.write(OUT/'summary.json',summary)
    print(json.dumps(summary),flush=True);print('ALL_72_REQUESTS_FINISHED',flush=True)
if __name__=='__main__':run()
