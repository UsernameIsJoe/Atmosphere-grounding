#!/usr/bin/env python3
"""Generate the human-readable pilot report and a figure from frozen analysis."""
import csv, hashlib, json
from pathlib import Path
P=Path(__file__).resolve().parent
summary=json.loads((P/'analysis_summary.json').read_text()); details=json.loads((P/'analysis_details.json').read_text())
rows=list(csv.DictReader((P/'comparison.csv').open())); cleanup=json.loads((P/'cleanup.json').read_text())
models=['qwen3.8:27b','gemma4:31b-it-bf16']
names={'qwen3.8:27b':'Qwen3.8 27B (Q4_K_M)','gemma4:31b-it-bf16':'Gemma4 31B IT (BF16)'}
state={'neither':'neither','support_only':'support','opposition_only':'oppose','both':'both'}
def fmt(x):
    x=float(x)
    return '>99.99%' if x>.9999 else f'{100*x:.1f}%'
tables=[]
for model in models:
    tables.append('### '+names[model]+'\n\n| Case | Calm-only extraction | Original-code readout | Rotated-code readout | Largest state-score change |\n|---|---|---|---|---|')
    for r in rows:
        if r['model']!=model:continue
        ex=state.get(r['extraction_state'],'invalid quote') if r['extraction_valid']=='True' else 'invalid quote'
        tables.append(f"| {r['case_id']} | {ex} | {state[r['canonical_state']]} ({fmt(r['canonical_confidence_lower'])}) | {state[r['rotated_state']]} ({fmt(r['rotated_confidence_lower'])}) | {100*float(r['max_state_probability_shift_upper']):.2f} pp |")
    tables.append('')
metrics=['| Measurement | Qwen | Gemma |','|---|---:|---:|']
for label,key,suffix in [
    ('Matched main calls','calls',''),('Extraction outputs passing schema/quote checks','valid_extractions','/12'),
    ('Valid native first-code readouts','valid_native_probability_readouts','/24'),
    ('All four alternatives returned','complete_four_state_distributions','/24'),
    ('Chosen-state changes after code rotation','code_mapping_label_flips','/12'),
    ('Readouts with chosen-state probability ≥99.9%','readouts_at_least_99_9_percent','/24')]:
    metrics.append('| '+label+' | '+' | '.join(str(summary['models'][m][key])+suffix for m in models)+' |')
