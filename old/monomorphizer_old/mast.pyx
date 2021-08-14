"""
The MAST Cython module is a target into which we copy the AST, substituting templates as required.
- MAST node = (AST node + computed properties (TID) - templates)
- simply copy AST nodes while replacing formal arguments with their actual arguments
    - IdInModuleExp is replaced with IdExp
- replace value binding IDs with ValGDefIDs, such that no scoping is required.

Evaluate while/by generating monomorphic IR = MASTICATION (heh heh)
- masticate is a synonym for chewing
- masticate sounds like 'making MAST' by doing work
- this module eats AST one bite at a time

MAST expressions can be evaluated totally using straightforward recursive functions.
- evaluated: used to cache values in a map
- totally: can evaluate arguments before evaluating substitution (since does not rely on previous result, only
  expression)
- when a template module is instantiated, we lazily masticate the module
    - substitute each type BoundVar TID for actual arg TID in the module type
        - TODO: fix typer.inference: ensure correct module type is exported (for type-classes later)
    - emit each element's value using recursive MASTICATION
    - each LambdaExp just returns a FunctionID (that is monomorphically unique)
    - each function call means masticating the called value, masticating the function definition, and then calling it
        - ONLY need to masticate definition eagerly if called
        - ALWAYS DEFAULT TO LAZY MASTICATION (cf initialization order)
    - if we cannot masticate an expression (due to a cycle), RAISE INITIALIZATION ORDER ERROR.
    - defining functions must be performed after defining globals

Thus, MAST construction involves iterative evaluation and lazy monomorphic IR construction such that we are guaranteed
to construct all the monomorphic IR we need.

TODO: add a `Builder` class that allows us to create and reference global template instantiations inside a function
TODO: add a `Value` class that allows us to map values of all data-types for templates efficiently
TODO: write a function to MASTICATE A MODULE-- can masticate all modules into a BOLUS
    - TREE SHAKING by only evaluating entry point and all related dependencies
        - TODO: specify varied entry point interfaces: different apps need different frameworks
            - default is just a hard-coded `TOT main` (no DV => no un-terminated loops => no UI)
        - TODO: write type-classes that apply to modules based on this feature
    - output is a struct-like value containing fields that may be...
        - integers/floats/structs/pointers/mut pointers/... any other static data
        - function pointers (in the form of IDs + optional context ptr unless `NoCtxPtr`)
        - these function pointers can be de-referenced since we allocate them/are just IDs into a table.
    - later, we can emit ALL FUNCTION DEFINITIONS and EACH SUB-MODULE VALUE as a BOLUS
        - function definitions rely on sub-module values for global references
        - globals
    - the BOLUS can then be processed and emitted
"""
