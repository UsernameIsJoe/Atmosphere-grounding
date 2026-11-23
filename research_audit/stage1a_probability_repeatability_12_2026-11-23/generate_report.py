#!/usr/bin/env python3
"""Build the human-readable report and static plots from verified readouts."""
import json, math, statistics
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parent
STATES=('neither','support_only','opposition_only','both')

def build():
    summary=json.loads((ROOT/'analysis_summary.json').read_text())
    details=json.loads((ROOT/'analysis_details.json').read_text())
    cache=json.loads((ROOT/'cache_analysis_summary.json').read_text())
    cd=json.loads((ROOT/'cache_analysis_details.json').read_text())
    direct=[json.loads(l) for l in (ROOT/'direct_gemma/readouts.jsonl').read_text().splitlines()]
    druntime=json.loads((ROOT/'direct_gemma/runtime.json').read_text())
    assert summary['native_readouts']==1248 and len(direct)==64 and cache['readouts']==240
    models=list(summary['models']);cases=sorted({r['case_id'] for r in details})
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
        'axes.spines.right':False,'figure.facecolor':'white','axes.facecolor':'white'})
    fig,axes=plt.subplots(2,1,figsize=(11,7),layout='constrained')
    for model,ax,name in zip(models,axes,['Qwen3.8 27B Q4_K_M','Gemma4 31B BF16']):
        rows={r['case_id']:r for r in details if r['model']==model and r['phase']=='main'}
        x=np.arange(len(cases));w=.36
        ax.bar(x-w/2,[100*rows[c]['max_mapping_mean_spread_upper'] for c in cases],w,color='#3069b0',label='Between four mapping means')
        ax.bar(x+w/2,[100*rows[c]['max_identical_request_range_upper'] for c in cases],w,color='#e78b40',label='Within an identical request (10 repeats)')
        ax.set_xticks(x,cases);ax.set_ylabel('Percentage points');ax.set_title(name,loc='left',fontweight='bold')
        ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
    axes[0].legend(frameon=False,ncols=2,loc='upper right')
    axes[0].set_ylim(0,max(100*r['max_mapping_mean_spread_upper'] for r in details if r['model']==models[0] and r['phase']=='main')*1.25)
    fig.suptitle('Letter-mapping differences and repeat variation',fontsize=15,fontweight='bold')
    fig.savefig(ROOT/'mapping_and_repeatability.png',dpi=180)
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10.5,3.8),layout='constrained')
    modes=['warm','cold'];names=['Reuse prompt cache','Recompute full prompt']
    vals=[cache['conditions'][m]['max_identical_request_probability_range_upper_pp'] for m in modes]
    bars=axes[0].bar(names,vals,color=['#e78b40','#248578'],width=.58)
    for b,v in zip(bars,vals):axes[0].text(b.get_x()+b.get_width()/2,v+.1,f'{v:.2f} pp',ha='center')
    axes[0].set_ylim(0,max(vals)*1.28);axes[0].set_ylabel('Largest repeat range (percentage points)')
    axes[0].set_title('Qwen: 12 prompts × 10 repeats',loc='left',fontweight='bold')
    native=[json.loads(l) for l in (ROOT/'results/gemma4_31b-it-bf16/responses.jsonl').read_text().splitlines()]
    u=[r for r in native if r['phase']=='main' and r['case_id']=='U06']
    q=[];g=[]
    for rot in [f'rotation_{i}' for i in range(4)]:
        rs=[r for r in u if r['rotation']==rot]
        q.append(100*statistics.mean(sum(r['measurement']['state_probability_intervals']['support_only'])/2 for r in rs))
        g.append(statistics.mean(r['measurement']['native_state_logprobs']['support_only']-r['measurement']['native_state_logprobs']['neither'] for r in rs))
    line1=axes[1].plot(range(4),q,'o-',color='#3069b0',label='Support probability')
    axes[1].set_xticks(range(4),['ABCD','BCDA','CDAB','DABC']);axes[1].set_ylabel('Support probability (%)',color='#3069b0')
    axes[1].ticklabel_format(axis='y',style='plain',useOffset=False)
    twin=axes[1].twinx();line2=twin.plot(range(4),g,'s--',color='#b05b20',label='Support − neither logit margin')
    twin.set_ylabel('Post-cap logit margin',color='#b05b20');twin.spines['top'].set_visible(False)
    axes[1].set_title('Gemma U06: saturation hides logit movement',loc='left',fontweight='bold')
    axes[1].legend(line1+line2,[l.get_label() for l in line1+line2],frameon=False,loc='lower left',fontsize=8)
    fig.savefig(ROOT/'cache_and_gemma_logits.png',dpi=180);plt.close(fig)
    main_rows=[]
    for model in models:
        m=summary['models'][model];a=m['phases']['main'];b=m['phases']['reloaded']
        main_rows.append(f"| {model} | {a['max_identical_request_range_upper_pp']:.4f} | {a['max_mapping_mean_spread_upper_pp']:.4f} | {a['cases_with_mapping_spread_exceeding_repeat_range']}/12 | {a['cases_with_different_mapping_winners']}/12 | {m['max_phase_mean_shift_same_payload_after_reload_upper_pp']:.4f} |")
    cache_rows=[]
    for mode in modes:
        c=cache['conditions'][mode]
        cache_rows.append(f"| {mode} | {c['max_identical_request_probability_range_upper_pp']:.4f} | {c['repeat_label_flip_groups']}/12 | {c['groups_with_identical_native_logprobs']}/12 | {c['median_request_seconds']:.3f} s | {c['cached_prefix_tokens_range']} |")
    cold_rows=[]
    for cid in sorted({d['case_id'] for d in cd}):
        ds=[d for d in cd if d['case_id']==cid]
        spread=100*max(max(d['cold']['mean_probability_intervals'][s][0] for d in ds)-min(d['cold']['mean_probability_intervals'][s][1] for d in ds) for s in STATES)
        state_list='; '.join(d['rotation'].replace('rotation_','')+': '+','.join(d['cold']['states']) for d in ds)
        cold_rows.append(f'| {cid} | {spread:.4f} | {state_list} |')
    direct_rows=[]
    for cid in ('K01','K06','U06'):
        r=next(r for r in direct if r['case_id']==cid and r['rotation']=='rotation_0' and r['repeat']==0)
        winner=r['selected_state'];other=max((s for s in STATES if s!=winner),key=lambda s:r['capped_logits'][s])
        gap=r['capped_logits'][winner]-r['capped_logits'][other]
        raw=r['analytically_reconstructed_pre_cap'];rawgap=raw[winner]-raw[other] if all(raw[s] is not None for s in [winner,other]) else None
        no_cap=r['without_softcap_conditional'];uncap='non-invertible' if no_cap is None else f'{100*no_cap[winner]:.10f}%'
        direct_rows.append(f"| {cid} | {winner} | {100*r['conditional_probabilities'][winner]:.10f}% | {gap:.6f} | {rawgap:.6f} | {uncap} |")
    all_count=sum(summary['models'][m]['chosen_probability_at_least_99_9_count'] for m in models)
    dg=summary['direct_gemma'];gb=summary['models'][models[1]]
    text=f'''# Native probability repeatability, label mapping and Gemma logits

**Executed November 23, 2026.** Same twelve real source reviews/target segments as the preceding [calm probability pilot](../stage1a_calm_probability_12_2026-11-23/README.md); calm only. These repeated measurements do not add independent review samples. The wider project remains weakly tied image–text emotion grounding, beyond this pilot.

## Findings

1. **Qwen's letter sensitivity is confirmed in this setup.** The native repetitions separate mapping differences from identical-request variation. A second, cache-disabled control produces exactly repeated four-code log probabilities while retaining large mapping effects, including a changed U06 verdict under CDAB.
2. **Prompt-cache reuse is a practical source of repeat variation here.** In the controlled Qwen backend experiment, full recomputation removed observed repeat variation on all twelve tested prompts. This is a measured property of this workload and binary, not a guarantee of every GPU or future run.
3. **Gemma's saturation is not repaired by undoing its soft-cap.** We captured actual pre-softmax capped logits on the same BF16 GGUF, checked a finite-precision analytic inverse, and evaluated the resulting counterfactual. Removing the cap preserves the winner and sharpens its four-code probability. Smaller visible probability changes do not establish more stable internal preferences.

## 1. Native repeat and mapping experiment

Pinned **Ollama 0.40.17**, RTX PRO 6000 Blackwell Server Edition 96 GB; serial requests and one loaded model. Same original checkpoints: Qwen `qwen3.8:27b` Q4_K_M digest `aaee06c39dcf2437cde036998d960e1fc1494b8191be7cc9657d01e509097813`; Gemma `gemma4:31b-it-bf16` digest `df1661a2a6aaa94faf24bbaf23a691877a27d0e6052598f105a225618a079e76`. Digests verified before calls. Native backend defaults include enabled MTP; this study does not ablate MTP.

Four evidence states, in fixed semantic order: neither, support only, opposition only, both. Assign codes **ABCD, BCDA, CDAB, DABC**. Question wording, definitions, review context, target and semantic option order stay fixed. The first two payloads match the previous pilot hashes exactly. These are four cyclic assignments, not all 24 permutations and not a wording test.

Ten shuffled repeat blocks per mapping/case/model, then unload/reload and three more blocks: **624 native readouts per model; 1,248 total**. Temperature 0, seed 42, context 8192, top_k 0, top_p 1, min_p 0, repeat_penalty 1, think false, one decision token, top twenty native alternatives. Debug-render requests are excluded from the readout count.

Here, q is native probability renormalized over the four exact single-letter codes. A change of 0.01 in q is one percentage point. For each review we compare the largest state-probability spread between four mapping means with the largest within-payload repeat range. Bounds retain omitted alternatives; omitted candidates are never treated as zero. Metrics are descriptive development diagnostics, not significance tests.

**Raw-field note:** the frozen helper's legacy `marginal_probability_intervals` and `max_state_interval_width` fields remain in raw measurement objects for auditability. They use an older rounded-residual bound and are not authoritative. This run recomputed `state_probability_intervals` from the top-k cutoff; every reported result uses those corrected state intervals or native log probabilities. Recompute any support/opposition marginal bounds using the same cutoff before downstream use.

| Model | Largest identical-request range, main (pp) | Largest mapping-mean spread, main (pp) | Cases mapping spread exceeds observed repeat range | Cases with different mapping winners | Largest mean shift after reload, same payload (pp) |
|---|---:|---:|---:|---:|---:|
{chr(10).join(main_rows)}

Both models had zero within-payload verdict-flip groups in the **native** main/reload blocks. This differs from cross-mapping changes and from the separate cached backend control below. Full phase-specific results, including the three-repeat reload phase, are in [analysis_summary.json](analysis_summary.json) and [comparison.csv](comparison.csv).

![Native mapping differences and repeat ranges](mapping_and_repeatability.png)

Gemma supplied complete four-code readouts in **{gb['complete_four_state_readouts']}/624** calls. Its chosen-state lower probability bound was at least 99.9% in **{gb['chosen_probability_at_least_99_9_count']}/624** calls. Available native log-probability differences preserve relative post-cap logit margins even when the top probability rounds close to one. The largest observed within-payload range of an available pairwise margin was **{gb['max_observed_identical_request_logit_margin_range']:.6f}**. Do not compare raw logit scales across model families as a calibrated confidence scale.

## 2. Adaptive Qwen cache control

Added after native Qwen variation was observed; documented separately in [CACHE_SUPPLEMENT.md](CACHE_SUPPLEMENT.md). K01, K06 and U06 × four mappings × ten repeats × cache on/off = **240 additional calls**. Same bundled llama-server executable, GGUF and server-rendered prompts. The direct `/completion` request differs only in `cache_prompt`; mode order is interleaved. Logged token counts verify that the cold condition reused zero prefix tokens.

| Condition | Largest identical-request range (pp) | Prompts with verdict flips across repeats | Prompts with identical four-code log probabilities | Median request time | Actual reused-prefix token range |
|---|---:|---:|---:|---:|---|
{chr(10).join(cache_rows)}

These twelve prompts are three reviews under four mappings. Median timing excludes model loading. The direct cached control and public API are separate routes: the largest difference between their mapping/case mean probabilities was **{cache['max_native_vs_warm_mean_gap_upper_pp']:.4f} pp**, so the cached endpoint should not be described as numerically interchangeable with native `/api/chat` in every call. The causal cache comparison is within the direct endpoint, where the request factor is controlled.

Full recomputation does **not** remove the letter effect:

| Case | Cold-cache mapping spread (pp) | Verdicts by rotation 0–3 |
|---|---:|---|
{chr(10).join(cold_rows)}

Ollama 0.40.17's [completion implementation](https://github.com/ollama/ollama/blob/v0.40.17/llm/llama_server.go) hardcodes `cache_prompt: true`; its public [options type](https://github.com/ollama/ollama/blob/v0.40.17/api/types.go) does not expose that switch. The tested route is the private bundled backend with explicit `cache_prompt=false`, requiring a scoring adapter or server change for normal pipeline use. No production pipeline code was changed here.

![Cache control and Gemma logit movement](cache_and_gemma_logits.png)

## 3. Gemma direct logits and inverse calculation

Separate backend: **llama-cpp-python {druntime['version']}**, the identical BF16 GGUF layer, actual Ollama-rendered prompt strings. Forty-eight case/mapping inputs plus sixteen repeated full recomputations on K01, K06, U03 and U06 = **64 direct forward passes**. Context/cache cleared each time; n_ctx 8192, n_batch/n_ubatch 512, all GPU layers, flash attention false. Token IDs and runtime metadata are retained. This is a backend condition, not an unrecorded substitution for native Ollama.

The direct backend agreed with native main-phase chosen states in **{dg['native_argmax_agreement']}/64** comparisons; the largest four-code probability difference against a native mapping/case mean was **{dg['max_native_vs_direct_probability_gap_upper_pp']:.6f} pp**. All rendered-prompt hashes were verified; input token counts matched native counts in **{dg['direct_token_count_matches_native_count']}/64** comparisons. The full-vocabulary winning token was one of the four codes in **{dg['full_vocabulary_winner_is_a_code']}/64** passes. Repeated direct passes had maximum absolute code-logit difference **{dg['max_direct_repeated_logit_difference']:.9g}**. See [native_alignment.json](direct_gemma/native_alignment.json).

The GGUF metadata verifies `gemma4.final_logit_softcapping = 30`. With pre-cap value u, capped pre-softmax score s and c=30:

```math
s = c \\tanh(u/c), \\qquad p_i = \\frac{{\\exp(s_i)}}{{\\sum_j \\exp(s_j)}}.
```

For an actual score strictly inside the cap:

```math
u = c \\operatorname{{atanh}}(s/c).
```

All four code scores were inside the cap in **{dg['fully_invertible_four_code_readouts']}/64** passes; the largest forward/inverse round-trip residual was **{dg['maximum_softcap_roundtrip_abs_error']:.3g}**. These are analytic reconstructions from finite-precision capped outputs, **not an internal pre-cap tensor hook**. The round-trip check verifies the algebra; it cannot recover precision lost upstream, and the inverse becomes sensitive near the cap. Boundary scores cannot be inverted reliably. Absolute pre-cap scores cannot be recovered uniquely from returned probabilities alone because softmax discards a shared additive offset; available log-probability differences do recover post-cap score differences.

Examples below are original ABCD mapping, first direct pass. The strongest alternative is another one of the four codes, not the whole vocabulary.

| Case | Winner | Original four-code probability | Post-cap winner/runner-up margin | Reconstructed pre-cap margin | Counterfactual probability without cap |
|---|---|---:|---:|---:|---:|
{chr(10).join(direct_rows)}

Removing the cap did not reduce the selected-state probability in **{dg['uncapping_does_not_reduce_chosen_probability']}/{dg['fully_invertible_four_code_readouts']}** fully invertible passes. The cap contracts logit differences; undoing it sharpens these choices. Large score separation plus softmax produces the extreme probabilities. This experiment does not isolate which training mechanism produced that separation.

Every direct readout also contains an offline temperature grid T=1,2,4,6,8. A larger scoring temperature can spread the numbers, but no temperature was learned from independent labels here. It is a sensitivity calculation, not calibration. Returned log-probability margins are useful immediately for inspecting hidden variation; they do not by themselves become emotion intensity.

## 4. What to use next

- For probability experiments, freeze full recomputation as the measurement condition and verify it again in the intended scoring adapter. Keep model digests, binary versions, rendering, tokenization and hardware recorded.
- For letter sensitivity, remap and average a fixed balanced set of semantic distributions; retain the spread alongside the mean. Averaging a predefined four-cycle set removes dependence on which of those four is singled out; it does not prove invariance to the other twenty assignments or revised wording. The present experiment measures sensitivity, not downstream benefit from this ensemble.
- For Gemma, preserve log probabilities/logit margins alongside probabilities. Do not undo the soft-cap expecting softer confidence. If calibrated probabilities are needed, fit a scoring temperature on separate annotations and compare hard targets, fixed label smoothing and probability targets on held-out locations.
- Stable confidence can accompany an attribution error. These twelve reused cases do not establish calibration, emotional-intensity measurement, better extraction accuracy or improved image-model training. The original K01 issue remains an interpretation diagnostic; no new adjudication or model selection is claimed.

## Artifacts and reproduction

- [Frozen protocol](PROTOCOL.md), [cache supplement](CACHE_SUPPLEMENT.md), [manifest](manifest.json).
- [The twelve frozen inputs and exact target segments](inputs.jsonl), verified against the manifest's case hash.
- [Native analysis](analysis_summary.json), [case/phase comparison](comparison.csv), [cache analysis](cache_analysis_summary.json).
- [Raw result archive](raw_results_bundle.tar.gz): complete native/cache requests and responses, rendered prompts, logs, source snapshot, 64 direct readouts, token IDs, all code logits and top-twenty scores; full-vocabulary capped vectors additionally for original-map K01/K06/U06. No model weights.
- [Raw archive hash and size](BUNDLE.json), [local verification](archive_integrity.json), [compute cleanup](cleanup.json).
- Scripts: [native runner](repeat_probe.py), [cache control](cold_cache_control.py), [logit capture](direct_logits.py), [native analysis](analyze_repeat.py), [cache analysis](analyze_cache.py), [report](generate_report.py), [packaging](package_results.py), [bootstrap](bootstrap.py).

Extract the archive into this directory. Verify every archived file against `INTEGRITY.json`. The archive preserves the execution-time code; the files alongside it include later report formatting. With `PILOT_ROOT` pointing to its `frozen_source_snapshot`, the exact source bytes are self-contained. Direct-artifact analysis also uses NumPy; plots use Matplotlib:

```bash
python analyze_repeat.py
python analyze_cache.py
python generate_report.py
```

Inference additionally requires the pinned Ollama/model digests and the recorded GPU/backend configuration. The direct backend uses the specified CUDA wheel; a loader-only repair exposes Ollama's bundled NVIDIA libraries without loading its ggml/llama libraries into the Python backend. Native requests were unchanged. An initial source-download check found the already-published target script had one extra terminal newline: recovery removed only that byte and required the original frozen SHA-256 before proceeding. Both setup events and the paused/resumed cache-control insertion are preserved in the archive. No test review was changed.

The owned pod was terminated after approximately **33 minutes**; the wall-clock compute estimate at the observed $2.69/hour rate is **$1.48**, excluding any separate storage/billing adjustments. The account pod list was empty after termination. Results were downloaded and all archive/file hashes verified before deletion; see [cleanup.json](cleanup.json).

The [preceding research discussion](../../Discussions/model-probability-stability-and-logits-2026-11-23.md) links the primary literature on label bias, probability repeatability, cache/batch effects and logits. This report adds direct measurements for our checkpoints.
'''
    # GitHub's math renderer need not accept operatorname: use plain text here.
    text=text.replace('\\operatorname{atanh}','\\mathrm{atanh}')
    (ROOT/'README.md').write_text(text)
    print('GENERATED README.md and two figures')

if __name__=='__main__':build()
