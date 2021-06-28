# Qy

A systems-programming language with a Pythonic feel and seamless C interoperability.

Work in progress. See the `news/` directory for rolling updates.

## Instructions to Use

### Part 1: Setting Up

The following steps only need to be performed once, while setting up.

0.  Ensure you have the following programs/libraries installed:
    - Python 3.9: see `https://python.org` with the PIP package manager
        - if you have Python but not `pip`, you can use the PIP bootstrap file in `dev/get-pip.py`
    - the Java Runtime Environment (JRE)
1.  Run either `build-grammar.bat` on Windows or `build-grammar.sh` on Linux/macOS to generate the grammar.
    - ensure you have the `java` runtime installed.
2.  Run `python3.9 -m pip install -r requirements.txt` to install all Python dependencies
3.  Run `setup.py build_ext --inplace` to build Cython extensions.
    - static evaluation uses these extension modules.
    
### Part 2: Running the compiler

It should suffice to run `qc` in the terminal regardless of your platform.
- on Windows, this should invoke the `qc.bat` batch file.
- on Linux and macOS, this should invoke the `qc` shell script.

Assuming all the above set-up has completed successfully, this should work without a hitch.

If this fails, please ensure the above installation steps succeeded.
