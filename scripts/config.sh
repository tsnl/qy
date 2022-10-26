PYTHON="python3.10"
VENV_PATH="venv"

NZEC_WRONG_CWD=1
NZEC_WRONG_PYTHON=2
NZEC_VENV_INSTALL_FAILED=3
NZEC_VENV_CREATE_FAILED=4

ERROR_HEADER="[QY] [ERROR] "
           
type -P $PYTHON 1> /dev/null 2> /dev/null
PYTHON_FIND_EC=$?

if [ $PYTHON_FIND_EC != 0 ]; then
    echo "$ERROR_HEADER Could not find appropriate Python interpreter: $PYTHON."
    echo "              Please ensure such an executable is on PATH or edit 'setup.sh'"
    exit $NZEC_WRONG_PYTHON
fi
