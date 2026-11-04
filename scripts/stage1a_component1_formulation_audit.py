#!/usr/bin/env python3
"""Frozen Component 1 controlled formulation audit: A/B/C with GTS D.

A: original typed JointIE schema, sentence.
B: claim-oriented schema, sentence.
C: claim-oriented schema, full original review.
D: deterministic GTS overlap / preservation, no model inference.

No assistant-authored correctness labels. Relation coverage and source fidelity
are diagnostics, not accuracy. Preserve cross-sentence graph edges separately.
"""
import collections
import json
import pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE=ROOT/"reports/component1_formulation_inputs"
OUT=ROOT/"reports/component1_formulation_audit"
CASES={55,74,97,113,123,139,181,187}
def load(name,filename):
    fs=list((BASE/name).rglob(filename))
    if len(fs)!=1:raise ValueError((name,filename,fs))
    return [json.loads(s) for s in fs[0].read_text(encoding="utf8").splitlines() if s]
def graph_edges(g):
    ent={x["id"]:x for x in g.get("entities",[])}
    edges=[]
    for r in g.get("relations",[]):
        if r["head"] not in ent or r["tail"] not in ent:
            raise ValueError("dangling edge")
        a,b=ent[r["head"]],ent[r["tail"]]
        edges.append({"type":r["type"],"head":a,"tail":b,"confidence":r.get("confidence")})
    return edges
def compact(edges):
    return [{"type":e["type"],"head":e["head"]["text"],"tail":e["tail"]["text"]} for e in edges]
def overlaps(a,b):
    return min(a["end"],b["end"])>max(a["start"],b["start"])
def index(rows):
    return {(x["row"],x["sentence_index"]):x for x in rows}
