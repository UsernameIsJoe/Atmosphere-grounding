#!/usr/bin/env python3
"""Contract tests using verbatim real review text; not model quality evaluation."""
import importlib.util
import pathlib
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("ollama_component1",ROOT/"scripts/stage1a_component1_ollama.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

ORIGINAL="Then the park is enveloped in trees and circulous paths that make you feel like you are being protected and comforted."
def obs(quote):
    return {"claim":"The park is enveloped in trees and paths.","evidence_quote":quote,
     "subject":"park","predicate":"enveloped in","object":"trees and paths","qualifiers":""}

class SourceContract(unittest.TestCase):
    def test_exact_source_spans(self):
        result=mod.validate_extraction({"observations":[obs("the park is enveloped in trees")]},ORIGINAL)
        self.assertEqual(result[0]["quote_match_status"],"exact_unique")
        self.assertEqual(ORIGINAL[result[0]["sentence_offsets"][0]["start"]:result[0]["sentence_offsets"][0]["end"]],"the park is enveloped in trees")
        self.assertFalse(result[0]["source_support_verified"])
    def test_wrong_quote_not_grounded(self):
        result=mod.validate_extraction({"observations":[obs("the park feels safe")]},ORIGINAL)
        self.assertEqual(result[0]["quote_match_status"],"not_in_source")
    def test_verification_must_cover_every_claim(self):
        result=mod.validate_extraction({"observations":[obs("trees"),obs("comforted")]},ORIGINAL)
        with self.assertRaises(ValueError):
            mod.verify_decisions({"decisions":[{"index":0,"verdict":"supported","reason":"source"}]},result)
    def test_valid_verdicts(self):
        result=mod.validate_extraction({"observations":[obs("trees")]},ORIGINAL)
        out=mod.verify_decisions({"decisions":[{"index":0,"verdict":"uncertain","reason":"unclear"}]},result)
        self.assertEqual(out[0]["verdict"],"uncertain")
    def test_invalid_verdict_rejected(self):
        result=mod.validate_extraction({"observations":[obs("trees")]},ORIGINAL)
        with self.assertRaises(ValueError):
            mod.verify_decisions({"decisions":[{"index":0,"verdict":"safe","reason":"emotional"}]},result)
if __name__=="__main__":
    unittest.main()
