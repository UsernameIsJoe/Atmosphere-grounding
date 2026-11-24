# Qualitative audit: three native decision models

Current assistant reading, November 24, 2026. Earlier discussion is visible; this is not blinded and does not create human probability targets. Exact full reviews are in `inputs.jsonl`. Values are original-wording arithmetic means over four aligned orders. Percentages below are rounded for display; all alternatives are retained at full analysis precision in the CSVs and raw records.

The earlier researcher agreement on four Gemma boundary cases is context for this reading, not a new numerical adjudication of Mammoth/Karpo/GLiDE. No inherited-reference NLL, Brier or accuracy score is used.

## K01

**Target:** It was so stressful but her humanity made everything so much better!

Neither is appropriate: the late photographer and personal wedding schedule explain the target stress and relief. The target does not attribute calm or agitation to the site atmosphere.

| Model | Neither | Support only | Opposition only | Both |
|---|---:|---:|---:|---:|
| Mammoth-1 | 23.00% | 10.19% | 32.36% | 34.45% |
| Karpo 31B | 88.33% | 1.14% | 8.91% | 1.62% |
| GLiDE 27B | 56.28% | 6.67% | 25.79% | 11.26% |

**Mammoth-1:** The original mean winner is both, with another large opposition component. This spreads probability between two misattributed readings; lower concentration does not repair the source attribution. The mean winner changes to opposition under wording 1 and returns to both under wording 2.

**Karpo 31B:** Neither is the winner in every tested presentation of this target. Its 88.33% original mean is a cleaner preference for the established attribution reading than the saved Decider vector. The exact percentage is not independently calibrated.

**GLiDE 27B:** Neither is the winner in every tested presentation, but opposition plus both still holds 37.05% in the original mean. The correct winning state does not establish a reliable complete training vector.

## K02

**Target:** Lights in the small box were years away- it was completely dark.

The target reports darkness in a restroom. It does not establish tranquility or calm-related disturbance; maintenance and general unpleasantness cannot automatically supply that dimension.

| Model | Neither | Support only | Opposition only | Both |
|---|---:|---:|---:|---:|
| Mammoth-1 | 83.92% | 0.78% | 15.08% | 0.22% |
| Karpo 31B | 99.85% | 0.02% | 0.12% | 0.01% |
| GLiDE 27B | 96.93% | 0.29% | 2.73% | 0.06% |

**Mammoth-1:** Neither wins, with 15.08% on opposition. That alternative needs a specific calm-related link not supplied by the target. This is a plausibility concern about the alternative allocation, not a numerical calibration verdict.

**Karpo 31B:** Strong neither is consistent with the target boundary. Its near-certainty is not established as calibrated.

**GLiDE 27B:** Strong neither is consistent with the target boundary; the small opposition alternative does not change the exclusion.

## K03

**Target:** I wouldn't go here if your looking for walk.

The target is about suitability for a walk. Other sentences describing a pleasant, sparsely attended park cannot silently become evidence in this target.

| Model | Neither | Support only | Opposition only | Both |
|---|---:|---:|---:|---:|
| Mammoth-1 | 91.16% | 1.75% | 6.64% | 0.45% |
| Karpo 31B | 99.99% | 0.01% | 0.00% | 0.00% |
| GLiDE 27B | 99.85% | 0.03% | 0.10% | 0.01% |

**Mammoth-1:** Neither is a reasonable winner; its opposition alternative may reflect the negative recommendation rather than calm-specific evidence.

**Karpo 31B:** Strong neither respects the target and emotion scope.

**GLiDE 27B:** Strong neither respects the target and emotion scope.

## K04

**Target:** What made this visit extra special was how surprisingly uncrowded it was.

Surprisingly uncrowded is a reported spatial/social condition with a defensible T connection to calm. It is not an explicit report of tranquility. Subsequent comfortable-strolling text cannot replace target evidence.

| Model | Neither | Support only | Opposition only | Both |
|---|---:|---:|---:|---:|
| Mammoth-1 | 2.20% | 97.45% | 0.21% | 0.14% |
| Karpo 31B | 67.79% | 32.11% | 0.05% | 0.06% |
| GLiDE 27B | 12.43% | 87.01% | 0.33% | 0.23% |

