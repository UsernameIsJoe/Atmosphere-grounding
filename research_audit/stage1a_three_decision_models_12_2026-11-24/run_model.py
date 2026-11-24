#!/usr/bin/env python3
"""Native four-state calm decisions, with same-forward score capture and frozen inputs."""
import dataclasses
import gc
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parent
NAME = sys.argv[1]
OUT = ROOT / 'results' / NAME
OUT.mkdir(parents=True, exist_ok=True)
CHECKPOINT = Path('/workspace/checkpoints') / NAME
STATES = ('neither', 'support_only', 'opposition_only', 'both')


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n')


def append(name, value):
    with (OUT / name).open('a') as f:
        f.write(json.dumps(value, ensure_ascii=False, separators=(',', ':'), default=str) + '\n')


def check_deadline():
    deadline = json.loads((ROOT / 'LEASE.json').read_text())['inference_deadline_epoch']
    if time.time() > deadline:
        raise TimeoutError('Global inference budget reached; retain all existing readouts')


class Native:
    def __init__(self):
        import torch
        self.raw = None
        self.calls = 0
        self.handle = None
        if NAME == 'mammoth':
            sys.path.insert(0, str(ROOT / 'runtime_source/onejev'))
            from qev.engine import DecisionEngine
            self.engine = DecisionEngine(str(CHECKPOINT), device='cuda:0', fork_mode='sequential',
                                         max_branch_tokens=16384, max_request_tokens=16384)
            self.temperature = self.engine.calibration.temperature('choice', 4)
            self.info = dataclasses.asdict(self.engine.info)
            self.core = self.engine.model
        elif NAME == 'karpo':
            sys.path.insert(0, str(ROOT / 'runtime_source/karpo/src'))
            from karpo_decision.decider import Decider
            self.engine = Decider.from_pretrained(CHECKPOINT, device='cuda', max_length=8192, token_budget=8192)
            self.temperature = self.engine.config.temperatures['choice']
            original = self.engine.logits
            def capture(sequences):
                values = original(sequences)
                assert len(values) == 1 and len(values[0]) == 1
                self.raw = values[0][0].tolist()
                return values
            self.engine.logits = capture
            self.info = {'attention': self.engine.config.attention, 'template': self.engine.config.template,
                         'readout_dtype': self.engine.config.readout_dtype, 'max_length': self.engine.max_length}
            self.core = self.engine.model
        elif NAME == 'glide':
            sys.path.insert(0, str(CHECKPOINT))
            from glide import Glide
            self.engine = Glide.from_pretrained(str(CHECKPOINT), device='cuda', max_len=8192, token_budget=8192)
            self.temperature = self.engine.temperature
            original = self.engine._logits
            def capture(sequences, vis):
                values = original(sequences, vis)
                assert len(values) == 1
                self.raw = values[0][:4]
                return values
            self.engine._logits = capture
            self.info = {'attention': self.engine.config.get('attention_mode'), 'midloop': self.engine.config.get('midloop'),
                         'vision': self.engine.vision, 'max_length': self.engine.max_len}
            self.core = self.engine.network
        else:
            raise ValueError(NAME)
        self.handle = self.core.register_forward_hook(self.count_call)

    def count_call(self, module, args, output):
        self.calls += 1

    def rendered(self, req):
        if NAME == 'mammoth':
            from qev.schema import SystemOneRequest
            from qev.prompt import render_question
            native = SystemOneRequest(**req)
            r = render_question('calm', native.questions['calm'], style=self.engine.style)
            text = self.engine._render_prompt(native.state, r.suffix)
            ids = self.engine._encode(text)
            return {'text': text, 'input_token_ids': ids, 'input_tokens': len(ids)}
        if NAME == 'karpo':
            plan = self.engine.plan(req)
            assert len(plan) == 1 and len(plan[0].keys) == 1
            p = plan[0]
            return {'decoded_tokens': self.engine.ckpt.processor.tokenizer.decode(p.input_ids.tolist(), skip_special_tokens=False),
                    'input_token_ids': p.input_ids.tolist(), 'input_tokens': p.length, 'markers': p.markers.tolist()}
        entries, vis = self.engine._prepare(req)
        assert len(entries) == 1 and vis is None
        text = entries[0][3]
        ids = self.engine.tokenizer(text, add_special_tokens=False)['input_ids']
        return {'text': text, 'input_token_ids': ids, 'input_tokens': len(ids)}

    def decide(self, req):
        import torch
        self.raw = None
        before = self.calls
        if NAME == 'mammoth':
            from qev.schema import SystemOneRequest
            response, meta = self.engine.decide(SystemOneRequest(**req), debias=1, debug=True)
            response = response.model_dump()
            diag = meta['diagnostics']['calm']
            assert len(diag['slot_logits']) == 1
            self.raw = diag['slot_logits'][0]
            assert diag['temperature'] == self.temperature
        else:
            response = self.engine.decide(req) if NAME == 'karpo' else self.engine.decide(req['state'], req['questions'])
            meta = {}
        answer = response['answers']['calm']
        p = answer['probabilities']
        keys = list(req['questions']['calm']['criteria'])
        assert self.raw is not None and len(self.raw) == 4
        if NAME == 'karpo':
            expected = (torch.tensor(self.raw, dtype=torch.float32) / self.temperature).softmax(-1).tolist()
        elif NAME == 'glide':
            from glide.model import _softmax
            expected = _softmax(self.raw, 4, self.temperature)
        else:
            from qev.calibrate import softmax
            expected = softmax(self.raw, self.temperature)
        reconstructed = dict(zip(keys, expected))
        delta = max(abs(reconstructed[k] - p[k]) for k in keys)
        assert delta < 3e-7, ('native_probability_mismatch', delta)
        assert set(p) == set(STATES) and abs(sum(p.values()) - 1) < 2e-7
        assert all(math.isfinite(x) and x >= 0 for x in p.values())
        return {'raw_logits': dict(zip(keys, self.raw)), 'probabilities': p,
                'selected_state': answer['choice'], 'native_answer': answer, 'usage': response.get('usage'),
                'native_temperature': self.temperature, 'native_reconstruction_max_abs_error': delta,
                'model_forward_passes': self.calls - before, 'native_diagnostics': meta}


