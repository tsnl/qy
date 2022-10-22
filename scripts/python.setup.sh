#!/usr/bin/env bash

$PYTHON -m pip install virtualenv
if [ $? != 0 ]; then
    echo "$ERROR_HEADER failed to install virtualenv. Terminating."
    exit $NZEC_VENV_INSTALL_FAILED
fi

if [ -d "$VENV_PATH" ]; then
    rm -rf "$VENV_PATH"
fi

$PYTHON -m venv "$VENV_PATH"
if [ $? != 0 ]; then
    echo "$ERROR_HEADER failed to create a virtualenv. Terminating."
    exit $NZEC_VENV_CREATE_FAILED
fi

source "$VENV_PATH/bin/activate"

$PYTHON -m pip install -r requirements.txt