**Mammoth-1:** Strong support retains the accepted positive inference, but its 97.45% concentration is not itself validated for this boundary.

**Karpo 31B:** Neither 67.79% versus support 32.11% is stricter than the earlier Gemma/Decider readings. This may exclude the T evidence the project intends to retain; it should not automatically be called a correctness improvement.

**GLiDE 27B:** Support 87.01% retains the T inference while leaving some neither mass. The allocation is plausible without proving its numerical confidence.

## K05

**Target:** If the owner of the chickens sees it, he yells from his home and asks if you are feeding poison to them.

Yelling directed toward visitors can disturb the encountered place experience. The habitual conditional wording and inference from an interaction leave a plausible neither alternative.

| Model | Neither | Support only | Opposition only | Both |
|---|---:|---:|---:|---:|
| Mammoth-1 | 21.25% | 0.31% | 78.08% | 0.36% |
| Karpo 31B | 9.32% | 0.04% | 90.61% | 0.03% |
| GLiDE 27B | 31.54% | 0.31% | 67.75% | 0.40% |

**Mammoth-1:** Opposition 78.08% and neither 21.25% put the uncertainty on relevant alternatives.

**Karpo 31B:** Opposition 90.61% is consistent with the earlier accepted reading, though more committed than the other new models.

**GLiDE 27B:** Opposition 67.75% and neither 31.54% expose the interaction-versus-atmosphere boundary. This is not automatically better calibrated than the more concentrated alternatives.

## K06

**Target:** It’s not closed to the street though so you have to keep an eye on your kids.

The target directly concerns child vigilance near traffic. Neither for calm is reasonable; heightened vigilance can also support a T agitation inference. A safety consequence is not automatically calm opposition.

| Model | Neither | Support only | Opposition only | Both |
|---|---:|---:|---:|---:|
| Mammoth-1 | 84.83% | 0.33% | 14.51% | 0.33% |
| Karpo 31B | 95.83% | 0.05% | 4.10% | 0.02% |
| GLiDE 27B | 98.35% | 0.07% | 1.51% | 0.07% |

**Mammoth-1:** Neither 84.83% and opposition 14.51% leave a meaningful vigilance-related alternative.

**Karpo 31B:** Neither 95.83% strongly separates the safety/vigilance concern from calm. This is a boundary choice, not proof that a T calm inference is impossible.

**GLiDE 27B:** Neither 98.35% makes the same distinction very strongly; the tiny alternative mass has not been empirically validated.

## U01

**Target:** 1/2 of the space was empty to become a dance floor later in the night.

The target describes space reserved for a future dance floor, rather than a present experience of tranquility or disturbance. Preserve its temporal scope.

| Model | Neither | Support only | Opposition only | Both |
|---|---:|---:|---:|---:|
| Mammoth-1 | 78.81% | 8.98% | 4.33% | 7.87% |
| Karpo 31B | 99.84% | 0.09% | 0.05% | 0.01% |
| GLiDE 27B | 97.11% | 1.77% | 0.95% | 0.17% |

**Mammoth-1:** Neither wins, but 8.98% support, 4.33% opposition and 7.87% both allocate notable mass to unsupported directional configurations. Both cannot be used as an uncertainty bucket.

**Karpo 31B:** Strong neither follows the target temporal scope.

**GLiDE 27B:** Strong neither follows the target temporal scope.

## U02

**Target:** The three exhibits on display were quite underwhelming…

Underwhelming exhibits concern content quality and do not establish calm support or opposition.

| Model | Neither | Support only | Opposition only | Both |
|---|---:|---:|---:|---:|
| Mammoth-1 | 97.45% | 0.05% | 2.48% | 0.02% |
| Karpo 31B | 100.00% | 0.00% | 0.00% | 0.00% |
| GLiDE 27B | 99.98% | 0.01% | 0.01% | 0.00% |

**Mammoth-1:** Neither is appropriate. The small opposition component remains a model preference, not observed agitation.

**Karpo 31B:** Strong neither is consistent with separating exhibit quality from atmosphere.

