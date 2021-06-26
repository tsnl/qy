Jun 25 (Part II)

Our strategy of looking up contexts using seeded IDs is highly flawed.
Consider the following example we've been using:

```
mod basic_linalg [T] {
    Vec2 = Struct {
        x :: T;
        y :: T;
    };
};
mod linalg {
    Vec2f = basic_linalg[Float32]:Vec2;
    Vec2i = basic_linalg[Int32]:Vec2;
};
```

The issue above was that both `Vec2f` and `Vec2i` were typed as
`Struct {x :: Int32, y :: Int32}`, as well as `Vec2` in `basic_linalg`!

Clearly, our substitution of `T` cannot be global, otherwise we will rewrite
bound definitions of it too.

The issue is that types don't really understand ALL the variables bound at a context,
and cannot instantiate 'everything'.

This can be fixed in a couple of ways: see `inference.py` (WIP).

---

Jun 25 (Part I)

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
        - such a signature could be wrapped in a `CFn{...}` block
        - such signatures allow us to inter-operate with C code. 
        - we must try to aggressively optimize non-`CFn` pointers down wherever relevant.
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
