# Cross-modal matching: research walkthrough

November 19, 2026

**My recommendation is to keep each location as a collection, use your evidence vectors to guide possible links, and combine whole-image and region-level information. Keep several plausible matches—or no match—instead of forcing exact pairs.**

This would combine published methods. Whether that combination improves our emotion model remains something to test.

One clarification: **we can still use CLIP with weakly paired data.** Its pretrained encoders can supply descriptive representations; we do not have to fine-tune it by declaring every same-place segment–photo combination a correct pair. The representation and the pairing objective are separate choices. [^1]

I found a particularly relevant precedent: **Hessel, Lee and Mimno, EMNLP 2019**, *Unsupervised Discovery of Multimodal Links in Multi-image, Multi-sentence Documents*. They learn image–sentence links from collections that share document membership, without individual pair annotations during training. Their setting explicitly includes sentences with several corresponding images or none. **Replacing “document” with “location” gives us a much closer starting point than ordinary caption matching**, although our emotional supervision adds another problem. [^2]

Here is how I would process one location.

**1. Give each segment two distinct roles: describing conditions and supplying emotional evidence.**

Retain:

- Its emotion vector and validity mask.
- Its evidence-category vector.
- The actual descriptive spans, relationships and qualifiers.
- Eligibility, E/T provenance and original review context.

For example, a segment describing shaded seating and expressing calm contains both a **condition we might locate visually** and an **emotional target**.

A segment saying only “I felt calm here” still supplies emotional evidence, but provides little specific content to localize. It can contribute to the place profile without receiving an invented segment–photo match.

**2. Represent each photograph at several scales.**

I would keep these representations together:

| Scale | What it contributes | Where I would use it |
|---|---|---|
| **Whole image** | Layout, enclosure, openness, composition and scene context | Every image |
| **Regions or contextual crops** | Seating, vegetation, entrances, people and their surrounding conditions | Descriptions involving identifiable elements |
| **Segmentation masks** | Area fractions, distributions and spatial measurements | Attributes that require those measurements |

**I would not start by matching emotions to individual pixels.** Pixel-level segmentation is useful for measuring vegetation coverage or visible sky. It does not establish which pixels produced someone’s emotional experience. DenseCLIP provides a precedent for pixel–text matching in dense prediction, rather than evidence that pixel-level emotion attribution is valid. [^3]

There is also a practical distinction between whole-image and local encoders. RegionCLIP demonstrated limitations when applying ordinary CLIP directly to regions; FILIP explicitly trains word–patch correspondence. So we should use a method designed or evaluated for local matching, rather than assume arbitrary CLIP patch vectors work equally well. [^4][^5]

Keep each region attached to its parent photograph and position. Flattening every crop into one location-wide collection would lose relationships.

**3. Use your evidence vectors as guidance, with finer descriptions underneath them.**

Your shared catalogue can help identify which visual measurements and regions deserve attention. But broad category overlap is a weak signal: two images can both contain “nature” while depicting very different conditions.

I would therefore combine:

- Shared category membership.
- Specific entities and attributes.
- Relationships and scene context.

For “seating shaded by trees,” detecting trees somewhere and benches somewhere else is insufficient. We need evidence for their relationship, with enough surrounding image context to assess it.

There is a relevant concept-based precedent: **MASK, ICLR 2026**, connects words and visual-region prototypes to support unpaired image–text matching. It supports the principle of a shared semantic bridge. Its bridge uses externally grounded concepts; it does **not** demonstrate that our broad evidence categories alone will suffice. [^6]

**4. Score possible correspondences before deciding which to retain.**

For a location with $S$ eligible segments and $I$ photographs, construct an $S \times I$ table of descriptive compatibility. Local evidence can refine each entry.

That score should assess whether the photograph depicts the described condition—not whether the photograph already appears “calm” or “safe.”

Initially, I would **rank and retain scores rather than apply an aggressive hard filter**. A low whole-image score could hide a relevant small region.

The correspondence should allow:

| Situation | Permitted result |
|---|---|
| Several photos depict the condition | Several links from one segment |
| One photo supports several descriptions | Several segments link to that photo |
| Available photos do not depict the condition | No match |
| Evidence remains ambiguous | Uncertain links retained for inspection |

Hessel et al. compare dense matching, selective top-$k$ links and assignment-based matching. Their selective approach provides a precedent for leaving material unaligned. Our adaptation should preserve multiple correspondences rather than assume a one-to-one assignment. [^2]

**5. Start with simple selective matching; consider partial optimal transport as a stronger alternative.**

