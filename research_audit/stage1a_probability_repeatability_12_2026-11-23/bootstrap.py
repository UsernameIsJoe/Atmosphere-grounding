#!/usr/bin/env python3
"""Provision owned transient compute; all source reviews fetched from public git."""
import hashlib, json, os, shutil, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT=Path('/workspace/probability_repeat_2026_11_23')
PILOT=Path('/workspace/repo/research_audit/stage1a_calm_probability_12_2026-11-23')
ENV={**os.environ,'OLLAMA_HOST':'127.0.0.1:11434','OLLAMA_MODELS':'/workspace/ollama_models',
    'OLLAMA_NUM_PARALLEL':'1','OLLAMA_MAX_LOADED_MODELS':'1','PILOT_ROOT':str(PILOT)}

def run(argv,**kw):
    print('RUN',argv,flush=True);return subprocess.run(argv,check=True,env=ENV,**kw)

def api(path,body=None):
    data=None if body is None else json.dumps(body).encode()
    req=urllib.request.Request('http://127.0.0.1:11434'+path,data=data,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=900) as r:
        raw=r.read()
        return json.loads(raw) if raw else {}

def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    if not shutil.which('zstd'):
        run(['apt-get','update']);run(['apt-get','install','-y','zstd'])
    if not Path('/workspace/repo/.git').exists():
        run(['git','clone','--depth','1','https://github.com/UsernameIsJoe/Atmosphere-grounding.git','/workspace/repo'])
    # The archived target-script source was frozen without its final newline.
    # Recover only that exact byte representation; never accept an arbitrary
    # source change. Every recovered file must match the original SHA256.
    source_manifest=json.loads((PILOT/'source_manifest.json').read_text())
    recovery=[]
    for name,meta in source_manifest['files'].items():
        dest=PILOT/name
        if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest()==meta['sha256']: continue
        url='https://raw.githubusercontent.com/'+source_manifest['repository']+'/'+source_manifest['commit']+'/'+meta['repository_path']
        with urllib.request.urlopen(url,timeout=60) as response: data=response.read()
        original_sha=hashlib.sha256(data).hexdigest()
        if original_sha!=meta['sha256'] and name=='source/target_script.py' and data.endswith(b'\n'):
            assert hashlib.sha256(data[:-1]).hexdigest()==meta['sha256'],'not the known final-newline mismatch'
            data=data[:-1]
            recovery.append({'path':name,'raw_sha256':original_sha,'recovered_sha256':meta['sha256'],'operation':'remove exactly one terminal newline to match frozen source bytes'})
        assert hashlib.sha256(data).hexdigest()==meta['sha256'],name+' source drift'
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    (ROOT/'source_recovery.json').write_text(json.dumps(recovery,indent=2))
    run([sys.executable,str(PILOT/'fetch_sources.py')])
    archive=Path('/workspace/ollama-linux-amd64-v0.40.17.tar.zst')
    run(['curl','-fL','--retry','3','-o',str(archive),'https://github.com/ollama/ollama/releases/download/v0.40.17/ollama-linux-amd64.tar.zst'])
    run(['tar','--zstd','-xf',str(archive),'-C','/usr'])
    log=(ROOT/'ollama.log').open('w')
    proc=subprocess.Popen(['/usr/bin/ollama','serve'],env=ENV,stdout=log,stderr=log,start_new_session=True)
    (ROOT/'server_pid.txt').write_text(str(proc.pid))
    for _ in range(60):
        try:
            assert api('/api/version')['version']=='0.40.17';break
        except Exception: time.sleep(1)
    else:raise RuntimeError('Ollama did not start')
    for name in ('qwen3.8:27b','dhiltgen/gemma4:31b-it-bf16-llamacpp'):
        run(['/usr/bin/ollama','pull',name])
    api('/api/copy',{'source':'dhiltgen/gemma4:31b-it-bf16-llamacpp','destination':'gemma4:31b-it-bf16'})
    hardware=run(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader'],capture_output=True,text=True).stdout
    (ROOT/'hardware.json').write_text(json.dumps({'gpu':hardware,'time':time.time(),'env':{k:ENV[k] for k in ENV if k.startswith('OLLAMA_')},'tags':api('/api/tags')},indent=2))
    run([sys.executable,str(ROOT/'repeat_probe.py'),'prepare'])
    # Install a binary wheel while native inference runs. This does not modify
    # Ollama or the native model files. Installation output is separate.
    install=(ROOT/'llama_python_install.log').open('w')
    wheel=subprocess.Popen([sys.executable,'-m','pip','install','--only-binary=llama-cpp-python',
        '--extra-index-url','https://abetlen.github.io/llama-cpp-python/whl/cu132','llama-cpp-python==0.3.25'],stdout=install,stderr=install,env=ENV)
    for model in ('qwen3.8:27b','gemma4:31b-it-bf16'):
        run([sys.executable,str(ROOT/'repeat_probe.py'),'run','--model',model])
    rc=wheel.wait(timeout=300)
    (ROOT/'wheel_install_status.json').write_text(json.dumps({'exit_code':rc}))
    if rc==0:
        manifest=Path('/workspace/ollama_models/manifests/registry.ollama.ai/dhiltgen/gemma4/31b-it-bf16-llamacpp')
        data=json.loads(manifest.read_text())
        layer=next(x for x in data['layers'] if x['mediaType']=='application/vnd.ollama.image.model')
        model_path=Path('/workspace/ollama_models/blobs')/layer['digest'].replace(':','-')
        run([sys.executable,str(ROOT/'direct_logits.py'),'--model-path',str(model_path)])
    else:
        print('DIRECT_BACKEND_INSTALL_FAILED',rc,flush=True)
    (ROOT/'COMPLETE.json').write_text(json.dumps({'complete_time':time.time(),'native_completed':True,'direct_install_code':rc}))

if __name__=='__main__':
    try: main()
    except BaseException as e:
        (ROOT/'FAILED.json').write_text(json.dumps({'error':repr(e),'time':time.time()}))
        raise
