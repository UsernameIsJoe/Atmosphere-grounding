# Three pre-gate checks — 2026-11-18

All 36 unchanged original reviews completed on Runpod; exit 0. No model training, no LLM/gate/emotion calls, no automatic adoption or removal.

| Check | Result |
| --- | --- |
| Raw or normalized exact duplicates | 0 groups |
| Near duplicates, word-trigram Jaccard >=0.8 | 0 pairs |
| Non-English top language | 0/36 |
| Uncertain language, top score <0.8 | 0/36 |
| Main toxicity >=0.5 | 0/36 |
| Main toxicity >=0.2 or >=0.8 | 0/36 at either threshold |
| Any toxicity category >=0.5 | 0/36 |
| Additional archived-v5 KEEP reviews flagged | 0/22 |

All 36 were classified as English. Lowest top-language score: 0.822698. All reviews fit Detoxify's 512-token limit (maximum 226 tokens without special tokens); no truncation or window aggregation was needed. Full-review toxicity inference took 41.60 seconds for 36 reviews; the script took 54.57 seconds including model downloads, excluding environment installation and pod startup. This is one CPU run, not a general benchmark.

## N05 and interpretation

N05 remains unflagged: toxicity score **0.00063436** versus provisional cutoff **0.5**, English score 0.958177. It ranks 13/36 by toxicity (counting scores at least as high). Highest toxicity in this set: K05, 0.00736459. This confirms these checks do not catch the motivating personal-rant case in this cohort. Toxicity is not our researcher's exact rhetorical eligibility construct.

At these diagnostic thresholds, all 36 would proceed to the unchanged relevance gate, whose archived v5 verdicts remain 22 KEEP / 14 REJECT. This is a deterministic join to existing gate outputs, not a new gate run or end-to-end deployment. No reason to lower the cutoff post hoc merely to force N05 to be caught. No positive toxicity examples or labeled independent holdout were included; zero flags is not an accuracy estimate or proof of performance.

## Components and reproducibility

1. Duplicate matching: raw text and NFKC/casefold/whitespace-normalized text. All 630 review pairs checked using exact word-trigram Jaccard; near-duplicate cutoff 0.8 with at least five words each. Datasketch MinHash (128 permutations, seed 42) estimates also saved; exact Jaccard controls flags, avoiding approximate-search misses in this small cohort. This is a within-cohort lexical check, not paraphrase detection or comparison against the complete review corpus. Different reviewers independently writing generic praise should not automatically be treated as fraud.
2. Language: pretrained fastText lid.176.bin, 176-language model. Top three scores saved. Non-English routing and uncertainty are separate flags; neither establishes invalid content.
3. Toxicity: official Detoxify unbiased RoBERTa checkpoint, using the author's pinned library implementation. Main toxicity cutoff 0.5, with predeclared sensitivity at 0.2/0.8; all seven returned category scores saved. Thresholds are diagnostic, not calibrated probabilities or an adopted rejection policy. No fine-tuning.

Runtime: cpu3c, 8 vCPU / 16 GB, CPU-only, US-CA-2, $0.24/hour. All model checksum hashes and installed versions are in runtime.json; input and runner hashes in manifest.json; original output checksums in hashes.json. Codebook/prompt/current gate config unchanged.

Reusable installation: scripts/setup_pregate_three_checks_20261118.sh
Runner: scripts/stage1a_pregate_three_checks_20261118.py
Source commit: df8dc7b12abedc0e024c3a659a2c03ab094eda32

Source models:
- https://fasttext.cc/docs/en/language-identification.html
- https://github.com/unitaryai/detoxify
- https://github.com/ekzhu/datasketch

The installer reconstructs the tested CPU environment and downloads the pretrained weights. No paid model endpoint or persistent pod is deployed. Original review texts and per-review scores are retained in predictions.jsonl; full duplicate pairs in duplicates.json; package lock in pip-freeze.txt. Cleanup receipt follows archive verification.
