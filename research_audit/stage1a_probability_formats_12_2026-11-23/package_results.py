#!/usr/bin/env python3
"""Stop the completed private server and preserve experiment artifacts."""
import hashlib,json,os,signal,tarfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def package():
    complete=json.loads((ROOT/'COMPLETE.json').read_text())
    assert complete['new_readouts'] in (615,651)
    pid=int((ROOT/'server_pid.txt').read_text());cmd=Path('/proc')/str(pid)/'cmdline'
    if cmd.exists():
        args=cmd.read_bytes();assert b'ollama' in args and b'serve' in args
        os.kill(pid,signal.SIGTERM);time.sleep(1)
    (ROOT/'service_stop.json').write_text(json.dumps({'time':time.time(),'pid':pid,'after_completed_scoring':True}))
    exclude={'upload_bundle.tar.gz','raw_results_bundle.tar.gz','raw_results_bundle.tar.gz.part','INTEGRITY.json','BUNDLE.json','__pycache__'}
    files=[p for p in ROOT.rglob('*') if p.is_file() and not any(x in exclude for x in p.relative_to(ROOT).parts) and p.suffix!='.pyc']
    (ROOT/'INTEGRITY.json').write_text(json.dumps({str(p.relative_to(ROOT)):{'sha256':digest(p),'bytes':p.stat().st_size} for p in sorted(files)},indent=2))
    files.append(ROOT/'INTEGRITY.json');dest=ROOT/'raw_results_bundle.tar.gz'
    with tarfile.open(str(dest)+'.part','w:gz',compresslevel=6) as tf:
        for p in sorted(files):tf.add(p,arcname=str(p.relative_to(ROOT)),recursive=False)
    Path(str(dest)+'.part').replace(dest)
    result={'bytes':dest.stat().st_size,'sha256':digest(dest),'files':len(files),'time':time.time()}
    (ROOT/'BUNDLE.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
if __name__=='__main__':package()
