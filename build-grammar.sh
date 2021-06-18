#!/usr/bin/env bash

ANTLR="java -jar ./dev/antlr-4.9.2-complete.jar"
GFILE="./NativeQyModule.g4"

$ANTLR $GFILE -o ./qcl/antlr/gen/ -no-listener -visitor
