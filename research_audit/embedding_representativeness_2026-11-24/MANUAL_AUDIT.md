# Qualitative inspection of 20 reviews

Assistant inspection of the complete review and all ranked segments, focusing on the highest and lowest Qwen weights. These are qualitative observations, not human gold labels or accuracy estimates. Exact source text and both model weights are in manual_audit_20.json.

| Source review ID | Observation |
|---|---|
| 67 | Two legitimate topics: Qwen slightly favors summer programming; MPNet favors the broad park description. No uniquely correct rank. |
| 181 | A long, disfluent second sentence receives almost the same Qwen weight as a concise place overview. Word count alone does not explain Qwen weights. |
| 166 | Shopping/dining and transport remain close; shopping/dining ranks first in both. |
| 20 | Specific activities and car-free access rank above the longer personal reflection; both models agree. |
| 38 | Park/sprinkler description ranks above generic child suitability; both models agree. |
| 76 | Both rank the opening Harvard-related clause first, although the review is largely about parenting philosophy. Representativeness does not establish gate eligibility. |
| 186 | Qwen ranks the specific MIT architecture statement first; MPNet ranks the travel/exploration statement first. Genuine interpretation difference. |
| 197 | Both favor the broad campus/history introduction. Qwen preserves more weight for buildings/plaques than MPNet. |
| 138 | Venue/music description ranks first and generic grateful reaction last in both. |
| 85 | Qwen almost ties amenities and broad park overview; MPNet favors the overview. All topics remain close. |
| 205 | Named auditorium/designer overview ranks first; the interior-shell fragment ranks last in both. Independent fragments lose reference context. |
| 169 | Study/lounge statement ranks first; “Good luck!” ranks last. Qwen still gives that farewell 13.6%, versus MPNet 6.5%, showing proportional compression. |
| 133 | Qwen favors seating/planting; MPNet favors play equipment. Broadly plausible but no single gold ordering for a multi-topic review. |
| 68 | Broad park introduction ranks first; Qwen puts dog-waste bags second, ahead of the lively basketball/children statement. Topic weight is not atmospheric importance. |
| 137 | Both favor the long event-space overview. Booking/service/secondhand content still needs the separate gate. |
| 80 | Both rank the play-equipment list first. Qwen ranks drinking water last; MPNet ranks shade/mosquitoes last. |
| 51 | Abbreviation splitting produces “John F.”, “Kennedy.” and “President John F.” fragments. Low ranks partly reflect segmentation damage. Fix segmentation before integrating weights. |
| 209 | Both favor the museum introduction. Qwen gives Glass Flowers more weight; MPNet favors broad recommendations. Qwen ranks the size fragment last. |
| 7 | Basketball overview ranks first. Qwen ranks the ambiguous “runs” clause last; MPNet puts the isolated light-hours statement last. Fragment/context sensitivity remains. |
| 40 | Qwen favors playground facilities while MPNet favors the basketball/exercise statement. Qwen weights are close to uniform; “Great park!” retains 18.8%. |

Main observations: broad place overviews often rank high; legitimate multi-topic reviews do not have a unique highest segment; short generic or referential fragments may retain meaningful weight; topic representativeness must stay separate from emotion evidence and gate eligibility. The most concrete next repair is abbreviation-aware segmentation, followed by a paired rerun on the same 100 source IDs.
