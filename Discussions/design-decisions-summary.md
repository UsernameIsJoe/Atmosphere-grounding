# Design decisions summary

Condensed from design sessions (2026-08-27). Full detail: [`Docs/ARCHITECTURE.txt`](../Docs/ARCHITECTURE.txt).

---

## End goal (C)

- Output **strength per lexicon** (inviting / safe / calm) + **ranked image features** under each  
- Associations from **co-occurrence only** — LLM does **not** invent links  

---

## Scientific story

1. Comments contain atmosphere language → LLM maps to **lexicon umbrellas**  
2. Photos → **Layer B** measures **ontology features** (primary image signal)  
3. **Learner** counts weighted co-occurrence at **place level**  
4. Validate on **held-out places**  

---

## Pass A vs Pass B

| | Pass A | Pass B |
|---|--------|--------|
| Input | Comment only | Comment + Layer B top-k (~12–24 families) |
| Output | `mentions.jsonl` | `mentions_fused.jsonl` |
| Nouns | Text-only → ontology add-ons | Confirm (full wt) / carry-over (reduced wt) / image-only add |

**Why nouns:** Photos may miss what reviewers saw; text add-ons supplement Layer B, never replace it.

---

## Image feature data

- **Primary:** Layer B place profile (DINO, Mask2Former, SigLIP, metrics)  
- **Add-ons:** Ontology-mapped nouns from Pass A/B  

---

## Scoring (locked)

- **Match:** Soft weight; cosine z-scored within place  
- **Aggregation:** Weighted mean → place profile  
- **Dual tracks (both computed):**  
  - Track 1: corpus co-occurrence, equal weight per place  
  - Track 2: within-place family rank (explain one place)  

---

## Data constraints

- Google Places API: ≤5 review texts, ≤10 photo refs per place  
- Scale by **more places**, not deeper reviews per place  
- Pilot 43 places / 3 photos = **credit budget**, not design ceiling  

---

## Known weakness

- **Location pairing:** same `place_id`, not caption pairs → soft weights + place aggregation  

---

## Later

- **Street View:** after place-photo path validates  
- **LoRA:** ontology language; targets from measured profiles + co-occurrence tables  

---

## Open (defer to prototyping)

- Pass A vs B selection rule per review  
- Track 1 vs 2 blend in final output  
- Pairing improvements beyond soft cosine  
- Opportunities list (see design chat; revisit after prototype)  

---

## Code vs design gap

Pilot Pass B still uses DINO object lists; target uses full Layer B profile. Co-occurrence learner with dual tracks not fully implemented yet.
