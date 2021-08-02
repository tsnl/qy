# Monomorphizer

This module substitutes constant values and types in polymorphic sub-modules,
producing a monomorphic AST (mast).

Note that this produces considerable bloat. 
Reckless allocation can significantly degrade performance.
We would like to allocate our AST nodes as tightly together as possible.
Thus, on each subsequent pass, the CPU caches a few streams of memory in a 
linear-scan fashion.

Note that this requires incrementally evaluating constants in the program.
This is because we would like to generate new monomorphs of polymorphic modules
only when required. 
Thus, we must evaluate compile-time constants used as template arguments to
cache and substitute.

Since Python is a poor fit for the above two tasks, the bulk of this 
functionality is implemented in C++.

Cython wrappers (for Python) are provided to...
1. initiate copying (cf `copier.pyx`) with substitutions applied
2. query results (cf `mast.pyx`) once output is generated

## What is `extension`?

Since the monomorphizer requires a lot of brute-force compute and benefits from
low-level memory management, we would like to write it in C++.

The `extension` subdirectory contains this C++ source code, and handles
a lowered version of the Python AST, already checked for correctness.

This C++ code is **then built into a library called `ExtensionLib`** that is
then dynamically linked against each wrapper.

This ensures that only one copy of the extension is resident in memory at once,
and prevents odd behavior when global variables are cloned.