metrics.append('| Largest semantic state-score change after code rotation | '+' | '.join(f"{summary['models'][m]['max_semantic_state_probability_shift_pp']:.2f} pp" for m in models)+' |')
metrics.append('| Mean total-variation distance after code rotation | '+' | '.join(f"{100*summary['models'][m]['mean_total_variation_lower']:.2f}%" for m in models)+' |')
report='''# Calm native-probability pilot — 12 matched reviews, November 23, 2026

**Status: executed development pilot.** 72 main calls across the same 12 original target segments/full reviews and the same two model digests used in the v0.5 study. One additional JSON-interface preflight failed atomic-code validation and is archived separately. No gate, cascade, new training or independent held-out evaluation was run.

## What this test establishes

**Native decision probabilities can be captured in a clear, mathematically defined way. They are neither forced to 0/1 by greedy decoding nor generated confidence ratings.** Both models produced valid single-code measurements on all 24 readouts per model. However, score robustness differed: Qwen's chosen states were stable while probabilities moved appreciably after code renaming; Gemma was nearly saturated and confidently retained a known attribution error. This supports further testing, not automatic adoption as evidence-quality weights.

'''+ '\n'.join(metrics)+'''

All chosen states were unchanged across the two code mappings. This checks one code permutation only; it does not demonstrate invariance to arbitrary prompts, option order, other checkpoints or new locations.

![Chosen-state probabilities under two code mappings](probability_readout.png)

Higher plotted confidence does not imply greater correctness. The vertical highlight marks K01, whose calm attribution was previously adjudicated as no place-attributed evidence.

## Matched method and the necessary interface refinement

1. **Existing extraction, narrowed to CALM:** retain the original v0.5 evidence rules, empty claim lists, opposing/supporting claims, exact source quotes and E/T. Change only the emotion scope and corresponding schema cardinality; also log native token probabilities.
2. **Companion source-level probability readout:** assess the same original target and full context directly, using four exhaustive evidence configurations: neither, support only, opposition only, both. This is an experimental measurement probe, not a replacement adopted for the project pipeline.
3. **Code control:** original mapping A/B/C/D corresponds to neither/support/oppose/both; rotated mapping B/C/D/A preserves semantic option order and changes only the code assigned to each state. Every case receives both variants for both models.

The initial Qwen JSON-string preflight combined the opening quote and state code into one token (`"A`). It failed our clean-code alignment check. The revised readout requests a single plain letter, disables JSON grammar only for that readout and limits generation to one token. Every valid measured code is therefore the first generated token, before quotes, explanations or other generated evidence. This does not mean JSON probabilities are inherently unusable; it makes this specific measurement unambiguous.

For candidate code k, use its returned native likelihood p(k). A state probability **conditional on the four canonical response codes** is q(k) = p(k) / sum(p(A), p(B), p(C), p(D)). These are model preferences over this defined readout, not calibrated probabilities of correctness or measurements of emotional intensity. Raw token likelihoods are retained separately. The model is never asked to output numeric confidence.

**Alternative coverage:** Qwen returns all four codes on 24/24 readouts. Gemma returns all four on 7/24; 17 readouts omit extremely unlikely alternatives from the top-20 list. These omissions are not zeros. Offline analysis bounds their probabilities by the reported top-k cutoff. The widest conditional-state interval for Gemma is below 0.000008 percentage points. Complete Gemma vectors remain marked unavailable where alternatives are missing, despite tight bounds.

Unrounded log probabilities and the full raw responses are preserved. Bounds in `analysis_details.json` and `comparison.csv` are authoritative: offline analysis uses the top-k cutoff directly rather than subtracting rounded dominant probabilities from one. The frozen runner and its original diagnostic fields remain unchanged for audit.

## Important cases

### K01: personal-event stress and conditional probability meaning

The target says “It was so stressful but her humanity made everything so much better!” Full context attributes the stress to a late photographer. The user's calm adjudication was **no place-attributed directional evidence**.

- Both calm-only extractions still produce an opposing claim from “It was so stressful.”
- Qwen's likelihood for the generated direction-token path `op` + `poses`, conditional on its already chosen quote, is **98.45%**. Gemma's corresponding `opp` + `oses` path likelihood is **99.9926%**. These are likelihoods of the selected canonical token paths, not distributions normalized over every possible direction string or probabilities that the claims are valid.
- Qwen's standalone readout instead chooses **neither**, at **48.73%** in the original coding and **67.66%** after rotation.
- Gemma's standalone readout chooses **opposition**, at **97.56%** and **99.07%** respectively, retaining the known attribution error with high preference.

The direction-after-quote and source-level readout measure different conditional decisions under different prompts. Their difference is not evidence that merely retaining probabilities improves accuracy. It demonstrates why we must specify the decision and conditioning context before putting a number into the emotion representation.

### U03 and U06: score variation is observable

Qwen assigns **98.31%** to opposition for U03's intrusive traffic noise, versus **48.48%** to support for U06's relaxed sitting/lights/music experience in the original coding. Its scores therefore retain distinctions discarded by hard labels. Whether those distinctions improve training remains untested. The user had adjudicated U06 as supporting calm.

### K04: source-boundary failure retained

Gemma emits “without the usual hustle and bustle” as an E quote. That phrase occurs in the full review but not in the fixed target segment. The extraction fails exact-target quote validation; it is not counted as empty or retried. Both models also infer calm from low crowding, a previously flagged conceptual boundary requiring researcher review. No new human gold label is assigned to K04 here.

## Case-by-case readout

“Support,” “oppose,” “neither” and “both” below are semantic states, not literal A–D output codes. Percentages are chosen-state probabilities conditional on the four codes. Gemma values with omitted alternatives use tight lower bounds; full precision and missingness are in the CSV/JSON.

'''+ '\n'.join(tables)+'''
## Interpretation and next bounded test

- **Feasibility: demonstrated.** The one-token response code provides a clean native probability signal. Both exact model digests support native logprobs through Ollama 0.40.17.
- **Hard-label stability: observed for this code swap.** Both models keep 12/12 states; their original-code states disagree with each other on K01, K05 and K06. Agreement is not correctness.
- **Score stability: limited for Qwen.** The largest state-probability movement is 23.26 percentage points despite unchanged chosen states. Do not assume arbitrary code names leave the emotion vector unchanged.
- **Gemma's raw soft targets are close to hard labels.** 21/24 chosen-state probabilities exceed 99.9%. Their small alternative likelihoods remain available in unrounded form or bounded; later calibration/temperature-based softening might still be informative, but was not tested here.
- **General claim-quality weighting: not established.** K01 is a concrete high-confidence attribution failure. The two explicit calm adjudications and this reused development set cannot establish 12-case accuracy, AUROC or calibration.
- **Training value: not tested.** A next bounded study should compare hard labels with actual soft targets and with constant-smoothing/shuffled-probability controls, preserving the same data splits and matching. No student/image model was trained in this pilot.

## Reproduction and files

- [Frozen protocol](PROTOCOL.md), [runner](run_pilot.py), [manifest](manifest.json), [offline analysis](analyze_results.py).
- [Summary](analysis_summary.json), [case details and corrected bounds](analysis_details.json), [CSV comparison](comparison.csv), [original runner summary](summary.json).
- [Raw result archive](raw_results_bundle.tar.gz): all 72 full requests/responses with native token alternatives, model runtime metadata, prompts, logs and the separate failed JSON-interface preflight.
- [Source manifest](source_manifest.json) and [source fetch helper](fetch_sources.py) recover the exact public input files at commit `79a6e4b61ec962661355aec898ca577551e87b47`; no synthetic review cases were used. To rerun, fetch sources, then run `python run_pilot.py prepare` before leasing compute. Existing manifests prevent silent drift or accidental mixing of runs.
- Models: Qwen3.8 27B **Q4_K_M** (`aaee06c39dcf2437cde036998d960e1fc1494b8191be7cc9657d01e509097813`); Gemma4 31B IT **BF16** (`df1661a2a6aaa94faf24bbaf23a691877a27d0e6052598f105a225618a079e76`). They match prior digests but differ in family and quantization; probabilities should not be presumed cross-model calibrated.

## Compute and cleanup

One RTX PRO 6000 Blackwell Server Edition 96 GB pod at the advertised **$2.69/hour**, with no persistent volume. All results were downloaded and SHA256-verified before termination. The subsequent pod list was empty.

'''+f"Lease duration was approximately **{cleanup['elapsed_minutes']:.1f} minutes**, giving an estimated compute cost of **${cleanup['estimated_compute_usd']:.2f}**, excluding any separate storage charges. This is an estimate, not an itemized bill. See [cleanup record](cleanup.json) and [runtime](runtime_system.json).\n"
(P/'README.md').write_text(report)

