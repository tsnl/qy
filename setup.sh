#!/usr/bin/env bash

# pushd qcl/vm/ || exit 1
# python3.9 setup.py build_ext --inplace
# popd || exit 1

pushd qcl/monomorphizer/ || exit 1
python3.9 setup.py build_ext --inplace
popd || exit 1
