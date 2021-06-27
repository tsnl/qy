Rather than `new`, use `make` and `push`, collectively known as `new` statements
- `push` allocates memory on the stack.
- `make` allocates memory using the active heap allocator.
- `push/make` are collectively known as `new` statements and admit the same syntax:
- usage:
    - `make (value)` returns a pointer with value stored
    - `make (value)` returns a pointer with value stored
    - `make mut(value)` returns a mutable pointer with value stored
    - `make mut(value)` returns a mutable pointer with value stored
    - `make [T^n]` returns an array or slice of immutable elements with each element un-initialized
    - `make [T^n](x)` is as above, but also initializes each element with `x :: T`
    - `make mut[T^n]` returns an array or slice with mutable elements with each element un-initialized
    - `make mut[T^n](x)` is as above, but also initializes each element with `x :: T`
    - can replace `make` with `push` in any case above