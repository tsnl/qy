#!/usr/bin/env bash

ANTLR="java -jar ./dev/antlr-4.10.1-complete.jar"
GFILE="./grammars/QySourceFile.g4"

$ANTLR $GFILE -o ./qcl/antlr/ -no-listener -visitor
