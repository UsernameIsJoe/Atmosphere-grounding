#!/usr/bin/env python3
"""Download versioned GitHub Actions ABSA experiment artifacts locally.

Requires GitHub CLI (gh), authenticated if needed. Refuses to overwrite prior
artifacts unless --overwrite. Never commits raw review text automatically.
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys
ROOT=pathlib.Path(__file__).resolve().parent
REPO="UsernameIsJoe/Atmosphere-grounding"
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--id",action="append",dest="ids",help="One experiment ID; repeat for multiple; omit for all Actions artifacts")
    p.add_argument("--output",type=pathlib.Path,default=pathlib.Path("reports/stage1a_archive"))
    p.add_argument("--list",action="store_true",help="Show tracked experimental code, workflows, and artifact locations")
    p.add_argument("--overwrite",action="store_true")
    args=p.parse_args()
    m=json.loads((ROOT/"manifest.json").read_text(encoding="utf8"))
    experiments=m["experiments"]
    if args.list:
        for e in experiments:
            print(f"{e['id']}: {e['name']}")
            for s in e["files"]:print(f"  code: {s}")
            if e["workflow"]:print(f"  workflow: {e['workflow']}")
            print(f"  run: {e['run_id'] or 'LOCAL'}; artifact: {e['artifact'] or 'NONE'}")
        return
    if shutil.which("gh") is None:
        p.error("Missing GitHub CLI. Install from https://cli.github.com/ and use gh auth login if required.")
    wanted=set(args.ids or [])
    known={e["id"] for e in experiments}
    unknown=wanted-known
    if unknown:p.error("Unknown experiment IDs: "+", ".join(sorted(unknown)))
    selected=[e for e in experiments if e["id"] in wanted] if wanted else [
        e for e in experiments if e["run_id"] and e["artifact"]]
    if any(not e["run_id"] or not e["artifact"] for e in selected):
        p.error("Selected experiment has no Actions artifact (local experiment or code-only workflow).")
    errors=[]
    for e in selected:
        out=args.output/e["id"]
        if out.exists() and any(out.iterdir()) and not args.overwrite:
            print("SKIP existing:",out,"(pass --overwrite to re-download)")
            continue
        if args.overwrite and out.exists():shutil.rmtree(out)
        out.mkdir(parents=True,exist_ok=True)
        command=["gh","run","download",str(e["run_id"]),"-R",REPO,
                 "-n",e["artifact"],"-D",str(out)]
        print("Downloading",e["id"],"from Actions run",e["run_id"],flush=True)
        process=subprocess.run(command,check=False)
        if process.returncode:
            errors.append(e["id"])
            print("FAILED (artifact may have expired or name may differ):",e["id"],file=sys.stderr)
    if errors:
        print("Unavailable artifacts:",", ".join(errors),file=sys.stderr)
        raise SystemExit(1)
if __name__=="__main__":main()
