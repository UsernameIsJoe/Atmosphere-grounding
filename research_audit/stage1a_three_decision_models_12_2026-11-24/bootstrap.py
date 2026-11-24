#!/usr/bin/env python3
"""Bounded native-runtime installation, checkpoint verification and three-model diagnostic."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parent
os.environ.update({'HF_HOME':'/workspace/hf_cache','HF_HUB_DISABLE_XET':'1','HF_HUB_DISABLE_TELEMETRY':'1',
                   'TOKENIZERS_PARALLELISM':'false','PYTHONUNBUFFERED':'1','MAX_JOBS':'8'})
PROTOCOL=json.loads((ROOT/'PROTOCOL.json').read_text())


def status(stage,**extra):
    (ROOT/'bootstrap_status.json').write_text(json.dumps({'stage':stage,'time':time.time(),**extra},indent=2)+'\n')
    print('STAGE',stage,extra,flush=True)


def command(args, logname, timeout=1200, env=None):
    with (ROOT/logname).open('a') as f:
        r=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,timeout=timeout,env=env)
    if r.returncode:raise RuntimeError(logname+' failed: '+str(r.returncode))


def download(name):
    from huggingface_hub import snapshot_download,HfApi
    info=PROTOCOL['models'][name];dest=Path('/workspace/checkpoints')/name
    print('DOWNLOAD',name,info,flush=True)
    snapshot_download(info['repo'],revision=info['revision'],local_dir=dest,max_workers=8,
                      ignore_patterns=['assets/*','.gitattributes'])
    meta=HfApi().model_info(info['repo'],revision=info['revision'],files_metadata=True)
    verified={}
    for sibling in meta.siblings:
        file=dest/sibling.rfilename
        if not file.is_file() or not file.name.endswith('.safetensors'):continue
        h=hashlib.sha256()
        with file.open('rb') as f:
            for block in iter(lambda:f.read(16*1024*1024),b''):h.update(block)
        expected=getattr(sibling.lfs,'sha256',None) if sibling.lfs else None
        if expected and expected!=h.hexdigest():raise ValueError('Weight checksum mismatch: '+str(file))
        verified[sibling.rfilename]={'bytes':file.stat().st_size,'sha256':h.hexdigest(),'expected_lfs_sha256':expected}
    for entry in json.loads((ROOT/'source_download_manifest.json').read_text()):
        if entry['model']!=name or 'error' in entry:continue
        file=dest/entry['file']
        if hashlib.sha256(file.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('Frozen source drift: '+str(file))
    out=ROOT/'results'/name;out.mkdir(parents=True,exist_ok=True)
    (out/'checkpoint_integrity.json').write_text(json.dumps(verified,indent=2)+'\n')
    print('DOWNLOAD_VERIFIED',name,len(verified),flush=True)
    return str(dest)


def install_common():
    command([sys.executable,'-m','pip','install','--no-cache-dir','--disable-pip-version-check','-r',
             str(ROOT/'frozen_source/glide/requirements.txt'),'torchvision==0.29.0','accelerate','pybase64','backports.zstd'],
             'install_common.log',timeout=1200)
    command([sys.executable,'-m','pip','install','--no-deps','-e',str(ROOT/'runtime_source/karpo')],
             'install_common.log',timeout=180)
    return sys.executable


def install_mammoth():
    dest=Path('/workspace/mammoth_env')
    command([sys.executable,'-m','venv',str(dest)],'install_mammoth.log',timeout=60)
    python=str(dest/'bin/python');constraints=str(ROOT/'frozen_source/mammoth/constraints.txt')
    command([python,'-m','pip','install','--no-cache-dir','torch==2.8.0','torchvision==0.23.0',
             '--index-url','https://download.pytorch.org/whl/cu128'],'install_mammoth.log',timeout=1200)
    pins=ROOT/'mammoth_torch_constraints.txt';pins.write_text('torch==2.8.0\ntorchvision==0.23.0\n')
    command([python,'-m','pip','install','--no-cache-dir','-c',constraints,'-c',str(pins),
             '-e',str(ROOT/'runtime_source/onejev')+'[torch]','flash-linear-attention','huggingface_hub','brotli'],
             'install_mammoth.log',timeout=1200)
    # The published setup installs this optional accelerator separately. Preserve
    # the native supported fallback if its bounded build fails, and record it.
    try:
        command([python,'-m','pip','install','--no-cache-dir','-c',constraints,'-c',str(pins),
                 '--no-build-isolation','causal-conv1d'],'install_mammoth.log',timeout=240)
    except Exception as e:
        (ROOT/'mammoth_optional_accelerator.json').write_text(json.dumps({'causal_conv1d_install_error':repr(e),
                'note':'Optional accelerator did not install within its bounded build; native Transformers fallback is retained.'},indent=2)+'\n')
    return python


def main():
    status('installing_downloading',python=sys.version)
    # A separate download dependency tree prevents parallel inference-stack pip
    # installs from changing the hub client while checkpoint transfers are live.
    downloader=Path('/workspace/hf_downloader')
    subprocess.run([sys.executable,'-m','pip','install','--quiet','--target',str(downloader),
                    'huggingface_hub==1.33.0'],check=True)
    sys.path.insert(0,str(downloader))
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        downloads={n:pool.submit(download,n) for n in ['mammoth','karpo','glide']}
        common=pool.submit(install_common);mammoth=pool.submit(install_mammoth)
        outcomes={}
        for name in ['karpo','glide','mammoth']:
            try:
                deadline=json.loads((ROOT/'LEASE.json').read_text())['inference_deadline_epoch']
                remaining=max(1,deadline-time.time())
                python=(mammoth if name=='mammoth' else common).result(timeout=remaining)
                downloads[name].result(timeout=max(1,deadline-time.time()))
                if time.time()>deadline:raise TimeoutError('Global inference deadline reached')
                status('running_model',model=name,previous_outcomes=outcomes)
                command([python,'-u',str(ROOT/'run_model.py'),name],name+'_run.log',timeout=max(1,deadline-time.time()))
                outcomes[name]='complete'
            except Exception as e:
                outcomes[name]={'error':repr(e)}
                (ROOT/(name+'_BOOTSTRAP_FAILED.json')).write_text(json.dumps({'time':time.time(),'error':repr(e),
                     'traceback':traceback.format_exc()},indent=2)+'\n')
                print('MODEL_FAILURE',name,repr(e),flush=True)
        status('finished',outcomes=outcomes)
        (ROOT/'ALL_MODELS_FINISHED.json').write_text(json.dumps({'time':time.time(),'outcomes':outcomes},indent=2)+'\n')


if __name__=='__main__':
    try:main()
    except BaseException as e:
        status('failed',error=repr(e));traceback.print_exc();raise
