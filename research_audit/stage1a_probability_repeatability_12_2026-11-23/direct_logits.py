#!/usr/bin/env python3
"""Separate llama.cpp Python backend check on the identical Gemma GGUF file."""
import argparse, ctypes, hashlib, json, math, os, platform, sys, tempfile, time
from pathlib import Path
import numpy as np

# The CUDA 13 wheel needs NVIDIA runtime libraries. Reuse Ollama's bundled
# NVIDIA libraries, keeping its separate ggml/llama binaries out of this path.
# The dynamic loader reads LD_LIBRARY_PATH at process startup, so re-exec once.
cuda_source=Path('/usr/lib/ollama/cuda_v13')
if cuda_source.exists() and os.environ.get('PROBE_CUDA_LOADER_READY')!='1':
    cuda_links=Path(tempfile.mkdtemp(prefix='probability_probe_cuda_'))
    for pattern in ('libcudart.so*','libcublas*.so*','libnvrtc*.so*'):
        for source in cuda_source.glob(pattern):
            target=cuda_links/source.name
            if not target.exists(): target.symlink_to(source)
    env={**os.environ,'PROBE_CUDA_LOADER_READY':'1',
        'LD_LIBRARY_PATH':str(cuda_links)+':'+os.environ.get('LD_LIBRARY_PATH','')}
    os.execvpe(sys.executable,[sys.executable,*sys.argv],env)

import llama_cpp
from llama_cpp import Llama

ROOT=Path(__file__).resolve().parent
STATES=('neither','support_only','opposition_only','both')
MAPS={f'rotation_{i}':dict(zip(STATES,('ABCD'*2)[i:i+4])) for i in range(4)}

def probs(z):
    z=np.asarray(z,dtype=np.float64); e=np.exp(z-z.max());return e/e.sum()

def run(model_path):
    manifest=json.loads((ROOT/'manifest.json').read_text())
    model='gemma4:31b-it-bf16'
    source=ROOT/'results'/model.replace(':','_')/'rendered_prompts.json'
    requests=json.loads(source.read_text())
    dest=ROOT/'direct_gemma';dest.mkdir(exist_ok=True)
    started=time.time()
    llm=Llama(model_path=model_path,n_ctx=8192,n_batch=512,n_ubatch=512,
        n_gpu_layers=-1,seed=42,logits_all=False,flash_attn=False,verbose=True)
    caps=[(k,v) for k,v in llm.metadata.items() if 'softcap' in k.lower()]
    cap=next((float(v) for k,v in caps if 'final_logit' in k or 'final_logit' in k.replace('.','_')),30.)
    metadata={'backend':'llama-cpp-python','version':llama_cpp.__version__,'model_path':model_path,
        'file_size':Path(model_path).stat().st_size,'gguf_metadata':llm.metadata,
        'settings':{'n_ctx':8192,'n_batch':512,'n_ubatch':512,'n_gpu_layers':-1,'flash_attn':False},
        'cuda_runtime_loader_path':os.environ.get('LD_LIBRARY_PATH'),
        'softcap_metadata':caps,'analytical_softcap_constant':cap,'start_time':started,
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'qualification':'Different inference binary from Ollama. Same GGUF; compare agreement explicitly. Pre-cap scores are analytic reconstructions, not internal hooks.'}
    (dest/'runtime.json').write_text(json.dumps(metadata,indent=2))
    codes={c:llm.tokenize(c.encode(),add_bos=False,special=False) for c in 'ABCD'}
    assert all(len(v)==1 for v in codes.values()),codes
    (dest/'code_tokens.json').write_text(json.dumps(codes))
    records=[]
    # Two identical full recomputations on four diagnostic cases. Other inputs
    # are evaluated once; this backend check is not the native repeat study.
    for item in requests:
        repeat_count=2 if item['case_id'] in ('K01','K06','U03','U06') else 1
        prompt=item['response']['_debug_info']['rendered_template']
        tokens=llm.tokenize(prompt.encode(),add_bos=False,special=True)
        if not tokens or tokens[0]!=llm.token_bos(): tokens=[llm.token_bos()]+tokens
        for repeat in range(repeat_count):
            llm.reset()
            llm._ctx.kv_cache_clear()
            start=time.monotonic();llm.eval(tokens)
            pointer=llm._ctx.get_logits_ith(-1)
            assert pointer
            z=np.ctypeslib.as_array(pointer,shape=(llm.n_vocab(),)).copy()
            assert np.isfinite(z).all()
            label_z=np.array([float(z[codes[MAPS[item['rotation']][s]][0]]) for s in STATES])
            q=probs(label_z)
            # Full-vocabulary native softmax for alignment, before any sampler.
            full_norm=float(np.max(z))+math.log(float(np.exp(z.astype(np.float64)-float(np.max(z))).sum()))
            native={s:math.exp(float(v)-full_norm) for s,v in zip(STATES,label_z)}
            valid=np.abs(label_z)<cap
            precap=np.full(4,np.nan)
            precap[valid]=cap*np.arctanh(label_z[valid]/cap)
            cap_roundtrip=np.full(4,np.nan)
            cap_roundtrip[valid]=cap*np.tanh(precap[valid]/cap)
            rec={'case_id':item['case_id'],'rotation':item['rotation'],'repeat':repeat,
                'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'token_count':len(tokens),
                'capped_logits':dict(zip(STATES,label_z.tolist())),'native_probabilities':native,
                'conditional_probabilities':dict(zip(STATES,q.tolist())),
                'selected_state':STATES[int(np.argmax(label_z))],
                'analytically_reconstructed_pre_cap':{s:float(v) if math.isfinite(v) else None for s,v in zip(STATES,precap)},
                'inverse_valid':dict(zip(STATES,valid.tolist())),
                'softcap_roundtrip_max_abs_error':float(np.max(np.abs(cap_roundtrip[valid]-label_z[valid]))) if valid.any() else None,
                'temperature_sensitivity':{str(t):dict(zip(STATES,probs(label_z/t).tolist())) for t in (1.,2.,4.,6.,8.)},
                'without_softcap_conditional':dict(zip(STATES,probs(precap).tolist())) if valid.all() else None,
                'elapsed_seconds':time.monotonic()-start}
            top=np.argsort(z)[-20:][::-1]
            saved={'code_capped_logits':label_z,'code_token_ids':np.array([codes[MAPS[item['rotation']][s]][0] for s in STATES]),
                'full_vocabulary_logsumexp':np.float64(full_norm),'top20_ids':top,'top20_capped_logits':z[top],
                'prompt_token_ids':np.asarray(tokens,dtype=np.int32)}
            if item['case_id'] in ('K01','K06','U06') and item['rotation']=='rotation_0' and repeat==0:
                saved['full_vocabulary_capped_logits']=z
            np.savez_compressed(dest/f"{item['case_id']}_{item['rotation']}_{repeat}.npz",**saved)
            with (dest/'readouts.jsonl').open('a') as f:f.write(json.dumps(rec,allow_nan=False)+'\n')
            records.append(rec)
        print('DIRECT_DONE',item['case_id'],item['rotation'],rec['selected_state'],flush=True)
    llm.close()
    print('DIRECT_COMPLETE',len(records),'readouts',time.time()-started,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model-path',required=True);a=p.parse_args();run(a.model_path)
