#!/usr/bin/env python3
"""Component 1 revision: parallel inference, source-grounded, non-generative reconciliation.

Input: frozen full-original-sentence GTS ASTE, GLiNER JointIE and independent
GLiNER predictions. Output: evidence units with source spans, overlap
provenance, unresolved contradictions, and ORIGINAL verbatim context.

No keyword-to-emotion mapping, no relevance selection, and no NLI.
"""
import collections
import json
import pathlib
import re
ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE=ROOT/"reports/component1_reconcile_inputs"
OUT=ROOT/"reports/component1_reconciled"

def read_one(folder,name):
    files=list((BASE/folder).rglob(name))
    if len(files)!=1:raise ValueError(f"Expected one {folder}/{name}: {files}")
    return [json.loads(s) for s in files[0].read_text().splitlines() if s.strip()]

def exact(text,span):
    a,b=span.get("start"),span.get("end")
    return isinstance(a,int) and isinstance(b,int) and 0<=a<b<=len(text) and text[a:b]==span.get("text")

def anchored(text,phrase):
    if not isinstance(phrase,str) or not phrase.strip():return {"text":phrase,"status":"missing"}
    matches=list(re.finditer(re.escape(phrase.strip()),text,re.I))
    if len(matches)==1:
        m=matches[0]
        return {"text":text[m.start():m.end()],"start":m.start(),"end":m.end(),"status":"unique"}
    return {"text":phrase,"status":"missing" if not matches else "ambiguous","occurrences":len(matches)}

def overlap(a,b):
    if not all(isinstance(x.get(k),int) for x in (a,b) for k in ("start","end")):return False
    return min(a["end"],b["end"])>max(a["start"],b["start"])

def make_joint(sentence,p):
    graph=p.get("graph",{})
    entities={}
    for x in graph.get("entities",[]):
        y={"text":x["text"],"start":x["start"],"end":x["end"],"type":x["type"],
           "confidence":x.get("confidence"),"source":"gliner_joint"}
        if not exact(sentence,y):raise ValueError("Joint output ungrounded")
        if x["id"] in entities:raise ValueError("duplicate entity IDs")
        entities[x["id"]]=y
    links=[]
    for r in graph.get("relations",[]):
        a=entities.get(r["head"]);b=entities.get(r["tail"])
        if a is None or b is None:raise ValueError("Unresolved JointIE edge")
        links.append({"id":"joint_"+str(len(links)),"kind":r["type"],
            "head":a,"tail":b,"sources":["gliner_joint"],
            "score":r.get("confidence"),"polarity":None,
            "status":"candidate_typed_graph","gts_corrob":[],
            "spans_original":True})
    return entities,links

def reconcile(original,joint,ind,gts):
    text=original["sentence"]
    assert joint["text"]==text
    s=gts["sentence"]
    assert s["text"]==text
    entities,links=make_joint(text,joint)
    # Prior matched audit stores each independent relation as a flat list.
    independents=[]
    for r in ind.get("relations",[]):
        a,b=anchored(text,r["aspect"]),anchored(text,r["opinion"])
        independents.append({"kind":r.get("type"),"head":a,"tail":b,
                             "source_exact":r.get("source_exact",False)})
    used_gts=set()
    gts_pairs=[]
    for i,r in enumerate(s["extraction"]["relations"]):
        a=r["aspect"];b=r["opinion"]
        # GTS's existing record uses original-review offsets. Rebase deliberately.
        lo=original["start"]
        if not (isinstance(a.get("start"),int) and isinstance(b.get("start"),int)
            and original["review"][a["start"]:a["end"]]==a["text"]
            and original["review"][b["start"]:b["end"]]==b["text"]
            and lo<=a["start"]<a["end"]<=original["end"]
            and lo<=b["start"]<b["end"]<=original["end"]):
            gts_pairs.append({"id":i,"status":"unresolved_source","raw":r});continue
        a_local={**a,"start":a["start"]-lo,"end":a["end"]-lo}
        b_local={**b,"start":b["start"]-lo,"end":b["end"]-lo}
        gts_pairs.append({"id":i,"aspect":a_local,"opinion":b_local,
             "polarity":r.get("polarity"),"status":"source_exact"})
    # A GTS link corroborates only an aligned *description* link with
    # overlapping aspect and opinion. It does not validate semantics.
    for l in links:
        if l["kind"]!="described_as":continue
        for p in gts_pairs:
            if p["status"]!="source_exact":continue
            if overlap(l["head"],p["aspect"]) and overlap(l["tail"],p["opinion"]):
                l["gts_corrob"].append({"id":p["id"],"polarity":p["polarity"]})
                l["sources"].append("gts_aste")
                used_gts.add(p["id"])
    for p in gts_pairs:
        if p["id"] in used_gts:continue
        if p["status"]!="source_exact":continue
        links.append({"id":"gts_"+str(p["id"]),"kind":"aspect_opinion",
            "head":p["aspect"],"tail":p["opinion"],"polarity":p["polarity"],
            "sources":["gts_aste"],"score":None,
            "gts_corrob":[],"status":"candidate_unmatched_gts",
            "spans_original":True})
    used_ent=set()
    for link in links:
        if "gliner_joint" in link["sources"]:
            for endpoint in ("head","tail"):
                e=link[endpoint]
                used_ent.add((e["start"],e["end"],e["type"]))
    unlinked=[x for x in entities.values() if
             (x["start"],x["end"],x["type"]) not in used_ent]
    # Retain old unconstrained GLiNER relations for ablation only.
    # Never silently promote them to validated claims.
    match_independent=0
    for link in links:
        if "gliner_joint" not in link["sources"]:continue
        match_independent+=any(z["kind"]==link["kind"] and
            overlap(z["head"],link["head"]) and overlap(z["tail"],link["tail"])
            for z in independents)
    return {
      "source":{k:original[k] for k in ("row","place_id","sentence_index","start","end","sentence","review")},
      "component1":{
        "status":"candidate_extraction_not_semantically_verified",
        "graph_feasible":joint.get("feasible"),"joint_error":joint.get("error"),
        "claims":links,"unlinked_observations":unlinked,
        "unresolved_gts":[p for p in gts_pairs if p["status"]!="source_exact"],
        "independent_gliner_relations_comparator":independents,
        "independent_match_count":match_independent,
        "source_sentence_always_included":True},
      "handoff":{"verbatim_source_sentence":text,
         "candidate_claims":links,
         "unlinked_observations":unlinked,
         "fallback_source_for_unexpressed_or_missing_claims":text,
         "no_emotion_inference":True}
    }

