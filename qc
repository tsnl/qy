#!/usr/bin/env sh

SCRIPT_PATH=$(realpath $0)
SCRIPT_DIR_PATH=$(dirname $SCRIPT_PATH)

python3.9 $SCRIPT_DIR_PATH/qc.py $@

# TODO: for release, switch to `python -O`
# python3.9 -O qc.py $@
