# Stage 1A — Component 2 v3 focused check (2026-11-09)

**Goal:** determine whether explicit evidence type + conservative but specific emotion applicability fixes Component 2 v2's confusing `direct`/ `indirect` and overuse of `uncertain`, without new extraction or model search.

### Fixed components
- Frozen real Qwen3 A0 extractions: same 20 reviews / 56 sentences; diagnostic 12 sentences / 23 extracted observations; original text remains authoritative.
- No change to Component 1; no Component 3 NLI executed.
- Same Qwen3 8B; `think=false`; structured JSON; fixed token budget; request logging.
- Only three historical pilot labels: calm, inviting, safe. No invented nine-emotion definitions.

### Change to Component 2
1. `place_related` yes/no/uncertain independent of emotion.
2. `evidence_type` explicitly distinguishes direct personal experience, explicit atmosphere descriptor, environmental/social indicators, location/access facts, general subjective praise, unrelated personal events and unclear source.
3. Per-emotion applicability `direct/indirect/not_applicable/uncertain`, where `not_applicable` is the default when no defensible specific connection exists; `uncertain` means a genuinely ambiguous source or relationship. Both indirect support and potential contradiction matter.
4. Require literal source `basis_quote` for direct/indirect, flag direct labels inconsistent with the evidence type and flag place-attribution contradictions; no hard deletion, preserve all raw labels. Keep Component 1's verification status separate: an incorrect causal paraphrase must not become ineligible simply because it is unsupported.

### Execute on the researcher's local PowerShell

```powershell
cd "$HOME\Desktop\Atmosphere-grounding"
git pull
python scripts/stage1a_component2_v3.py --check-only
python scripts/stage1a_component2_v3.py
```

The script writes `reports/stage1a_component2_v3/diagnostic/summary.json` and `decisions.jsonl`. If interrupted, use `--resume`. Each model request prints `REQUEST` before inference. No previous outputs are overwritten. v2 records are included for side-by-side comparison if present in their original local folder. A default 180-second timeout avoids unobserved long stalls; the script exits and writes an error record if a request fails.

### Actual source-derived failure cases to inspect

- Row 55 (0): generic `charming and cozy` vs `in the heart of Cambridge`; mere geography should not imply calm, inviting, safe. `cozy` might be indirect, but not automatically direct.
- Row 55 (2): reported protected/comforted experience, distinguish from trees/paths as environmental indicators; preserve typo `circulous` rather than confidently rewriting into `winding`.
- Row 74 (1): `well patrolled by police` is indirect relevance to perceived safety, not direct visitor feeling. `Ckean` is ambiguous.
- Row 97 (0): source speculation about garden redesign remains a place claim but source fidelity is questionable.
- Row 97 (2): elevator and public access are access facts, possibly indirect to inviting but not automatically to safety/calm.
- Row 113 (0): `inspiring place` and `great location` are place-related but not blanket evidence for all 3 emotions.
- Row 187 (0): `reception is kindly and informative` is a social indicator, not necessarily an explicit self-reported emotional experience.

### Go criterion
Inspect all 23 original sentence/claim/relevance tuples, compare with v2, and determine whether (1) direct vs indirect is conceptually faithful, (2) no specific indirect or opposing evidence is missed, (3) unwarranted universal relevance and ambiguous labels are reduced, (4) source quotes and negative/hedged relations are preserved. Output counts alone are not quality metrics. If these pass a small human review, freeze Component 2 provisionally and run a **no-filter vs. selected-evidence NLI ablation with the same NLI model**. No hard filter or accuracy claims until independent annotation.