def main():
    old=read_one("matched","matched_predictions.jsonl")
    new=read_one("joint","predictions.jsonl")
    gts_cases=read_one("gts","review_cases.jsonl")
    key=lambda z:(z["row"],z["sentence_index"])
    old_by={key(z):z for z in old}
    joint_by={key(z):z for z in new}
    gts_by={(c["row"],s["sentence_index"]):{"case":c,"sentence":s}
          for c in gts_cases for s in c["sentences"]}
    if not (len(old_by)==len(joint_by)==len(gts_by)==56 and
         set(old_by)==set(joint_by)==set(gts_by)):
        raise ValueError("Matched sentence identities required")
    outputs=[]
    totals=collections.Counter()
    for k in old_by:
        row=old_by[k];j=joint_by[k];t=gts_by[k]
        if not (row["sentence"]==j["text"]==t["sentence"]["text"]):
            raise ValueError("Input sentence mismatch")
        src={**row,"start":row["source_start"],"end":row["source_end"],"review":t["case"]["review"]}
        result=reconcile(src,j,row["models"]["gliner"],t)
        outputs.append(result)
        cs=result["component1"]
        totals["sentences"]+=1
        totals["joint_feasible"]+=bool(cs["graph_feasible"])
        totals["joint_errors"]+=bool(cs["joint_error"])
        totals["joint_links"]+=sum("gliner_joint" in x["sources"] for x in cs["claims"])
        totals["gts_unmatched_links"]+=sum(x["sources"]==["gts_aste"] for x in cs["claims"])
        totals["linked_gts_corrob"]+=sum(len(x["gts_corrob"]) for x in cs["claims"])
        totals["unlinked_observations"]+=len(cs["unlinked_observations"])
        totals["unresolved_gts"]+=len(cs["unresolved_gts"])
        totals["independent_gliner_links"]+=len(cs["independent_gliner_relations_comparator"])
        totals["joint_links_matching_independent"]+=cs["independent_match_count"]
        totals["sentences_no_model_claim"]+=not bool(cs["claims"])
        totals["unlinked_reported_experiences"]+=sum(x["type"]=="reported_experience" for x in cs["unlinked_observations"])
        totals["linked_reported_experiences"]+=sum(x["kind"]=="evokes_experience" for x in cs["claims"])
        n_j=sum("gliner_joint" in x["sources"] for x in cs["claims"])
        # Conservation: every successful graph relation and extracted GTS pair
        # is retained either as joint, GTS corroboration or unmatched candidate.
        assert n_j==len(j["graph"].get("relations",[]))
        n_gts=len(t["sentence"]["extraction"]["relations"])
        n_overlap=sum(len(x["gts_corrob"]) for x in cs["claims"])
        n_solo=sum(x["sources"]==["gts_aste"] for x in cs["claims"])
        assert n_gts==n_overlap+n_solo+len(cs["unresolved_gts"])
        assert cs["graph_feasible"] or cs["joint_error"] is not None
        for relation in cs["claims"]:
            for p in ("head","tail"):
                v=relation[p]
                if v.get("status")=="unresolved_source":continue
                if isinstance(v.get("start"),int):
                    assert row["sentence"][v["start"]:v["end"]]==v["text"]
        assert result["source"]["review"][row["source_start"]:row["source_end"]]==row["sentence"]
        assert result["handoff"]["verbatim_source_sentence"]==row["sentence"]
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"reconciled.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in outputs))
    report={
      "method":"Parallel GLiNER JointIE and GTS inference; deterministic span-aware evidence reconciliation",
      "not_model_training":True,"not_precision_recall_f1":True,
      "no_emotion_target_extraction":True,
      "all_source_sentences_retained":True,"sample_reviews":20,
      "counts":dict(totals),
      "known_limits":["Typed edge constraints ensure allowed endpoint types, not semantic truth.",
      "GTS agreement is span overlap and not independent gold correctness.",
      "Unlinked entities are observations, not complete propositions.",
      "Full original sentence survives all missed or erroneous extraction.",
      "No relevance or NLI improvement demonstrated by this component-only run."]
    }
    (OUT/"summary.json").write_text(json.dumps(report,indent=2))
    for r in outputs:
        if r["source"]["row"] in (55,74,97,113,123,139,181,187):
            print("FOCUS",json.dumps({"text":r["source"]["sentence"],
                "claims":r["component1"]["claims"],
                "unlinked":r["component1"]["unlinked_observations"],
                "prior_independent_links":r["component1"]["independent_gliner_relations_comparator"]},ensure_ascii=False))
    print("SUMMARY",json.dumps(report,indent=2))
if __name__=="__main__":main()
