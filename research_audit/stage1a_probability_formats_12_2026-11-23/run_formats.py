#!/usr/bin/env python3
"""Cold Qwen readout-format diagnostic, reusing previously measured payloads."""
import hashlib, importlib.util, itertools, json, math, os, random, re, subprocess, time, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('frozen_pilot',ROOT/'frozen_pilot/run_pilot.py')
pilot=importlib.util.module_from_spec(spec);spec.loader.exec_module(pilot)
STATES=tuple(pilot.STATES)
MODEL='qwen3.8:27b'
WORDS=dict(zip(STATES,('none','support','opposition','both')))
DESC=dict(zip(STATES,(
    'No defensible supporting OR opposing claim about calm is supplied by the target.',
    'At least one defensible supporting claim about calm; no opposing claim.',
    'At least one defensible opposing claim about calm; no supporting claim.',
    'At least one defensible supporting claim AND at least one opposing claim about calm.')))

def sha(x):
    if isinstance(x,str):x=x.encode()
    if not isinstance(x,bytes):x=json.dumps(x,ensure_ascii=False,sort_keys=True).encode()
    return hashlib.sha256(x).hexdigest()

def request(host,path,body=None):
    data=None if body is None else json.dumps(body,ensure_ascii=False).encode()
    req=urllib.request.Request(host+path,data=data,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=180) as r:
        b=r.read();return json.loads(b) if b else {}

def options(fmt,assignment):
    if fmt=='text':return WORDS
    chars='ABCD' if fmt=='letters' else '1234'
    return dict(zip(STATES,(chars*2)[assignment:assignment+4]))

def system_prompt(fmt,assignment,order):
    mapping=options(fmt,assignment)
    prompt=pilot.probe_prompt(mapping)
    original='\n'.join(mapping[s]+': '+DESC[s] for s in STATES)
    ordered=STATES[order:]+STATES[:order]
    if fmt=='text':
        # Definitions have no arbitrary option IDs. Meaningful state names
        # are embedded in the corresponding sentences and move with them.
        lines=[DESC[s]+' The state name is '+mapping[s]+'.' for s in ordered]
        prompt=prompt.replace('corresponding single letter','corresponding single state word')
    else:lines=[mapping[s]+': '+DESC[s] for s in ordered]
    assert prompt.count(original)==1
    prompt=prompt.replace(original,'\n'.join(lines))
    if fmt=='numbers':
        prompt=prompt.replace('corresponding single letter','corresponding single digit')
        prompt=prompt.replace('reasoning, numbers, percentages','reasoning, explanations, percentages')
    return prompt

def conditions():
    result=[]
    for fmt in ('letters','numbers','text'):
        pairs=[(0,o) for o in range(4)]
        if fmt!='text':pairs +=[(a,0) for a in range(1,4)]
        for a,o in pairs:
            result.append({'format':fmt,'assignment':a,'order':o,'id':f'{fmt}_a{a}_o{o}',
                'mapping':options(fmt,a),'system_prompt':system_prompt(fmt,a,o)})
    assert len(result)==18
    return result

def completion_payload(prompt,n_probs=20):
    return {'prompt':prompt,'n_predict':1,'n_probs':n_probs,'temperature':0,'seed':42,
        'top_k':0,'top_p':1,'min_p':0,'repeat_penalty':1,'presence_penalty':0,
        'frequency_penalty':0,'n_keep':4,'stream':False,'post_sampling_probs':False,
        'cache_prompt':False,'return_tokens':True,'timings_per_token':True}

