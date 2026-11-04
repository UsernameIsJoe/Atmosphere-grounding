import pathlib
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"scripts"))
from stage1a_gts_joint_aste_probe import unique_span,standardize


def test_standardize_source_exact_triplet():
    text="The gardens are beautiful."
    result=standardize(text,[["gardens","beautiful","positive"]])
    assert result[0]["grounded"]
    assert result[0]["aspect"]["start"]==4


def test_repeated_text_flagged_not_fabricated():
    result=standardize("park and park are beautiful",
                       [["park","beautiful","positive"]])
    assert not result[0]["grounded"]
    assert result[0]["aspect"]["status"]=="ambiguous"


def test_parser_rejects_malformed_predictions():
    try:
        standardize("park is nice",[{"park":"nice"}])
        raise AssertionError("Did not reject malformed prediction")
    except ValueError:
        pass
