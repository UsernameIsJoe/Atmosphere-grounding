#!/usr/bin/env python3
"""Joint GTS-BERT ASTE challenger on the EXACT original M1 controlled cases.

Hugging Face checkpoint is trained on laptop/restaurant reviews. External
checkpoint's custom decoder is used per its model card and run in isolated CI.
All raw predictions and source-alignment ambiguities are retained.
"""
import argparse
import json
import re
import sys
from pathlib import Path

MODEL = "gauneg/bert-gts-absa-triple"


def make_predictor():
    import torch
    from huggingface_hub import hf_hub_download
    from transformers import AutoTokenizer
    torch.set_num_threads(min(4, torch.get_num_threads()))
    model_source = hf_hub_download(repo_id=MODEL, filename="bert_opinion.py")
    decoder_source = hf_hub_download(repo_id=MODEL, filename="post.py")
    sys.path.insert(0, str(Path(model_source).parent))
    sys.path.insert(0, str(Path(decoder_source).parent))
    from bert_opinion import BertGTSOpinionTriple
    from post import DecodeAndEvaluate
    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    model = BertGTSOpinionTriple.from_pretrained(MODEL).eval()
    decode = DecodeAndEvaluate(tokenizer)

    def predict(text):
        # Decoder supplied by checkpoint author, so return raw outputs for audit.
        with torch.inference_mode():
            return decode.decode_predict_string_one(text, model, max_len=128)
    return predict


def unique_span(text, phrase):
    # GTS tokenizer sometimes inserts whitespace before source punctuation,
    # e.g. "not quiet ;" vs. "not quiet;". Canonicalize only that artifact.
    # The returned text and offsets ALWAYS refer to the literal original review.
    canonical = re.sub(r"\s+([,;:.!?])", r"\1", phrase.strip())
    matches = [(m.start(), m.end()) for m in re.finditer(re.escape(canonical), text, re.I)]
    if len(matches) != 1:
        return {"text":phrase, "start":None, "end":None,
                "status":"missing" if not matches else "ambiguous"}
    a,b=matches[0]
    return {"text":text[a:b], "start":a, "end":b,
            "status":"normalized_punctuation" if canonical != phrase.strip() else "unique"}


def standardize(text, raw):
    output=[]
    if not isinstance(raw, (list, tuple)):
        raise ValueError("Unexpected GTS output type "+str(type(raw)))
    for triple in raw:
        if not isinstance(triple, (list, tuple)) or len(triple)<3:
            raise ValueError("Unexpected GTS triplet "+repr(triple))
        aspect,opinion,polarity = triple[:3]
        if not all(isinstance(x,str) for x in (aspect,opinion,polarity)):
            raise ValueError("Non-string GTS aspect/opinion/polarity "+repr(triple))
        a,o=unique_span(text,aspect),unique_span(text,opinion)
        output.append({
            "aspect":a,"opinion":o,"polarity":polarity,
            "method":"gts_bert_joint_aste",
            "grounded":a["status"] in ("unique", "normalized_punctuation") and o["status"] in ("unique", "normalized_punctuation"),
            "raw":triple,
        })
    return output


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",required=True)
    parser.add_argument("--real-reviews",action="store_true",help="Use previously frozen 20 real-review JSONL cases")
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    if args.real_reviews:
        cases=[json.loads(s) for s in Path(args.input).read_text(encoding="utf-8").splitlines() if s]
        assert len(cases)==20
    else:
        cases=json.loads(Path(args.input).read_text(encoding="utf-8"))
        assert len(cases)==8
    predict=make_predictor()
    out=[]
    for c in cases:
        source=c["review"] if args.real_reviews else c["text"]
        raw=predict(source)
        relations=standardize(source,raw)
        entry={"extraction":{"relations":relations,"raw":raw,
                             "parse_status":"gts_checkpoint_decoder"}}
        if args.real_reviews:
            entry.update({"row":c["row"],"place_id":c["place_id"],"review":source})
        else:
            entry.update({"id":c["id"],"text":source})
        out.append(entry)
        print(c["row"] if args.real_reviews else c["id"],"generated",len(relations),"grounded",
              sum(r["grounded"] for r in relations),flush=True)
    target=Path(args.output)
    target.parent.mkdir(parents=True,exist_ok=True)
    if args.real_reviews:
        target.write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in out),encoding="utf-8")
    else:
        target.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")


if __name__=="__main__":
    main()
