#!/usr/bin/env python3
"""Start the pinned Qwen backend on an owned transient GPU."""
import json,os,subprocess,sys,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ENV={**os.environ,'OLLAMA_HOST':'127.0.0.1:11434','OLLAMA_MODELS':'/workspace/ollama_models',
    'OLLAMA_NUM_PARALLEL':'1','OLLAMA_MAX_LOADED_MODELS':'1'}
def command(args):
    print('RUN',args,flush=True);return subprocess.run(args,check=True,env=ENV)
try:
    command(['apt-get','update']);command(['apt-get','install','-y','zstd'])
    archive='/workspace/ollama-v0.40.17.tar.zst'
    command(['curl','-fL','--retry','3','-o',archive,'https://github.com/ollama/ollama/releases/download/v0.40.17/ollama-linux-amd64.tar.zst'])
    command(['tar','--zstd','-xf',archive,'-C','/usr'])
    log=open(ROOT/'ollama.log','w')
    proc=subprocess.Popen(['/usr/bin/ollama','serve'],env=ENV,stdout=log,stderr=log,start_new_session=True)
    (ROOT/'server_pid.txt').write_text(str(proc.pid))
    for _ in range(60):
        try:
            with urllib.request.urlopen('http://127.0.0.1:11434/api/version') as r:assert json.load(r)['version']=='0.40.17'
            break
        except Exception:time.sleep(1)
    else:raise RuntimeError('server did not start')
    command(['/usr/bin/ollama','pull','qwen3.8:27b'])
    command([sys.executable,str(ROOT/'run_formats.py')])
except BaseException as e:
    (ROOT/'BOOTSTRAP_FAILED.json').write_text(json.dumps({'time':time.time(),'error':repr(e)}));raise