def main():
    import numpy as np
    import torch
    random.seed(42); np.random.seed(42); torch.manual_seed(42); torch.cuda.manual_seed_all(42)
    torch.set_num_threads(4)
    requests = [json.loads(l) for l in (ROOT / 'requests.jsonl').read_text().splitlines()]
    assert len(requests) == 144
    check_deadline()
    t0 = time.monotonic(); model = Native(); torch.cuda.synchronize()
    runtime = {'model': NAME, 'model_source': json.loads((ROOT/'PROTOCOL.json').read_text())['models'][NAME],
               'seed': 42, 'torch': torch.__version__, 'cuda_runtime': torch.version.cuda,
               'gpu': subprocess.check_output(['nvidia-smi','--query-gpu=name,driver_version,memory.total','--format=csv,noheader'],text=True).strip(),
               'packages': {k: importlib.metadata.version(k) for k in ['torch','transformers','safetensors','huggingface-hub','numpy']},
               'load_seconds': time.monotonic()-t0,'native_temperature':model.temperature,'native_info':model.info,
               'deterministic_algorithms':torch.are_deterministic_algorithms_enabled(), 'serial_requests': True,
               'cache_note':'Mammoth retains native within-request prefix computation and fresh cache per request; no cross-request prefix reuse. Karpo/GLiDE use full native reference forwards.'}
    write('runtime.json',runtime)
    rendered=[]
    for r in requests:
        e=model.rendered(r['request'])
        assert 0 < e['input_tokens'] < (16384 if NAME=='mammoth' else 8192)
        rendered.append({'case_id':r['case_id'],'order_id':r['order_id'],'wording_id':r['wording_id'],
                         'request_sha256':r['request_sha256'],**e})
    write('rendered_requests.json',rendered)
    runtime['min_input_tokens']=min(r['input_tokens'] for r in rendered)
    runtime['max_input_tokens']=max(r['input_tokens'] for r in rendered)
    write('runtime.json',runtime)
    print('MODEL_LOADED',NAME,runtime['load_seconds'],runtime['min_input_tokens'],runtime['max_input_tokens'],flush=True)
    count=0
    def evaluate(item,phase,rep):
        nonlocal count
        check_deadline(); t0=time.monotonic()
        result=model.decide(item['request']);torch.cuda.synchronize()
        result.update({'model':NAME,'phase':phase,'repeat':rep,'case_id':item['case_id'],'order_id':item['order_id'],
                       'wording_id':item['wording_id'],'state_order':item['state_order'],'request_sha256':item['request_sha256'],
                       'elapsed_seconds':time.monotonic()-t0})
        append('readouts.jsonl',result);count+=1
        if count%12==0:print('READOUT',NAME,count,phase,item['case_id'],result['selected_state'],round(max(result['probabilities'].values()),6),flush=True)
    base=[r for r in requests if r['wording_id']=='wording_0']
    extra=[r for r in requests if r['wording_id']!='wording_0']
    for phase,subset,repeats in [('main',base,10),('paraphrase',extra,3)]:
        for rep in range(repeats):
            order=list(subset);random.Random(20261124+rep+(1000 if phase=='paraphrase' else 0)).shuffle(order)
            for item in order:evaluate(item,phase,rep)
            write('progress.json',{'model':NAME,'phase':phase,'readouts':count,'blocks':rep+1,'time':time.time()})
    model.handle.remove();del model;gc.collect();torch.cuda.empty_cache();torch.cuda.synchronize()
    check_deadline();t0=time.monotonic();model=Native();torch.cuda.synchronize()
    runtime['reload_seconds']=time.monotonic()-t0
    for item in base:
        if item['order_id']=='order_0':evaluate(item,'reloaded',0)
    runtime['end_time']=time.time();runtime['peak_gpu_memory_bytes']=torch.cuda.max_memory_allocated()
    write('runtime.json',runtime)
    write('RUN_COMPLETE.json',{'model':NAME,'total_readouts':count,'expected':780,'time':time.time()})
    print('COMPLETE',NAME,count,flush=True)


if __name__=='__main__':
    try:main()
    except BaseException as e:
        write('RUN_FAILED.json',{'model':NAME,'time':time.time(),'error':repr(e),'traceback':traceback.format_exc()})
        traceback.print_exc();raise
