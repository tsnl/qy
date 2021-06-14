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
