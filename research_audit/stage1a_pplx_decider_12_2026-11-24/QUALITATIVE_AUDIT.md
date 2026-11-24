# Qualitative audit of native PPLX-Decider probabilities

November 24, 2026. Current assistant reading, with earlier discussion visible; not blinded and not independent human ground truth. The numeric vectors are actual saved outputs averaged over four semantic-aligned native criteria orders. No new model explanations were generated.

The researcher previously agreed generally with the four Gemma boundary-case readings. That agreement does not supply validated probabilities for this new model. This audit records seven semantically reasonable profiles, one clear attribution mismatch, and four construct-boundary cases.

## K01: Personal wedding-logistics stress

**Target:** It was so stressful but her humanity made everything so much better!

**Native mean:** neither 10.02%, support only 5.13%, opposition only 62.82%, both 22.03%.

**Assistant assessment:** clear attribution mismatch. The target names stress and relief, but the full review attributes them to a late photographer and accommodation of a personal wedding schedule. Neither qualifies as a place-calm judgment under the stated attribution rule. Opposition-only plus both receives 84.85%, so the lower maximum than Gemma does not mean the full distribution handles the error better.

## K02: Dark restroom

**Target:** Lights in the small box were years away- it was completely dark.

**Native mean:** neither 95.44%, support only 0.65%, opposition only 3.70%, both 0.21%.

**Assistant assessment:** semantically reasonable. Darkness in a poorly maintained restroom is not in itself reported tranquility or disturbance. Strong neither is consistent with the calm boundary, without making a safety judgment.

## K03: Walking suitability

**Target:** I wouldn't go here if your looking for walk.

**Native mean:** neither 99.42%, support only 0.17%, opposition only 0.31%, both 0.09%.

**Assistant assessment:** semantically reasonable. The target concerns suitability for a walk. Other sentences mention sparse attendance and a pleasant park, but they cannot silently become evidence in this target. Strong neither is reasonable.

## K04: Uncrowded visit

**Target:** What made this visit extra special was how surprisingly uncrowded it was.

**Native mean:** neither 7.00%, support only 90.76%, opposition only 0.94%, both 1.31%.

**Assistant assessment:** boundary case. Surprisingly uncrowded is a reported spatial/social condition supporting an inferential calm reading, but it is not a direct report of tranquility. Support at 90.76% is defensible only if this T inference is accepted. Subsequent comfortable-strolling text may clarify context but cannot replace the target.

## K05: Owner yelling

**Target:** If the owner of the chickens sees it, he yells from his home and asks if you are feeding poison to them.

**Native mean:** neither 45.59%, support only 0.81%, opposition only 52.81%, both 0.79%.

**Assistant assessment:** boundary case. Yelling directed at visitors can disturb an encountered place experience. The 52.81% opposition versus 45.59% neither split exposes the interaction-versus-place-atmosphere boundary. This is a plausible ambiguity profile, not a measured 53% chance of correctness.

## K06: Street / watching children

**Target:** It’s not closed to the street though so you have to keep an eye on your kids.

**Native mean:** neither 95.47%, support only 0.35%, opposition only 3.87%, both 0.31%.

**Assistant assessment:** boundary case. The target directly concerns children and an open boundary to traffic. Neither for calm is reasonable; heightened vigilance can also support T opposition. A 95.47% neither reading is more decisive than the earlier softened Gemma distribution and does not resolve the construct boundary.

## U01: Future dance floor

**Target:** 1/2 of the space was empty to become a dance floor later in the night.

**Native mean:** neither 88.17%, support only 5.00%, opposition only 5.69%, both 1.14%.

**Assistant assessment:** semantically reasonable. The target describes space reserved for a future dance floor, not present tranquility, disturbance, or a visitor response. Neither is reasonable. Its 88.17% concentration is less strong than several unrelated-content cases but cannot be independently calibrated from this reading.

## U02: Underwhelming exhibits

**Target:** The three exhibits on display were quite underwhelming…

**Native mean:** neither 99.58%, support only 0.09%, opposition only 0.27%, both 0.06%.

**Assistant assessment:** semantically reasonable. Underwhelming exhibits are a content-quality assessment. They do not establish calm opposition or support. Strong neither is appropriate to the target.

## U03: Intrusive traffic noise

**Target:** It is hard to get the sound of the Memorial Drive cars out of your head as they are only a few yards from this park with no real barriers blocking the sound.

**Native mean:** neither 0.78%, support only 0.31%, opposition only 98.64%, both 0.27%.

**Assistant assessment:** semantically reasonable. The target explicitly reports intrusive car sound affecting the visitor at the park and no barriers to that noise. Strong calm opposition is supported by the text, with no need to infer calm from the mere existence of a road.

## U04: Fun for all ages

**Target:** This museum is fun for all ages.

**Native mean:** neither 97.78%, support only 1.19%, opposition only 0.85%, both 0.18%.

**Assistant assessment:** semantically reasonable. Fun for all ages concerns enjoyment and suitability, not tranquility. Strong neither is consistent with separating emotion dimensions.

## U05: Fame / cleanliness

**Target:** This station is epic and famous, but not the cleanest.

**Native mean:** neither 94.98%, support only 0.44%, opposition only 4.17%, both 0.41%.

**Assistant assessment:** semantically reasonable. Fame and imperfect cleanliness do not themselves imply calm or disturbance. Strong neither is reasonable; context complaints about a closed toilet cannot supply new target evidence.

## U06: Comfortable seating / music

**Target:** Lovely sitting under the fairy lights in a comfy Adirondack chair, while a busker played songs from the 70s.

**Native mean:** neither 40.65%, support only 56.42%, opposition only 1.39%, both 1.54%.

**Assistant assessment:** boundary case. The lovely seated experience, comfortable chair and music support a plausible ease/relaxation inference, without explicitly reporting tranquility. The 56.42% support versus 40.65% neither split is semantically plausible. Music and comfort alone are not automatically calm, and these proportions have not been human-validated.