Two options are worth comparing:

| Method | How it works | Main consideration |
|---|---|---|
| **Selective similarity links** | Retain plausible links with weights and an explicit no-match decision | Transparent and easier to audit; acceptance rules need calibration |
| **Partial optimal transport** | Allocates correspondence weights jointly across the two collections while allowing unmatched content | More structured, but its costs and matching constraints introduce additional assumptions |

**OMIT** supplies a concrete partial-matching precedent: it matches visual and textual fragments while using auxiliary “dustbins” to reduce contributions from irrelevant fragments. It was evaluated on image–caption retrieval. Applying that mechanism to location-wide collections would be **our extension**, including decisions about how much material may remain unmatched. [^7]

I would not assume optimal transport is automatically better. A mathematically optimal allocation can still connect semantically incorrect material if its compatibility scores are poor.

**6. Use those links to supervise visual predictions without copying the segment’s score onto every photo.**

A segment’s candidate photographs form a weighted visual collection. Its emotional evidence can supervise a prediction pooled from that collection.

This follows the principle of **multiple-instance learning**: supervision belongs to a collection, while individual-instance labels remain unknown. Attention-based MIL provides a validated mechanism for learning weighted aggregation. Extending its original classification formulation to our emotion vectors would require an appropriate regression or distributional objective. [^8]

I would first establish descriptive matching separately, then train the emotion predictor. That makes it easier to determine whether improvements come from better correspondence or from the emotion model reshaping the matches.

The visual prediction branch must operate without reviews at inference. Individual-image predictions would still need independent image-level evaluation.

**The comparison I would actually run is:**

| Version | What changes | What it tests |
|---|---|---|
| A | Place/category profiles, without segment–photo links | Whether explicit pairing is necessary |
| B | Add whole-image descriptive links | Whether correspondence improves supervision |
| C | Add region evidence while retaining whole scenes | Whether local information adds value |
| D | Replace simple link selection with partial transport | Whether joint allocation improves correspondence |

These are proposed experiments, not established performance rankings. Keep eligibility and place-level splits consistent, and assess both **content-link correctness** and **emotion prediction** using independent judgments.

One further trap: descriptions from different places can legitimately match the same visual conditions. We should therefore inspect any training objective that automatically treats every different-place combination as a negative.

**I would begin with A–C.** Your category structure may already improve supervision without exact pairing; soft correspondence may improve it further; regions should earn their added complexity through the comparison.

[^1]: Radford et al. (2021). [Learning Transferable Visual Models From Natural Language Supervision](https://proceedings.mlr.press/v139/radford21a.html). ICML.
[^2]: Hessel, Lee and Mimno (2019). [Unsupervised Discovery of Multimodal Links in Multi-image, Multi-sentence Documents](https://aclanthology.org/D19-1210/). EMNLP-IJCNLP. [Full paper](https://aclanthology.org/D19-1210.pdf).
[^3]: Rao et al. (2022). [DenseCLIP: Language-Guided Dense Prediction With Context-Aware Prompting](https://openaccess.thecvf.com/content/CVPR2022/html/Rao_DenseCLIP_Language-Guided_Dense_Prediction_With_Context-Aware_Prompting_CVPR_2022_paper.html). CVPR.
[^4]: Zhong et al. (2022). [RegionCLIP: Region-Based Language-Image Pretraining](https://openaccess.thecvf.com/content/CVPR2022/html/Zhong_RegionCLIP_Region-Based_Language-Image_Pretraining_CVPR_2022_paper.html). CVPR.
[^5]: Yao et al. (2022). [FILIP: Fine-grained Interactive Language-Image Pre-Training](https://arxiv.org/abs/2111.07783). ICLR.
[^6]: Yin et al. (2026). [Multimodal Aligned Semantic Knowledge for Unpaired Image-text Matching](https://proceedings.iclr.cc/paper_files/paper/2026/hash/e48fa1c4f08fd1ae35d5df8352c3106d-Abstract-Conference.html). ICLR. [Full paper](https://proceedings.iclr.cc/paper_files/paper/2026/file/e48fa1c4f08fd1ae35d5df8352c3106d-Paper-Conference.pdf).
[^7]: Pan et al. [Learning Image-Text Matching with Optimal Partial Transport](https://arxiv.org/html/2603.14349v1). [arXiv record](https://arxiv.org/abs/2603.14349).
[^8]: Ilse, Tomczak and Welling (2018). [Attention-based Deep Multiple Instance Learning](https://proceedings.mlr.press/v80/ilse18a.html). ICML.