def main():
    aa=load("A","predictions.jsonl")
    bc=load("BC","predictions.jsonl")
    gts=load("GTS","review_cases.jsonl")
    A=index(aa)
    B=index([x for x in bc if x["condition"]=="B"])
    C={x["row"]:x for x in bc if x["condition"]=="C"}
    G={(c["row"],s["sentence_index"]):s
        for c in gts for s in c["sentences"]}
    assert len(A)==len(B)==len(G)==56 and set(A)==set(B)==set(G)
    assert len(C)==len(gts)==20
    totals=collections.defaultdict(collections.Counter)
    reports=[]
    for k,ar in A.items():
        br=B[k];gr=G[k];cr=C[k[0]]
        text=ar["text"];st,en=ar["start"],ar["end"]
        if not(text==br["text"]==gr["text"] and
            cr["input_text"][st:en]==text and
            ar["place_id"]==br["place_id"]==cr["place_id"]):
            raise ValueError("Review or sentence mismatch")
        outputs={}
        for label,obj in (("A",ar),("B",br)):
            entities=obj["graph"].get("entities",[])
            edges=graph_edges(obj["graph"])
            for e in entities:
                assert text[e["start"]:e["end"]]==e["text"]
            outputs[label]={"entities":entities,"edges":edges,"error":obj.get("error")}
        # C runs on the complete original review, so only include entities and
        # relations whose endpoints lie entirely within THIS sentence.
        ce=[x for x in cr["graph"].get("entities",[])
            if st<=x["start"] and x["end"]<=en]
        craw=graph_edges(cr["graph"])
        cin=[x for x in craw if all(st<=x[q]["start"] and x[q]["end"]<=en
                                     for q in ("head","tail"))]
        cross=[x for x in craw if not all(st<=x[q]["start"] and x[q]["end"]<=en
                                     for q in ("head","tail"))]
        outputs["C"]={"entities":ce,"edges":cin,"error":cr.get("error"),
            "review_graph_cross_or_other_sentence":cross}
        for tag,data in outputs.items():
            totals[tag]["sentences"]+=1
            totals[tag]["sentences_with_entities"]+=bool(data["entities"])
            totals[tag]["sentences_with_edges"]+=bool(data["edges"])
            totals[tag]["entities"]+=len(data["entities"])
            totals[tag]["edges"]+=len(data["edges"])
            totals[tag]["errors"]+=bool(data["error"])
            totals[tag]["experience_entities"]+=sum(
                x["type"] in ("reported_experience",) for x in data["entities"])
            totals[tag]["experience_edges"]+=sum(
                e["type"] in ("evokes_experience","induces_experience") for e in data["edges"])
        # D identical GTS predictions applied by original source offsets to
        # each formulation: avoid false 'improvements' due to duplicate links.
        gz=gr["extraction"]["relations"]
        matched={}
        for tag,data in outputs.items():
            matched[tag]=[]
            for i,t in enumerate(gz):
                a,b=t["aspect"],t["opinion"]
                if not(all(isinstance(x.get("start"),int) and isinstance(x.get("end"),int)
                    for x in (a,b))):continue
                # GTS spans are in whole review coordinates.
                if not(st<=a["start"]<a["end"]<=en and st<=b["start"]<b["end"]<=en):
                    continue
                al={"start":a["start"]-st,"end":a["end"]-st}
                bl={"start":b["start"]-st,"end":b["end"]-st}
                if text[al["start"]:al["end"]]!=a["text"] or text[bl["start"]:bl["end"]]!=b["text"]:
                    raise ValueError("GTS source span mismatch")
                found=False
                for e in data["edges"]:
                    head=e["head"];tail=e["tail"]
                    h={**head,"start":head["start"]-(st if tag=="C" else 0),
                       "end":head["end"]-(st if tag=="C" else 0)}
                    v={**tail,"start":tail["start"]-(st if tag=="C" else 0),
                       "end":tail["end"]-(st if tag=="C" else 0)}
                    if e["type"] in ("described_as","has_condition") and overlaps(h,al) and overlaps(v,bl):
                        found=True;break
                if found:matched[tag].append(i)
            totals[tag]["gts_reconciled"]+=len(set(matched[tag]))
            totals[tag]["gts_kept_separate"]+=len(gz)-len(set(matched[tag]))
            totals[tag]["union_sentences_with_claims"]+=bool(data["edges"] or gz)
            totals[tag]["sentences_without_any_claim"]+=not bool(data["edges"] or gz)
        reports.append({"row":k[0],"sentence_index":k[1],"place_id":ar["place_id"],
          "text":text,"start":st,"end":en,
          "GTS":[{"aspect":x["aspect"]["text"],"opinion":x["opinion"]["text"],
                  "polarity":x.get("polarity")} for x in gz],
          "conditions":{tag:{"entities":[{"text":e["text"],"type":e["type"]} for e in data["entities"]],
            "edges":compact(data["edges"]),"error":data["error"],
            "gts_corrob_ids":matched[tag]} for tag,data in outputs.items()}})
    summary={"sample":{"reviews":20,"matched_sentences":56},
      "conditions":{"A":"existing typed schema, sentence","B":"claim schema, sentence",
           "C":"same claim schema, entire review (mapped to each original sentence)",
           "D":"frozen GTS combined identically with A, B, C"},
      "metrics":{k:dict(v) for k,v in totals.items()},
      "C_review_edges_total":sum(len(graph_edges(x["graph"])) for x in C.values()),
      "C_review_entities_total":sum(len(x["graph"].get("entities",[])) for x in C.values()),
      "C_review_errors":sum(bool(x.get("error")) for x in C.values()),
      "caveats":["No complete independent human gold. Counts and match rates are NOT correctness.",
        "C has review-level context and may contain cross-sentence relationships excluded from per-sentence metrics.",
        "Different schemas define different units; count comparison is descriptive, not model quality.",
        "GTS corroboration means overlapping original spans, NOT semantic endorsement.",
        "No relevance or downstream NLI experiment occurs in this test."]}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False))
    (OUT/"matched_cases.jsonl").write_text(
        "".join(json.dumps(r,ensure_ascii=False)+"\n" for r in reports))
    print("AUDIT_SUMMARY",json.dumps(summary,indent=2),flush=True)
    for r in reports:
        if r["row"] in CASES:
            print("FIXED_CASE",json.dumps({"row":r["row"],"idx":r["sentence_index"],
                 "text":r["text"],"GTS":r["GTS"],"A":r["conditions"]["A"],
                 "B":r["conditions"]["B"],"C":r["conditions"]["C"]},
                 ensure_ascii=False),flush=True)
if __name__=="__main__":main()
