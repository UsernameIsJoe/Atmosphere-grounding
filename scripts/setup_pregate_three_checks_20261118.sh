#!/bin/sh
set -eu
python -m pip install --no-cache-dir torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install --no-cache-dir numpy==1.26.4 transformers==4.57.1 fasttext-wheel==0.9.2 datasketch==1.6.5 git+https://github.com/unitaryai/detoxify.git@7ef6576274b91bfc6e06a41f69ad41cc04eaccf1
python -u scripts/stage1a_pregate_three_checks_20261118.py