try:
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,4.2),sharey=True)
    for ax,model in zip(axes,models):
        rr=[r for r in rows if r['model']==model];xs=list(range(len(rr)))
        a=[100*float(r['canonical_confidence_lower']) for r in rr];b=[100*float(r['rotated_confidence_lower']) for r in rr]
        ax.axvspan(-.35,.35,color='#c74343',alpha=.08)
        for x,y,z in zip(xs,a,b):ax.plot([x,x],[y,z],color='#8995a2',lw=1)
        ax.scatter(xs,a,s=30,label='Original codes',color='#2267a5',zorder=3)
        ax.scatter(xs,b,s=28,label='Rotated codes',color='#dc8a21',marker='D',zorder=3)
        ax.set_xticks(xs,[r['case_id'] for r in rr],rotation=45);ax.set_title(names[model]);ax.set_ylim(35,102)
        ax.grid(axis='y',alpha=.2);ax.spines[['top','right']].set_visible(False);ax.legend(frameon=False,fontsize=8,loc='lower left')
    axes[0].set_ylabel('Model preference for chosen evidence state (%)')
    fig.suptitle('Same 12 inputs, two code mappings: score stability is separate from correctness',fontsize=11)
    fig.tight_layout();fig.savefig(P/'probability_readout.png',dpi=180);plt.close(fig)
except ImportError:
    print('Matplotlib unavailable; report tables remain authoritative.')
print('Wrote README.md and probability_readout.png when plotting is available.')
