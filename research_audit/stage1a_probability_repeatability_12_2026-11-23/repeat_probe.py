#!/usr/bin/env python3
"""Repeated native readouts of frozen real reviews; no label adjudication."""
import argparse, hashlib, importlib.util, itertools, json, math, os, random, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PILOT = Path(os.environ.get('PILOT_ROOT', '/workspace/repo/research_audit/stage1a_calm_probability_12_2026-11-23'))
spec = importlib.util.spec_from_file_location('frozen_pilot', PILOT/'run_pilot.py')
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)
STATES = pilot.STATES
MAPS = {f'rotation_{i}': dict(zip(STATES, ('ABCD'*2)[i:i+4])) for i in range(4)}

def digest(x):
    if not isinstance(x, (bytes, str)):
        x = json.dumps(x, ensure_ascii=False, sort_keys=True)
    if isinstance(x, str): x = x.encode()
    return hashlib.sha256(x).hexdigest()

def call(path, body=None, timeout=240):
    return pilot.request('http://127.0.0.1:11434', path, body, timeout)

def payload(model, row, rotation):
    req = pilot.payload(model, row, 'canonical')
    req['messages'][0]['content'] = pilot.probe_prompt(MAPS[rotation])
    return req

def measure(response, mapping):
    out = pilot.probability_readout(response, mapping)
    if not out['valid']: return out
    assert out['decision_token_index'] == 0 and out['tokens_reconstruct_content']
    # Do not clip omitted probability mass against rounded 1-p values.
    known = out['native_state_probabilities']
    missing = out['missing_states']
    mass = sum(known.values())
    cap = out['topk_cutoff_probability']
    out['state_probability_intervals'] = {
        s: [known[s]/(mass+len(missing)*cap), known[s]/mass] if s in known
        else [0., cap/(mass+cap)] for s in STATES}
    e = response['logprobs'][0]
    codes = {a['token']: float(a['logprob']) for a in e['top_logprobs']}
    codes[e['token']] = float(e['logprob'])
    out['native_state_logprobs'] = {s: codes[c] for s,c in mapping.items() if c in codes}
    out['pairwise_logit_margins'] = {a+'__'+b: out['native_state_logprobs'][a]-out['native_state_logprobs'][b]
        for a,b in itertools.combinations(STATES,2) if a in out['native_state_logprobs'] and b in out['native_state_logprobs']}
    return out

def prepare():
    rows = pilot.inputs()
    old = json.loads((PILOT/'manifest.json').read_text())
    assert digest(rows) == old['cases_sha256']
    assert digest((PILOT/'run_pilot.py').read_bytes()) == old['runner_sha256']
    # First two mappings reproduce the original request bodies exactly.
    for row in rows:
        for rot, prior in [('rotation_0','canonical'),('rotation_1','rotated')]:
            assert payload('MODEL',row,rot) == pilot.payload('MODEL',row,prior)
            assert digest(payload('MODEL',row,rot)) == old['payload_hashes'][row['case_id']][prior]
    (ROOT/'prompts').mkdir(exist_ok=True)
    for name,mapping in MAPS.items(): (ROOT/'prompts'/f'{name}.txt').write_text(pilot.probe_prompt(mapping))
    manifest = {'protocol':'native_repeat_and_letter_mapping_v1', 'source_pilot_commit':'e58939fd1c67b67c802103cc081fd2d07bc1187e',
        'models':pilot.MODELS, 'cases_sha256':digest(rows), 'source_runner_sha256':old['runner_sha256'],
        'runner_sha256':digest(Path(__file__).read_bytes()), 'mappings':MAPS, 'options':pilot.OPTIONS,
        'main_repeats_per_mapping_case':10, 'reload_repeats_per_mapping_case':3,
        'expected_native_readouts':2*12*4*(10+3),
        'payload_hashes':{r['case_id']:{rot:digest(payload('MODEL',r,rot)) for rot in MAPS} for r in rows},
        'schedule':'interleaved mappings/cases within repeat blocks, random seed 20261123',
        'qualification':'development pilot; no new gold labels, calibration or model training'}
    dest = ROOT/'manifest.json'
    if dest.exists(): assert json.loads(dest.read_text()) == manifest, 'manifest drift'
    else: dest.write_text(json.dumps(manifest,indent=2))
    print('PREPARED',manifest['expected_native_readouts'],'native readouts',flush=True)
    return rows

