#!/usr/bin/env bash

if [ ! -d ".git" ]; then
    echo "$ERROR_HEADER Expected to run this script in the repository root."
    exit 1
fi

source ./scripts/config.sh

source ./scripts/python.setup.sh
source ./scripts/parser.clean.sh
source ./scripts/parser.generate.sh
