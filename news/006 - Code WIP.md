Jun 25

After a brief break, I implemented...
1. typing chain expressions
2. typing chain elements
    - should also validate initialization
3. an `IdTypeSpecInModule` class (that was missing in `ast.node`)
4. an empty `post_typer_basic_checks` module

WIP:
1. typing `IdTypeSpecInModule`
    - also review typing for `IdExpInModule` and factor
2. `post_typer_basic_checks` (the next pass in compilation)
    - need to check initialization orders, at least for global variables
    - need to verify mutability
    - need to verify/prove side-effects-specifiers
    - TODO: consider a different function signature for functions without closure args.
        - such a signature could be wrapped in a `NoClosures{...}` block
        - such signatures allow us to inter-operate with C code. 
        - we must try to aggressively optimize non-`NoClosure` pointers down wherever relevant.
        - lambdas and currying are vital, so no harm in embracing the closure case as default.

---

Jun ??

- Implemented the parser
    - note it is re-entrant
    - note we expect it to cache parse trees
    - we catch ANTLR errors and generate a `ParserCompilationError`
      - see: https://stackoverflow.com/questions/32224980/python-2-7-antlr4-make-antlr-throw-exceptions-on-invalid-input
      - subclassing the exception type may work well
      - investigate using `antlr4.error.ErrorStrategy.ErrorStrategy` instead.

- Implemented the dependency dispatcher
    - todo: post feedback using the feedback mechanism
    
- TODO: intercept `CompilationError` instances and report once feedback is ready.

---
