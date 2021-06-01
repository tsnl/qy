ECHO OFF


REM TODO: check if this actually works!

set version = %%"python3 --version"
if "%version:~7,10%" != "3.9"
    ECHO "`python3` must refer to Python3.9. Use a `virtualenv`?"
    EXIT 1

python qc.py