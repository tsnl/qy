#!/usr/bin/env bash

ROOT_PATH=$(dirname $(realpath $0))

python3.10 "$ROOT_PATH/qc.py" $@

# TODO: for release, switch to `python -O`
# python3.9 -O qc.py $@
