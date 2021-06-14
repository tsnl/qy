# The Qy Compiler Specification

This document details how a Qy compiler would behave, thereby specifying the Qy programming language.
In this document, `Qy` refers to the language, while `Qc` refers to the Qy compiler.


### Modules and Projects

Each Qy source file is a stand-alone `module` that other modules may import or that the compiler may use as an 
entry-point to construct a project graph.
Thus, the term 'module' is used to refer to a single source file.

Each module contains zero or more `submodule`s, each defined with a `mod` block.
No submodule may contain another submodule.

Each module may also import other modules using an `import` statement.

The compiler constructs `the project graph` from `an entry-point module` by recursively parsing and extracting all 
imported module file-paths.
- the user passes the entry-point module path to the compiler

NOTE: a module cannot import itself
- the project graph is a true graph, no reflexive edge relations permitted

#### The `$` character in import paths

NOTE: an import path may contain the `$` character, which is substituted for the directory of the entry point,
also known as the **content root directory.**

To help make this obvious, the following file-extensions are followed:
1. All qy modules that are imported have a `.qy` extension.
2. All entry-point qy modules have a `.qy-app` or `.qy-lib` extension

Thus, the `$` character always points to a directory containing a `qy-app` or `qy-lib` extension.

Furthermore, no `*.qy-app` or `*.qy-lib` file can be imported by another `*.qy*` file.
