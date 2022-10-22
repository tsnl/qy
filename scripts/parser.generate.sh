#!/usr/bin/env bash

ANTLR="java -jar ./dev/antlr-4.11.1-complete.jar"
GFILE="./grammars/QySourceFile.g4"

$ANTLR $GFILE -o ./qcl/parser/antlr/ -no-listener -visitor