**GLiDE 27B:** Strong neither is consistent with separating exhibit quality from atmosphere.

## U03

**Target:** It is hard to get the sound of the Memorial Drive cars out of your head as they are only a few yards from this park with no real barriers blocking the sound.

The target explicitly reports intrusive traffic sound affecting the visitor at the park, with no effective sound barrier. This is direct calm-related disturbance.

| Model | Neither | Support only | Opposition only | Both |
|---|---:|---:|---:|---:|
| Mammoth-1 | 0.24% | 0.09% | 99.60% | 0.07% |
| Karpo 31B | 0.03% | 0.00% | 99.95% | 0.01% |
| GLiDE 27B | 0.19% | 0.08% | 99.67% | 0.06% |

**Mammoth-1:** Strong opposition is grounded in the text.

**Karpo 31B:** Strong opposition is grounded in the text.

**GLiDE 27B:** Strong opposition is grounded in the text.

## U04

**Target:** This museum is fun for all ages.

Fun for all ages describes enjoyment and suitability rather than tranquility.

| Model | Neither | Support only | Opposition only | Both |
|---|---:|---:|---:|---:|
| Mammoth-1 | 96.00% | 3.76% | 0.19% | 0.05% |
| Karpo 31B | 99.94% | 0.05% | 0.01% | 0.00% |
| GLiDE 27B | 99.70% | 0.21% | 0.07% | 0.01% |

**Mammoth-1:** Neither is appropriate; the modest support alternative should not be treated as observed calm.

**Karpo 31B:** Strong neither respects the emotion-specific boundary.

**GLiDE 27B:** Strong neither respects the emotion-specific boundary.

## U05

**Target:** This station is epic and famous, but not the cleanest.

Fame and imperfect cleanliness do not themselves establish calm or disturbance. Context about a closed toilet cannot become separate target evidence.

| Model | Neither | Support only | Opposition only | Both |
|---|---:|---:|---:|---:|
| Mammoth-1 | 89.09% | 0.43% | 9.74% | 0.75% |
| Karpo 31B | 99.98% | 0.01% | 0.01% | 0.00% |
| GLiDE 27B | 99.82% | 0.04% | 0.12% | 0.02% |

**Mammoth-1:** Neither wins, but opposition receives 9.74%. A calm-specific link for that alternative is absent from the target.

**Karpo 31B:** Strong neither follows the construct and target-scope rules.

**GLiDE 27B:** Strong neither follows the construct and target-scope rules.

## U06

**Target:** Lovely sitting under the fairy lights in a comfy Adirondack chair, while a busker played songs from the 70s.

The lovely seated experience, comfortable chair and music support a defensible ease/relaxation inference without explicitly reporting tranquility. Music and comfort are not automatically calm.

| Model | Neither | Support only | Opposition only | Both |
|---|---:|---:|---:|---:|
| Mammoth-1 | 20.79% | 77.91% | 0.48% | 0.82% |
| Karpo 31B | 60.41% | 39.51% | 0.03% | 0.05% |
| GLiDE 27B | 49.05% | 49.83% | 0.55% | 0.57% |

**Mammoth-1:** Support 77.91% versus neither 20.79% retains the T interpretation with an alternative.

**Karpo 31B:** Neither 60.41% versus support 39.51% is a stricter boundary. Under wording 1, the four-order mean is neither 51.65% versus support 48.26%; one individual order changes winner.

**GLiDE 27B:** Support 49.83% versus neither 49.05% is effectively tied. One original order and two matched-order wording comparisons change winner. A single positive verdict hides this ambiguity.

## Selection limits

The two positive calm examples depend on T inference. This set does not contain a clear explicitly worded positive calm control, and most targets are exclusions. It cannot establish broad positive recall or justify preferring a model simply because it often selects neither. The known wedding case can also fail the separate gate. A clean correction there is diagnostic, not an estimated production accuracy gain.

Karpo and GLiDE are the most useful new finalists from this reading: one is stricter on inferred evidence, the other retains it more readily. Their exact numerical confidence and the training benefit of these soft vectors remain untested.
