#!/usr/bin/env bash

pushd qcl/interpretation/ || exit 1
python3.9 setup.py build_ext --inplace
popd || exit 1
