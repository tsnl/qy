# Qy Lang

Qy is a gradually-typed programming, message-based programming language that 
aims to provide the convenience of Python without compromising on control or
performance.

Gradual typing is the union of dynamic and static typing. Variables lacking any
user type specifiers rely on type inference or dynamic typing to be determined.

It is compiled ahead-of-time and can be deployed anywhere that languages like
C, C++, Rust, Swift, or Zig can be deployed.

## Setup

- Install Python 3.9 or PyPy3.9 including the Pip package manager
  - first try `python -m ensurepip`, else need to use OS' package manager.
- Install a recent version of the Java Runtime Environment (JRE)-- used to build 
  the grammar.
- Run setup (requires an internet connection for first-time setup)

  ```
  $ bash scripts/setup.sh
  ```
  
  For developers, you can also run

  ```
  $ source scripts/setup.sh
  ```

...and that's it, you're all set to run `qbt`, the Qy build tool.

NOTE: if you are a Windows user, please use WSL or a Virtual Machine to run `qc`.
Since `qc` is just a C++ code generator (similar to `cfront`), the generated source files can then
be compiled using a Windows compiler.

## Usage

Run `./qc --help` to print help, and go from there (WIP).
