# Qy v2.1

Qy is a systems programming language that compiles to C.

It is mostly C with a few extra quality-of-life features, and most importantly, a compiler set up the way I like, so I
can extend it easily.

Conforming to C allows us to transparently interoperate with C code, and code in any other language that interoperates
with C code.

In the future, Qy will be distributed as a Python package named `qy-compiler` such that...
- `qc` can be invoked to run the tool in a directory 