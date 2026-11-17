# E/T codebook v0.6 — place-level attribution

Scope: classify the origin of a FIXED emotion judgment. Emotion, direction, and evidence quotation are supplied and must remain unchanged. E/T classification does not validate the emotion judgment. The v0.5 emotion definitions remain frozen for the separate completion run.

E — Direct place-level experience. The target directly describes how the place or the visit as a whole feels to the reviewer, or directly appraises the place itself in a way expressing the supplied emotional meaning. An explicit emotion adjective is not required. Examples: “I felt relaxed here”; “This place is peaceful”; “A beautiful oasis”; “This place felt unwelcoming.”

T — Inference to place-level experience. The target describes an object, person, affiliate, service, event, activity, process, or condition associated with the place. Connecting that description to the supplied place-level emotion requires inference, even if the subordinate thing is explicitly described emotionally or positively. Examples: “The food was delicious”; “Chelsea was incredible to work with”; “The performance was wonderful”; “Planning the wedding was stress free”; “The staff were friendly.”

Decision procedure:
1. Read the fixed emotion, direction and quote in the target sentence.
2. Identify what the relevant description actually evaluates: the place/overall visit, or a subordinate thing/interaction/process.
3. Choose E only if the relevant emotional appraisal is explicitly about the place or overall experience there. Otherwise choose T. Merely happening at a place does not make a description E.
4. A named place is not required when its referent is clear. “I felt safe here” is E; a threat by an attendant without a stated place-level feeling is T. “The staff made this place feel welcoming” is E because the place-level result is explicit. “The staff were welcoming” is T because the appraisal concerns staff.
5. Classify each supplied claim independently. A sentence may contain E for one claim and T for another. If a quote contains direct place-level support for its supplied emotion, use E even when it also names contributing conditions. Use target text to resolve quote scope; context may resolve references but cannot contribute new evidence.
6. E/T is independent of certainty, emotional polarity, literal cue words, and whether the fixed emotion inference is persuasive. Do not reject, correct, add or delete emotion claims. Generic positive praise of food can receive T for a supplied inviting claim without endorsing the validity of that inviting judgment.

Reporting: model agreement measures consistency, not accuracy. No independent human E/T gold labels are currently established for this cohort. Preserve legacy v0.5 outputs and report changes separately.