def measure(response,mapping):
    entries=response.get('completion_probabilities') or []
    if not entries:return {'valid':False,'error':'no native log probabilities'}
    e=entries[0]
    lp={a['token']:float(a['logprob']) for a in e.get('top_logprobs',[])}
    lp[e['token']]=float(e['logprob'])
    known={s:lp[c] for s,c in mapping.items() if c in lp}
    if not known:return {'valid':False,'error':'no candidate in returned top-k'}
    ps={s:math.exp(v) for s,v in known.items()};mass=sum(ps.values())
    missing=[s for s in STATES if s not in known]
    cutoff=math.exp(min(float(a['logprob']) for a in e['top_logprobs']))
    intervals={s:[ps[s]/(mass+len(missing)*cutoff),ps[s]/mass] if s in ps
        else [0.,cutoff/(mass+cutoff)] for s in STATES}
    reverse={v:k for k,v in mapping.items()}
    content=response.get('content','')
    selected=reverse.get(content)
    return {'valid':selected is not None,'raw_text':content,'selected_state':selected,
        'candidate_mass':mass,'native_state_logprobs':known,'missing_states':missing,
        'complete_distribution':not missing,'state_probability_intervals':intervals,
        'conditional_probabilities':{s:ps[s]/mass for s in STATES} if not missing else None,
        'topk_cutoff_probability':cutoff,'pairwise_logit_margins':{
            a+'__'+b:known[a]-known[b] for a,b in itertools.combinations(STATES,2) if a in known and b in known}}

