#!/usr/bin/env python3
"""Structural regressions for Component 2 v3; no synthetic reviews / model calls."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from stage1a_component2_v3 import EMOTIONS,validate_response,mechanical_audit

SOURCE="Ckean, well kept, and well patrolled by police."
CLAIM={"claim":"The area is well patrolled by police.","status":"candidate_passed_checks"}
def make(place="yes",etype="environmental_social_indicator",safety="indirect"):
 return {"index":0,"place_related":place,"evidence_type":etype,"place_reason":"place description",
   "applicability":[{"emotion":e,"status":safety if e=="safe" else "not_applicable",
     "basis_quote":"well patrolled by police" if e=="safe" and safety in ("direct","indirect") else "",
     "reason":"specific social observation"} for e in EMOTIONS]}
class Tests(unittest.TestCase):
 def test_complete(self):
  self.assertEqual(list(validate_response({"decisions":[make()]},[CLAIM])),[0])
 def test_duplicate_emotions_rejected(self):
  row=make();row["applicability"][1]["emotion"]="safe"
  with self.assertRaises(ValueError):
   validate_response({"decisions":[row]},[CLAIM])
 def test_police_indirect_allowed(self):
  routes,flags=mechanical_audit(make(),CLAIM,SOURCE)
  self.assertEqual(flags,[])
  self.assertEqual(routes["safe"]["route"],"nli_candidate")
 def test_police_direct_flagged(self):
  routes,flags=mechanical_audit(make(safety="direct"),CLAIM,SOURCE)
  self.assertTrue(any("direct_without_explicit" in f for f in flags))
  self.assertEqual(routes["safe"]["route"],"needs_review")
 def test_nonliteral_quote_flagged(self):
  row=make()
  row["applicability"][-1]["basis_quote"]="the reviewer felt safe"
  routes,flags=mechanical_audit(row,CLAIM,SOURCE)
  self.assertTrue(any("no_literal_basis" in f for f in flags))
 def test_unrelated_but_applicable_flagged(self):
  routes,flags=mechanical_audit(make(place="no"),CLAIM,SOURCE)
  self.assertTrue(flags)
  self.assertEqual(routes["safe"]["route"],"needs_review")
 def test_source_fidelity_flagged_independently(self):
  c=dict(CLAIM,status="flagged_not_accepted")
  routes,flags=mechanical_audit(make(),c,SOURCE)
  self.assertTrue(any("component1_claim_flagged" in f for f in flags))
 def test_uncertain_is_distinct_from_not_applicable(self):
  row=make(safety="not_applicable")
  routes,flags=mechanical_audit(row,CLAIM,SOURCE)
  self.assertEqual(routes["safe"]["route"],"not_selected")
  self.assertEqual(flags,[])
if __name__=="__main__":unittest.main()
