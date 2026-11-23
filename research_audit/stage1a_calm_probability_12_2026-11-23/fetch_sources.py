#!/usr/bin/env python3
"""Recover frozen public source files for this experiment; never overwrite drift."""
import hashlib,json,urllib.request
from pathlib import Path
root=Path(__file__).resolve().parent
manifest=json.loads((root/'source_manifest.json').read_text())
for name,meta in manifest['files'].items():
    destination=root/name
    if destination.exists():
        assert hashlib.sha256(destination.read_bytes()).hexdigest()==meta['sha256'],name+' has local drift'
        print('VERIFIED',name)
        continue
    url='https://raw.githubusercontent.com/'+manifest['repository']+'/'+manifest['commit']+'/'+meta['repository_path']
    with urllib.request.urlopen(url,timeout=60) as response:content=response.read()
    assert hashlib.sha256(content).hexdigest()==meta['sha256'],name+' source hash mismatch'
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_bytes(content)
    print('FETCHED',name)
