# Qy v2.1

Qy is a systems programming language that compiles to C++ and consumes C.

## Setup

- Install Python 3.9
- Install a recent version of the Java Runtime Environment (JRE)-- used to build the grammar.
- Install Python dependencies
    ```
    $ python3 -m pip install -r requirements.txt
    ```
- Build parser from grammar (requires Java)
    ```
    $ ./scripts/build-grammar.sh
    ```
  
...and that's it, you're all set.

## Usage

Run `./qc --help` to print help, and go from there (WIP).
