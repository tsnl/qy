# Modules

_Below is a sequential outline of how each module transforms text files into executables._

The `frontend` module turns file paths into data-structures that conveniently describe the contents of files
as well as dependencies.

- `frontend` loads source files, handling lexing, parsing, and constructing the AST.
    - it uses the `antlr` model, which also contains generated code using the grammar
    - e.g. code -> AST

The following modules help model propositions as we analyze code loaded via the front-end:

- `ast` contains classes to instantiate an abstract syntax tree.
    - it is useful to identify the location (in line, column coordinates) of parts of source code.
- `type` helps write strings that specify types
    - each type is just an integer ID
    - every type can be spelled using the `spelling` submodule.

After the `frontend` module, we run the `typer` to build `typer.context.Context` instances that
map identifier names based on the `ast` to types, expressed using `type`.

- `typer` helps solve type systems using typing rules & judgements.
    - two sub-passes: `seeding`, then `inference`
    - uses type substitution to determine the types of everything in code
    - uses `context` objects to map value and type ID names to `scheme`s.
        - each `scheme` is a polymorphic mapping to other type IDs

Once we have a typed AST, we use an interpreter to evaluate constants.

- `interpretation` handles evaluation of constants and lowering of the AST to a register-VM IR
    - this is achieved by emitting byte-code for a low-level register VM
    - the typed AST is compiled into IR, during which we detect...
        - mutability errors
        - invalid initialization orders
        - infinite types/invalid mutability specifiers
        - or anything else that may prevent us from lowering the typed AST to an ASM-like format
    - this IR can also be executed at compile-time
        - use lazy compilation to bake templates as required using constants evaluated so far.
        - after evaluating every template value argument, the cache is complete for the program and finite.
    