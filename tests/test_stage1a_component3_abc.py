#!/usr/bin/env python3
"""No-LLM contract tests using real user pilot artifacts when available."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from stage1a_component3_abc import (
    HYPOTHESES, evidence_result, source_key, EMOTIONS)

class TestAblation(unittest.TestCase):
    def test_fixed_hypotheses(self):
        self.assertEqual(set(HYPOTHESES),{"calm","inviting","safe"})
        self.assertIn("physically safe",HYPOTHESES["safe"])

    def test_source_key(self):
        self.assertEqual(source_key({"row":55,"sentence_index":2}),(55,2))

    def test_no_selected_evidence_not_neutral(self):
        value=evidence_result([])
        self.assertEqual(value["evidence_status"],"no_selected_evidence")
        self.assertNotIn("label",value)

    def test_mixed_evidence_preserved(self):
        examples=[{"prediction":{"label":"entailment"}},
                  {"prediction":{"label":"contradiction"}}]
        value=evidence_result(examples)
        self.assertTrue(value["mixed"])
        self.assertTrue(value["any_entailment"])
        self.assertTrue(value["any_contradiction"])

if __name__=="__main__": unittest.main()
