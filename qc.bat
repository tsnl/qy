@ECHO OFF

REM TODO: check if this actually works!
REM set version = %%"python3 --version"
REM if "%version:~7,10%" != "3.9"
REM     ECHO "`python3` must refer to Python3.9. Use a `virtualenv`?"
REM     EXIT 1

python3.9 qc.py %*