def prepare():
    rows=pilot.inputs();manifest=json.loads((ROOT/'source_manifest.json').read_text())
    assert sha(rows)==manifest['cases_sha256']
    for name,meta in manifest['source_files'].items():assert sha((ROOT/name).read_bytes())==meta['sha256'],name
    old=json.loads((ROOT/'previous_rendered_prompts.json').read_text())
    indexed={(r['case_id'],int(r['rotation'][-1])):r for r in old}
    cs=conditions()
    for r in rows:
        for a in range(4):
            assert system_prompt('letters',a,0)==indexed[(r['case_id'],a)]['request']['messages'][0]['content']
    manifest.update({'protocol':'qwen_cold_formats_and_gemma_offline_v1','runner_sha256':sha(Path(__file__).read_bytes()),'conditions':cs,
        'unique_conditions':216,'repeats_per_new_condition':3,'existing_cold_conditions':12,
        'base_new_readouts':612,'runtime_anchors':3,'extra_readouts_if_anchor_drift':36,
        'reuse_tolerance_probability_absolute':1e-4,
        'scope':'Four cyclic assignments and four cyclic orders, independently; no full factorial interaction or all 24 permutations.',
        'semantic_readout':'Unmarked definitions with fixed meaningful state words; each must tokenize as one token before any scored run.',
        'measurement':'Native pre-sampling probabilities; conditional on four exact response strings. Missing candidates trigger a logged larger top-k retry.'})
    (ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    for c in cs:
        d=ROOT/'prompts';d.mkdir(exist_ok=True);(d/(c['id']+'.txt')).write_text(c['system_prompt'])
    print('PREPARED',len(rows),'reviews',len(cs),'conditions',flush=True)
    return rows,cs,indexed

def run():
    rows,cs,old_rendered=prepare()
    api='http://127.0.0.1:11434'
    assert request(api,'/api/version')['version']=='0.40.17'
    tag=next(m for m in request(api,'/api/tags')['models'] if m['name']==MODEL)
    assert tag['digest']==pilot.MODELS[MODEL]
    load=request(api,'/api/generate',{'model':MODEL,'prompt':'','keep_alive':'30m',
        'options':{**pilot.OPTIONS,'num_predict':1}})
    processes=subprocess.check_output(['ps','-eo','args'],text=True).splitlines()
    line=next(l for l in processes if l.startswith('/usr/lib/ollama/llama-server ') and '--model ' in l)
    host='http://127.0.0.1:'+re.search(r'--port (\d+)',line).group(1)
    tokenization={}
    for label in list('ABCD1234')+list(WORDS.values()):
        tokenization[label]=request(host,'/tokenize',{'content':label,'add_special':False,'with_pieces':True})
    (ROOT/'tokenization.json').write_text(json.dumps(tokenization,indent=2))
    assert all(len(v['tokens'])==1 for v in tokenization.values()),'multi-token response: full-sequence scoring required'
    (ROOT/'runtime.json').write_text(json.dumps({'time':time.time(),'model':tag,'load':load,
        'backend_process':line,'props':request(host,'/props'),'show':request(api,'/api/show',{'model':MODEL}),
        'gpu':subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader'],text=True)},indent=2))
    rendered={}
    for r in rows:
        for c in cs:
            key=(r['case_id'],c['id'])
            if c['format']=='letters' and c['order']==0:
                rendered[key]=old_rendered[(r['case_id'],c['assignment'])]['response']['_debug_info']['rendered_template']
            else:
                req=pilot.payload(MODEL,r,'canonical');req['messages'][0]['content']=c['system_prompt'];req['_debug_render_only']=True
                rendered[key]=request(api,'/api/chat',req)['_debug_info']['rendered_template']
    (ROOT/'rendered_prompts.json').write_text(json.dumps([{'case_id':k[0],'condition':k[1],'prompt':v,'sha256':sha(v)} for k,v in rendered.items()]))
    old=[json.loads(l) for l in (ROOT/'previous_cold_readouts.jsonl').read_text().splitlines()]
    old_by={(cid,a):[r for r in old if r['case_id']==cid and r['rotation']==f'rotation_{a}'] for cid in ('K01','K06','U06') for a in range(4)}
    def score(cid,c,phase,repeat):
        req=completion_payload(rendered[(cid,c['id'])]);t=time.monotonic()
        rec={'case_id':cid,'condition':c['id'],'format':c['format'],'assignment':c['assignment'],
            'order':c['order'],'mapping':c['mapping'],'phase':phase,'repeat':repeat,
            'request':req,'request_sha256':sha(req),'started_at':time.time()}
        response=request(host,'/completion',req);m=measure(response,c['mapping'])
        if m.get('missing_states') or m.get('error'):
            rec['initial_top20_response']=response;rec['initial_top20_measurement']=m
            req={**req,'n_probs':200};response=request(host,'/completion',req);m=measure(response,c['mapping'])
            rec['expanded_topk_request']=req
        rec.update(response=response,measurement=m,elapsed_seconds=time.monotonic()-t)
        assert response.get('timings',{}).get('cache_n',0)==0,'cache unexpectedly reused'
        with (ROOT/'responses.jsonl').open('a') as f:
            f.write(json.dumps(rec,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
        return rec
    anchor=[]
    for cid in ('K01','K06','U06'):
        c=next(c for c in cs if c['id']=='letters_a0_o0');r=score(cid,c,'anchor',0)
        q=r['measurement']['conditional_probabilities'];prior=old_by[(cid,0)][0]['measurement']['normalized_state_probabilities']
        gap=max(abs(q[s]-prior[s]) for s in STATES) if q else 1.
        anchor.append({'case_id':cid,'max_probability_gap':gap})
    reuse=all(a['max_probability_gap']<=1e-4 for a in anchor)
    (ROOT/'reuse_decision.json').write_text(json.dumps({'reuse_old_cold_baselines':reuse,'anchors':anchor,
        'tolerance_absolute':1e-4,'qualification':'Engineering threshold for cross-runtime data reuse, not a semantic confidence tolerance.'},indent=2))
    reused=[]
    if reuse:
        for (cid,a),rs in old_by.items():
            for r in rs:reused.append({'case_id':cid,'condition':f'letters_a{a}_o0','format':'letters',
                'assignment':a,'order':0,'mapping':options('letters',a),'phase':'reused','repeat':r['repeat'],
                'measurement':measure(r['response'],options('letters',a)),'source':'previous_cold_readouts.jsonl',
                'source_request_sha256':r['request_sha256']})
    (ROOT/'reused_readouts.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in reused))
    tasks=[(r,c) for r in rows for c in cs if not (reuse and c['format']=='letters' and c['order']==0 and r['case_id'] in ('K01','K06','U06'))]
    rng=random.Random(20261124)
    for repeat in range(3):
        rng.shuffle(tasks)
        for r,c in tasks:score(r['case_id'],c,'main',repeat)
        print('FORMAT_BLOCK_DONE',repeat+1,'of 3','readouts',(repeat+1)*len(tasks),flush=True)
    request(api,'/api/generate',{'model':MODEL,'keep_alive':0})
    (ROOT/'COMPLETE.json').write_text(json.dumps({'time':time.time(),'new_readouts':3+3*len(tasks),
        'reused_readouts':len(reused),'reused_conditions':12 if reuse else 0}))
    print('FORMAT_RUN_COMPLETE',flush=True)

if __name__=='__main__':
    import sys
    if len(sys.argv)>1 and sys.argv[1]=='prepare':prepare()
    else:
        try:run()
        except BaseException as e:
            (ROOT/'FAILED.json').write_text(json.dumps({'time':time.time(),'error':repr(e)}));raise