def run(model):
    rows = prepare()
    assert call('/api/version')['version'] == '0.40.17'
    tag = next(x for x in call('/api/tags')['models'] if x['name']==model)
    assert tag['digest'] == pilot.MODELS[model], 'checkpoint drift'
    outdir = ROOT/'results'/model.replace(':','_')
    outdir.mkdir(parents=True,exist_ok=True)
    (outdir/'runtime.json').write_text(json.dumps({'version':call('/api/version'),'model':tag,
        'show':call('/api/show',{'model':model}), 'time':time.time()},indent=2))
    path = outdir/'responses.jsonl'
    old = [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []
    done = {(r['phase'],r['repeat'],r['case_id'],r['rotation']) for r in old}
    for phase,repeats in [('main',10),('reloaded',3)]:
        if all((phase,k,r['case_id'],m) in done for k in range(repeats) for r in rows for m in MAPS): continue
        # Unload before each phase. This is an intentional recorded reload, not
        # a claim that every subsequent request has a cold prompt cache.
        unloaded = call('/api/generate',{'model':model,'keep_alive':0})
        with (outdir/'phase_events.jsonl').open('a') as f:
            f.write(json.dumps({'phase':phase,'time':time.time(),'unload':unloaded})+'\n')
        rng = random.Random(20261123 + (1 if phase=='reloaded' else 0))
        for repeat in range(repeats):
            schedule = [(r,m) for r in rows for m in MAPS]
            rng.shuffle(schedule)
            for row,rot in schedule:
                key = phase,repeat,row['case_id'],rot
                if key in done: continue
                req = payload(model,row,rot)
                rec = {'phase':phase,'repeat':repeat,'case_id':row['case_id'],'rotation':rot,
                    'model':model,'request_sha256':digest(req),'request':req,'started_at':time.time()}
                start = time.monotonic()
                try:
                    resp = call('/api/chat',req)
                    rec.update(response=resp,measurement=measure(resp,MAPS[rot]))
                    assert rec['measurement']['valid'], rec['measurement']
                except Exception as exc:
                    rec['error'] = repr(exc)
                    with path.open('a') as f: f.write(json.dumps(rec,ensure_ascii=False)+'\n')
                    raise
                rec['elapsed_seconds'] = time.monotonic()-start
                with path.open('a') as f:
                    f.write(json.dumps(rec,ensure_ascii=False)+'\n'); f.flush(); os.fsync(f.fileno())
                done.add(key)
            print('BLOCK_DONE',model,phase,repeat+1,'of',repeats,'total',len(done),flush=True)
    # Capture the server's actual rendered input for the separate direct-logit
    # backend check. These are new debug calls, excluded from native readouts.
    rendered=[]
    for row in rows:
        for rot in MAPS:
            req = payload(model,row,rot);req['_debug_render_only']=True
            resp = call('/api/chat',req)
            assert resp.get('_debug_info',{}).get('rendered_template'),resp
            rendered.append({'case_id':row['case_id'],'rotation':rot,'request':req,'response':resp})
    (outdir/'rendered_prompts.json').write_text(json.dumps(rendered,ensure_ascii=False))
    call('/api/generate',{'model':model,'keep_alive':0})
    print('MODEL_DONE',model,len(done),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','run']);parser.add_argument('--model',choices=list(pilot.MODELS))
    args=parser.parse_args()
    if args.action=='prepare':prepare()
    else:run(args.model)
