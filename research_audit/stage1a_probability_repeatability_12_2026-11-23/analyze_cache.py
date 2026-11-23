#!/usr/bin/env python3
"""Analyze the separately logged, adaptively added prompt-cache control."""
import json, statistics
from collections import defaultdict
from pathlib import Path
from analyze_repeat import stat_group, STATES, sha

ROOT=Path(__file__).resolve().parent

def analyze():
    rows=[json.loads(l) for l in (ROOT/'qwen_cache_control/responses.jsonl').read_text().splitlines()]
    assert len(rows)==240 and len({(r['case_id'],r['rotation'],r['mode'],r['repeat']) for r in rows})==240
    native=[json.loads(l) for l in (ROOT/'results/qwen3.8_27b/responses.jsonl').read_text().splitlines()]
    groups=defaultdict(list); ng=defaultdict(list)
    for r in native:
        if r['phase']=='main':ng[(r['case_id'],r['rotation'])].append(r)
    for r in rows:
        assert not r.get('error') and r['measurement']['valid']
        assert sha(r['request'])==r['request_sha256']
        groups[(r['case_id'],r['rotation'],r['mode'])].append(r)
    assert all(len(rs)==10 for rs in groups.values())
    stats={key:stat_group(rs) for key,rs in groups.items()}
    details=[]
    for cid,rotation in sorted({(r['case_id'],r['rotation']) for r in rows}):
        warm=stats[(cid,rotation,'warm')];cold=stats[(cid,rotation,'cold')]
        ns=stat_group(ng[(cid,rotation)])
        # Verify cache_prompt is the sole request factor between the modes.
        request_sets=[]
        for mode in ('warm','cold'):
            request_sets.append({sha({k:v for k,v in r['request'].items() if k!='cache_prompt'}) for r in groups[(cid,rotation,mode)]})
        assert request_sets[0]==request_sets[1] and len(request_sets[0])==1
        gap=lambda a,b:max(max(abs(a['mean_probability_intervals'][s][0]-b['mean_probability_intervals'][s][1]),abs(a['mean_probability_intervals'][s][1]-b['mean_probability_intervals'][s][0])) for s in STATES)
        details.append({'case_id':cid,'rotation':rotation,'warm':warm,'cold':cold,
            'max_native_vs_warm_mean_gap_upper_pp':100*gap(ns,warm),
            'native_selected_states':ns['states'],
            'warm_agrees_with_native_states':ns['states']==warm['states'],
            'cold_agrees_with_native_states':ns['states']==cold['states'],
            'max_warm_vs_cold_mean_gap_upper_pp':100*gap(warm,cold)})
    summary={'readouts':len(rows),'prompts':12,'repeats_per_condition':10,
        'max_native_vs_warm_mean_gap_upper_pp':max(d['max_native_vs_warm_mean_gap_upper_pp'] for d in details),
        'warm_native_state_agreement_prompts':sum(d['warm_agrees_with_native_states'] for d in details),
        'cold_native_state_agreement_prompts':sum(d['cold_agrees_with_native_states'] for d in details),
        'max_warm_vs_cold_mean_gap_upper_pp':max(d['max_warm_vs_cold_mean_gap_upper_pp'] for d in details),
        'conditions':{},'qualification':'Adaptive diagnostic after native repeat noise was observed. Same Ollama-bundled binary and rendered prompts; direct completion endpoint. Twelve selected prompts, no calibration or general determinism claim.'}
    for mode in ('warm','cold'):
        gs=[g for key,g in stats.items() if key[2]==mode]
        rs=[r for r in rows if r['mode']==mode]
        summary['conditions'][mode]={'readouts':len(rs),
            'max_identical_request_probability_range_upper_pp':100*max(g['max_probability_range_upper'] for g in gs),
            'repeat_label_flip_groups':sum(len(g['states'])>1 for g in gs),
            'groups_with_identical_native_logprobs':sum(g['distinct_logprob_fingerprints']==1 for g in gs),
            'median_request_seconds':statistics.median(r['elapsed_seconds'] for r in rs),
            'cached_prefix_tokens_range': [min(r['response'].get('timings',{}).get('cache_n',-1) for r in rs),max(r['response'].get('timings',{}).get('cache_n',-1) for r in rs)],
            'prompt_tokens_evaluated_range': [min(r['response'].get('timings',{}).get('prompt_n',-1) for r in rs),max(r['response'].get('timings',{}).get('prompt_n',-1) for r in rs)]}
    (ROOT/'cache_analysis_summary.json').write_text(json.dumps(summary,indent=2))
    (ROOT/'cache_analysis_details.json').write_text(json.dumps(details,indent=2))
    print(json.dumps(summary,indent=2))

if __name__=='__main__':analyze()
