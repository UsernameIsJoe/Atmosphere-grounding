"""Regression test: ABSA extraction must not pass unsupported pipeline kwargs."""
import importlib.util
from pathlib import Path

def test_absa_pipeline_call_uses_supported_signature():
    path = Path(__file__).resolve().parents[1] / "scripts" / "stage1a_compare_abc.py"
    spec = importlib.util.spec_from_file_location("stage1a_compare_abc", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    seen = []
    def fake_extractor(text, **kwargs):
        seen.append((text, kwargs))
        return [{"start": 9, "end": 14, "entity_group": "POS", "score": 0.98}]
    result = module.extract_absa(fake_extractor, "The park feels calm.")
    assert seen == [("The park feels calm.", {})]
    assert len(result) == 1
    assert result[0]["sentence"] == "The park feels calm."
