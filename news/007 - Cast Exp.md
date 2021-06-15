Jun 14, 2021

I realized we do not need a bespoke 'struct' constructor expression.

Structs can be cast from tuples, so a general cast expression is more useful.

I settled on admitting a type specifier prefix for any expressions wrapped with `{}` or `()`. 
- the `{...}` expression always refers to a chain
- the `(...)` expression can be unit, identity, or tuple
- a type specifier can be used like a function before either such `wrappedExp` to perform a cast.
    - so a type-spec can be used 'as a function' that converts any data-type to the specified type in a way that will 
      succeed or fail at compile-time.
- NOTE: chains uniquely admit an optional effects specifier, so
  - this is allowed:
    
    ```
    Tot Vec3f {(1, 2, 3)}
    ```
    
  - but this is not:
    
    ```
    Tot Vec3f (1, 2, 3)
    ```

    - `Tot` can only be supplied for chains
    