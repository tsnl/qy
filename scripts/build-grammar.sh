#!/usr/bin/env bash

ANTLR="java -jar ./dev/antlr-4.9.2-complete.jar"
GFILE="./grammars/QySourceFile.g4"

$ANTLR $GFILE -o ./qcl/antlr/ -no-listener -visitor
