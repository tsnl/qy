# 002 - Slices, Arrays, Pointers

Jun 2, 2021

While thinking about arrays and slices, I realized they had to support `mut` element types, just like pointers.
This got me thinking... it is no accident that C allows pointers to be used as arrays.
In essence, a pointer is a **window into a contiguous segment of memory.**

Since our language enforces SSA anyway, what if we took another page out of LLVM and 
**treated the stack as a separate allocator?**
- assume all `alloca` are redirected to a parallel stack.
- two ||el stacks isomorphic to one interleaved stack.
    - the isomorphism simply concatenates the contents of parallel frames and pushes/pops them at once
- so we can do function calls on a stack while requiring the user to explicitly `alloca` data.

## Memory Views

A memory view is a length-bound pointer into memory.

This length is constant for each memory view value instance, but we can use polymorphism within the compiler to
encompass...
- arrays (ptr + const length), and
- ~~pointers (array with length 1), and~~ 
- slices (array of any length)

A few crucial observations:
- ~~pointers are just arrays of length 1~~
  - how do we access elements within arrays and slices without pointers?
  - we still need pointers to express load/store operations 
- arrays have constant length, while slices have dynamic length


The unified syntax to type this is...
- `[T, n]` for arrays-- `mut[T, n]` for mutable access
- `[T, ?]` for slices-- `mut[T, ?]` for mutable access
- `[T]` for pointers-- `mut[T]` for mutable access
    - ~~just sugar over `[T^1]` and `mut[T^1]` resp.~~
    - ~~this language does not support first-class pointers... spooky?~~
        - too spooky: no way to load from an array at index as well as set to a pointer without overloading/refs
    - only pointers support `*` to de-reference, but there is no `get-pointer-to` syntax.
        - `int const* x = &42` in C++ would be replaced by `x = new(42)`
        - this is because `&` in C++ uses the fact that memory for the argument is stored on the stack or data segment 
          first

When the program begins execution, it has no memory views.
A program may acquire a memory view from an allocator or any function.

Use the built-in `new <memory-view-constructor>` allocator to allocate memory.
- memory-view-constructor ALWAYS has a length component:
    - if `?`, an error, since we need to know how much space to allocate
    - if constant, return type is an array.
    - if dynamic, return type is a slice.
    - note array -> slice is OK, but slice -> array cannot be done except by user memcpy/assert.
- what about pointers? **instead of mem-view-ctor, pass parenthesized contents** 
    - may still accept `mut` prefix
- we can later allow the user to `use` an allocator exhibiting a certain interface for a certain scope.
    - different functions with more verbose names can implement array and slice allocation cases
    - this is one of the rare cases where operator overloading is very useful universally
- summary of `new`:
    - `new (value)` returns a pointer with value stored
    - `new mut(value)` returns a mutable pointer with value stored
    - `new[T^n]` returns an array or slice of immutable elements with each element un-initialized
    - `new[T^n](x)` is as above, but also initializes each element with `x :: T`
    - `new mut[T^n]` returns an array or slice with mutable elements with each element un-initialized
    - `new mut[T^n](x)` is as above, but also initializes each element with `x :: T`

Finally, `array[index]` and `slice[index]` return pointers.

Note that every allocator simply returns a slice. This means there is no way to allocate a pointer.
This is intentional.

```
mod print_fib {
    print_until = (n) -> {
        fibonacci_table :: mut[UInt64, ?];
        fibonacci_table = new mut[UInt64, n];
        if n > 0 {
            print_int(0);
            print_newline();
        };
        if n > 1 {
            print_int(1);
            print_newline();
        };
        if n > 2 {
            fibonacci_table[0] := 0;
            fibonacci_table[1] := 1;
            for (i = new mut(2); *i < n; i := *i + 1) {
                x0 = *fibonacci_table[i-1];
                x1 = *fibonacci_table[i-2];
                sum = x0 + x1;
                fibonacci_table[i] := sum;
                
                print_int(sum);
                print_newline();
            };
        };
        0
    };
};
```

Note that further iterations can support **array literals as sugar over `new`, `a[i]`, and `:=`**
- this means that only the array and pointer allocating `new` variants can be called outside function definitions.
- in fact, it should be impossible to use the slice-allocator at a module-top-level scope since no dynamic variables 
  should be bound.
- the usual initialization-order checks will need to be performed
    - but this may mean a more granular initialization order. Ooh?

```
mod primes {
    cached_primes = [2, 3, 5, 7, 11, 13, 17, 19];
};
```

Finally, recall that templates use `<...>` calls.

```
mod vec <T, dim> {
    Vec = [T, dim];
    MutVec = mut[T, dim]; 
}; 
```
---

Applied changes to array syntax.

TODO: add `new`
- removed '^' and '^mut'