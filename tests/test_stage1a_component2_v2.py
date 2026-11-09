#!/usr/bin/env python3
"""Structural regression tests on genuine historical review text; no model calls."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from stage1a_component2_v2 import validate_response,check_and_handoff,PILOT_EMOTIONS

SENTENCE="A charming and cozy park that is nestled in the heart of Cambridge.  "
CLAIMS=[{"claim":"The park is charming and cozy"}]

def row(eligibility="yes",status="indirect",quote="charming and cozy"):
    return {"index":0,"place_related":eligibility,"place_reason":"describes park",
            "applicability":[{"emotion":e,"status":status,
              "basis_quote":quote if status in ("direct","indirect") else "",
              "reason":"test structure"} for e in PILOT_EMOTIONS]}

class TestContract(unittest.TestCase):
    def test_complete_decisions(self):
        actual=validate_response({"decisions":[row()]},CLAIMS,SENTENCE)
        self.assertEqual(set(actual),{0})

    def test_missing_target_rejected(self):
        r=row();r["applicability"].pop()
        with self.assertRaises(ValueError):
            validate_response({"decisions":[r]},CLAIMS,SENTENCE)

    def test_place_related_indirect_routes(self):
        handoff,flags=check_and_handoff(row(),SENTENCE)
        self.assertEqual(flags,[])
        self.assertTrue(all(v["route"]=="nli_candidate" for v in handoff.values()))

    def test_ineligible_relevant_flags_not_deleted(self):
        handoff,flags=check_and_handoff(row(eligibility="no"),SENTENCE)
        self.assertTrue(flags)
        self.assertTrue(all(v["route"]=="needs_review" for v in handoff.values()))

    def test_missing_quote_flags(self):
        handoff,flags=check_and_handoff(row(quote="winding paths"),SENTENCE)
        self.assertTrue(flags)
        self.assertEqual(handoff["calm"]["route"],"needs_review")

    def test_uncertain_place_prevents_confident_routing(self):
        handoff,flags=check_and_handoff(row(eligibility="uncertain"),SENTENCE)
        self.assertTrue(flags)
        self.assertEqual(handoff["safe"]["route"],"needs_review")

    def test_unrelated_not_applicable_not_selected(self):
        handoff,flags=check_and_handoff(row(eligibility="no",status="not_applicable"),SENTENCE)
        self.assertFalse(flags)
        self.assertEqual(handoff["safe"]["route"],"not_selected")

if __name__=="__main__":unittest.main()
