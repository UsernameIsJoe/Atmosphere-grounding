#!/usr/bin/env python3
"""Compare response formats using matched cold payloads and explicit intervals."""
import csv,hashlib,itertools,json,statistics
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parent
STATES=('neither','support_only','opposition_only','both')

def digest(req):return hashlib.sha256(json.dumps(req,ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def summarize(rs):
    iv={s:[r['measurement']['state_probability_intervals'][s] for r in rs] for s in STATES}
    means={s:[statistics.mean(v[k] for v in pairs) for k in (0,1)] for s,pairs in iv.items()}
    ranges={s:[max(0.,max(v[0] for v in pairs)-min(v[1] for v in pairs)),
        max(v[1] for v in pairs)-min(v[0] for v in pairs)] for s,pairs in iv.items()}
    return {'n':len(rs),'states':sorted({r['measurement'].get('selected_state') or 'invalid' for r in rs}),
        'distinct_native_state_score_sets':len({json.dumps(r['measurement']['native_state_logprobs'],sort_keys=True) for r in rs}),
        'means':means,'ranges':ranges,'max_repeat_range_upper_pp':100*max(v[1] for v in ranges.values()),
        'valid':sum(r['measurement']['valid'] for r in rs),
        'candidate_mass_mean':statistics.mean(r['measurement']['candidate_mass'] for r in rs),
        'mean_native_logprobs':{s:statistics.mean(r['measurement']['native_state_logprobs'][s] for r in rs)
            for s in STATES if all(s in r['measurement']['native_state_logprobs'] for r in rs)}}

def analyze():
    meta=json.loads((ROOT/'COMPLETE.json').read_text())
    fresh=[json.loads(l) for l in (ROOT/'responses.jsonl').read_text().splitlines()]
    reused=[json.loads(l) for l in (ROOT/'reused_readouts.jsonl').read_text().splitlines()]
    assert len(fresh)==meta['new_readouts'] and len(reused)==meta['reused_readouts']
    for r in fresh:
        assert digest(r['request'])==r['request_sha256'] and r['request']['cache_prompt'] is False
        assert r['response'].get('timings',{}).get('cache_n',0)==0
    primary=[r for r in fresh if r['phase']=='main']+reused
    assert len({(r['case_id'],r['condition'],r['repeat'],r['phase']) for r in primary})==len(primary)
    groups=defaultdict(list)
    for r in primary:groups[(r['case_id'],r['condition'])].append(r)
    assert len(groups)==216
    gs={k:summarize(v) for k,v in groups.items()}
    assert all(g['n'] in (3,10) for g in gs.values())
    cases=sorted({r['case_id'] for r in primary});details=[];summary={};csvrows=[]
    for fmt in ('letters','numbers','text'):
        for family in ('assignment','order') if fmt!='text' else ('order',):
            for cid in cases:
                keys=[f'{fmt}_a{i}_o0' if family=='assignment' else f'{fmt}_a0_o{i}' for i in range(4)]
                vs=[gs[(cid,k)] for k in keys]
                lower=max(max(0.,max(v['means'][s][0] for v in vs)-min(v['means'][s][1] for v in vs)) for s in STATES)
                upper=max(max(v['means'][s][1] for v in vs)-min(v['means'][s][0] for v in vs) for s in STATES)
                canonical=gs[(cid,fmt+'_a0_o0')]
                canonical_state=canonical['states'][0] if len(canonical['states'])==1 and canonical['states'][0]!='invalid' else None
                margins=[]
                if canonical_state:
                    for v in vs:
                        lp=v['mean_native_logprobs']
                        if len(lp)==4:margins.append(lp[canonical_state]-max(lp[s] for s in STATES if s!=canonical_state))
                d={'case_id':cid,'format':fmt,'family':family,'max_spread_lower_pp':100*lower,
                    'max_spread_upper_pp':100*upper,'condition_states':{k:v['states'] for k,v in zip(keys,vs)},
                    'any_variant_state_change':len({s for v in vs for s in v['states']})>1,
                    'max_repeat_range_upper_pp':max(v['max_repeat_range_upper_pp'] for v in vs),
                    'canonical_winner_logit_margin_range':max(margins)-min(margins) if len(margins)==4 else None}
                details.append(d)
                csvrows.append({k:d[k] for k in ['case_id','format','family','max_spread_lower_pp','max_spread_upper_pp','any_variant_state_change','max_repeat_range_upper_pp','canonical_winner_logit_margin_range']})
        fmtrows=[r for r in primary if r['format']==fmt]
        fmtgroups=[g for (cid,cond),g in gs.items() if cond.startswith(fmt+'_')]
        family_summary={}
        for family in ('assignment','order') if fmt!='text' else ('order',):
            ds=[d for d in details if d['format']==fmt and d['family']==family]
            family_summary[family]={'max_spread_lower_pp':max(d['max_spread_lower_pp'] for d in ds),
                'max_spread_upper_pp':max(d['max_spread_upper_pp'] for d in ds),
                'median_case_spread_upper_pp':statistics.median(d['max_spread_upper_pp'] for d in ds),
                'cases_with_changed_states':sum(d['any_variant_state_change'] for d in ds),
                'median_canonical_winner_logit_margin_range':statistics.median(d['canonical_winner_logit_margin_range'] for d in ds if d['canonical_winner_logit_margin_range'] is not None),
                'max_canonical_winner_logit_margin_range':max((d['canonical_winner_logit_margin_range'] for d in ds if d['canonical_winner_logit_margin_range'] is not None),default=None)}
        summary[fmt]={'conditions':len(fmtgroups),'readouts':len(fmtrows),
            'valid_exact_response_count':sum(r['measurement']['valid'] for r in fmtrows),
            'complete_four_state_readouts':sum(r['measurement']['complete_distribution'] for r in fmtrows),
            'mean_candidate_mass':statistics.mean(g['candidate_mass_mean'] for g in fmtgroups),
            'min_candidate_mass':min(r['measurement']['candidate_mass'] for r in fmtrows),
            'max_repeat_range_upper_pp':max(g['max_repeat_range_upper_pp'] for g in fmtgroups),
            'repeat_state_flip_groups':sum(len(g['states'])>1 for g in fmtgroups),
            'groups_with_identical_native_state_scores':sum(g['distinct_native_state_score_sets']==1 for g in fmtgroups),
            'families':family_summary}
    comparisons=[]
    for family in ('assignment','order'):
        for cid in cases:
            ls=next(d for d in details if d['format']=='letters' and d['family']==family and d['case_id']==cid)
            ns=next(d for d in details if d['format']=='numbers' and d['family']==family and d['case_id']==cid)
            comparisons.append({'family':family,'case_id':cid,'numbers_less_sensitive':ns['max_spread_upper_pp']<ls['max_spread_lower_pp'],
                'letters_spread_pp':ls['max_spread_upper_pp'],'numbers_spread_pp':ns['max_spread_upper_pp']})
    canonical={cid:{fmt:gs[(cid,fmt+'_a0_o0')]['states'] for fmt in ('letters','numbers','text')} for cid in cases}
    output={'new_readouts':len(fresh),'reused_readouts':len(reused),'unique_conditions':len(groups),
        'formats':summary,'numbers_vs_letters':comparisons,'canonical_states':canonical,
        'topk_expansion_calls':sum('expanded_topk_request' in r for r in fresh),
        'max_shared_logprob_difference_after_topk_expansion':max((abs(r['initial_top20_measurement']['native_state_logprobs'][s]-r['measurement']['native_state_logprobs'][s]) for r in fresh if 'expanded_topk_request' in r for s in set(r['initial_top20_measurement'].get('native_state_logprobs',{})) & set(r['measurement'].get('native_state_logprobs',{}))),default=0.),
        'qualification':'Same development reviews. Four cyclic variants per factor, no all-permutation or full-factorial guarantee; no independent accuracy/calibration evaluation.'}
    (ROOT/'qwen_analysis.json').write_text(json.dumps(output,indent=2))
    (ROOT/'qwen_analysis_details.json').write_text(json.dumps(details,indent=2))
    (ROOT/'qwen_condition_summaries.json').write_text(json.dumps([{'case_id':k[0],'condition':k[1],**v} for k,v in gs.items()],indent=2))
    with (ROOT/'qwen_comparison.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(csvrows[0]));w.writeheader();w.writerows(csvrows)
    print(json.dumps(output,indent=2))

if __name__=='__main__':analyze()
