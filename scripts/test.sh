#!/usr/bin/env bash

if [ ! -d ".git" ]; then
    echo "$ERROR_HEADER Expected to run this script in the repository root."
    exit $NZEC_WRONG_CWD
fi

python3.10 -m unittest discover -s test -p *_test.py
