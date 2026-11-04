import pathlib
import sys
from types import SimpleNamespace
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"scripts"))
from stage1a_relation_pilot import parse_triplets, locate, make_relation, select_pilot, SYNTHETIC

def test_parse_json_array_and_dict():
    assert parse_triplets('[["gardens","beautiful","positive"]]')[0]==[("gardens","beautiful","positive")]
    assert parse_triplets('{"triplets":[{"aspect":"traffic","opinion":"loud","sentiment":"negative"}]}')[0]==[("traffic","loud","negative")]

def test_bad_generation_does_not_create_relations():
    assert parse_triplets("maybe trees are nice")[0]==[]
    assert parse_triplets('{"label":"positive"}')[0]==[]

def test_source_unique_offsets():
    r=make_relation("The trees are beautiful.","trees","beautiful","positive","mock")
    assert r["grounded"]
    assert r["aspect"]["start"]==4
    assert r["opinion"]["text"]=="beautiful"

def test_repeated_source_unverified():
    r=make_relation("trees and trees are beautiful","trees","beautiful","positive","mock")
    assert not r["grounded"]
    assert r["aspect"]["status"]=="ambiguous_multiple_occurrences"

def test_missing_source_not_fabricated():
    r=make_relation("The trees are nice","garden","beautiful","positive","mock")
    assert not r["grounded"]
    assert r["aspect"]["start"] is None

def test_prespecified_pilot_consistency():
    rows=[{"place_id":f"p{i%43}","text":"An example "+("long "*i)} for i in range(214)]
    a=select_pilot(rows)
    assert a==select_pilot(rows)
    assert len(a)==20 and len(set(a))==20
    assert {55,74,97,113,123,139,181,187}.issubset(a)

def test_fixed_control_suite():
    assert len(SYNTHETIC)==8

def test_model_card_colon_output():
    triples,status=parse_triplets('garden:beautiful:positive\ntraffic:loud:negative')
    assert status=='parsed_colon_triplets'
    assert triples==[('garden','beautiful','positive'),('traffic','loud','negative')]
