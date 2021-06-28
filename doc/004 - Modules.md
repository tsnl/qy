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

(everything below WIP)

The following modules help us represent transformed forms of the typed AST.

- `hlir` = high-level IR
    - goal: polymorphic IR suitable for static evaluation, const branch elimination before template generation
    - represents code in an executable/interpretable format
    - capable of executing polymorphic code
    - written in Cython
- `mlir` = mid-level IR
    - goal: template-expanded form suitable for SMT analysis, optimization
    - written in pure Python: does not need to be interpreted
    
The following modules help us generate `hlir`, then `llvm-ir` modules.
- `hlir_compiler` = turns a typed AST into HLIR
    - we can check side-effects-specifier validity inductively here.
    - we can check initialization order, mutability here.
    - if code is valid, we can emit high-level IR. Otherwise, due to above errors, compilation may fail.
- `hlir_static_eval` = evaluates expressions in HLIR to expand templates
    - this is where all compile-time evaluation occurs
    - only errors when exceptions raised during static evaluation, which we cannot guarantee against.
- `mlir_compiler` = turns an HLIR module into an MLIR module
    - mainly involves (1) expanding templates, and (2) dead-code elimination
- `mlir_analysis` = checks an MLIR module using the `z3` library.
- `llir_compiler` = turns an MLIR module into an LLVM IR module using the `llvm` library.
