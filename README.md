# Qy v2.1

Qy is a systems programming language that compiles to C++ and consumes C.

## Setup

- Install Python 3.10
- Install a recent version of the Java Runtime Environment (JRE)-- used to build the grammar.
- Run setup

  ```
  $ bash scripts/setup.sh
  ```
  
  For developers, you can also run

  ```
  $ source scripts/setup.sh
  ```

...and that's it, you're all set to run `qc`, the Qy compiler.

NOTE: if you are a Windows user, please use WSL or a Virtual Machine to run `qc`.
Since `qc` is just a C++ code generator (similar to `cfront`), the generated source files can then
be compiled using a Windows compiler.

## Usage

Run `./qc --help` to print help, and go from there (WIP).
