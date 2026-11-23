#!/usr/bin/env python3
"""Freeze verified source bytes and archive this experiment, excluding weights."""
import hashlib, json, os, shutil, subprocess, tarfile, time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PILOT=Path(os.environ.get('PILOT_ROOT','/workspace/repo/research_audit/stage1a_calm_probability_12_2026-11-23'))

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def package():
    snapshot=ROOT/'frozen_source_snapshot';snapshot.mkdir(exist_ok=True)
    for name in ('run_pilot.py','manifest.json','source_manifest.json','fetch_sources.py'):
        shutil.copy2(PILOT/name,snapshot/name)
    shutil.copytree(PILOT/'source',snapshot/'source',dirs_exist_ok=True)
    frozen=json.loads((snapshot/'source_manifest.json').read_text())
    for name,meta in frozen['files'].items():assert digest(snapshot/name)==meta['sha256']
    manifest=json.loads((ROOT/'manifest.json').read_text())
    assert digest(snapshot/'run_pilot.py')==manifest['source_runner_sha256']
    assert digest(ROOT/'repeat_probe.py')==manifest['runner_sha256']
    for name in ('qwen3.8_27b','gemma4_31b-it-bf16'):
        rows=[json.loads(l) for l in (ROOT/'results'/name/'responses.jsonl').read_text().splitlines()]
        assert len(rows)==624 and all(not r.get('error') and r['measurement']['valid'] for r in rows)
    direct=ROOT/'direct_gemma/readouts.jsonl'
    assert direct.exists() and len(direct.read_text().splitlines())==64
    binaries={}
    for s in ['/usr/bin/ollama','/usr/lib/ollama/llama-server',
            '/usr/local/lib/python3.12/dist-packages/llama_cpp/lib/libllama.so']:
        path=Path(s)
        if path.exists():binaries[s]={'bytes':path.stat().st_size,'sha256':digest(path)}
    (ROOT/'binary_provenance.json').write_text(json.dumps({'time':time.time(),'binaries':binaries,
        'python_version':subprocess.check_output(['python','--version'],text=True).strip()},indent=2))
    excluded={'__pycache__','code_bundle.b64','code_bundle.tar.gz','raw_results_bundle.tar.gz','raw_results_bundle.tar.gz.part','BUNDLE.json','INTEGRITY.json'}
    files=[p for p in ROOT.rglob('*') if p.is_file() and not p.is_symlink()
        and not any(part in excluded for part in p.relative_to(ROOT).parts) and p.suffix!='.pyc']
    integrity={str(p.relative_to(ROOT)):{'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(files)}
    (ROOT/'INTEGRITY.json').write_text(json.dumps(integrity,indent=2))
    files.append(ROOT/'INTEGRITY.json')
    dest=ROOT/'raw_results_bundle.tar.gz'
    with tarfile.open(str(dest)+'.part','w:gz',compresslevel=6) as tf:
        for path in sorted(files):tf.add(path,arcname=str(path.relative_to(ROOT)),recursive=False)
    Path(str(dest)+'.part').replace(dest)
    result={'path':str(dest),'bytes':dest.stat().st_size,'sha256':digest(dest),'files':len(files),'time':time.time()}
    (ROOT/'BUNDLE.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))

if __name__=='__main__':package()
