#!/usr/bin/env bash

./qc eg/matmul/matmul.qyp.jsonc && \
pushd build && \
    cmake ../qc-build/ && \
    cmake --build . && \
popd && \
echo -e "=== Run ===" && ./build/matmul
