# Step 0 diff

```diff
- from stage1a_component3_abc import HYPOTHESES as DIRECTIONAL
+ DIRECTIONAL = {"calm":"This place feels calm.","inviting":"This place feels inviting.","safe":"This place feels safe."}

- if REPORTED.search(part): ...
- elif INDICATOR.search(part): ...
+ lemmas = sampling_lemmas(part)
+ if REPORTED_LEMMAS & lemmas: ...
+ elif INDICATOR_LEMMAS & lemmas: ...

- "REVIEW CONTEXT (for reference only):\n" + sentence
+ review = read_lines(REVIEWS)[case["row"]]["text"]
+ assert review[case["start"]:case["end"]] == sentence
+ "REVIEW CONTEXT (for reference only):\n" + review

+ seen_quotes = set()
- if permitted and quote and quote in sentence:
+ if permitted and quote and quote in sentence and quote not in seen_quotes:
+     seen_quotes.add(quote)
```

The archived `research_audit/stage1a_final_2026-11-10/results/*.json` files are unchanged.
