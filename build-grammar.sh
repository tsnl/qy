#!/usr/bin/env bash

java -jar ./dev/antlr-4.9.2-complete.jar ./NativeQyModule.g4 -o ./qcl/parser/gen/ -no-listener -visitor
