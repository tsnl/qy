# ptc-checks: post-type-check checks

After we've typed the AST, we still need to verify that the input program is valid.

If this were an interpreted language, then each source file could be viewed as a partial definition of a single constant
module expression, i.e. a struct-like object with value and type fields.

In fact, this is the goal of ~~this~~ the `vm` module:
the VM offers a Python-level of efficiency for static evaluation,
mainly because it uses high-level abstractions that can easily be queried for validation.

The key idea is that we traverse the AST to evaluate several constants in each context.

These constants include...
1. dynamic typing information for each value, 
    - e.g. mutability
    - e.g. side-effects specification
2. value arguments for template calls, especially array sizes
3. transitive dependency maps for how each value is initialized
    - e.g. ensuring global variables have a valid initialization order
    - e.g. ensuring use of `:=` in `TOT` blocks only assigns to stack pointers pushed in the frame
    - e.g. ensuring closures are valid for each function
4. minor polish stuff the typer cannot handle but is easy to check, like
    - inferring the side-effects specifier for a lambda based on the RHS (1:1 mapping)
    - ensuring types are finite

Although these constants serve different purposes, the fundamental idea is the same: that we can 'interpret' the module
constant.

## VM

A `Frame` instance mirrors a `Context` object, but also associates identifiers with an optional value.

