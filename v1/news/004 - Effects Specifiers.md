# May 11, 2021

I finally have a large chunk of time to devote to this project (~10 days).

The `Pandemonium` project (which came before Astropod) highlighted a problem with C interop: how do we track 
side-effects?

The answer lies in Haskell's treatment of mutation:
- even if we don't opt for lazy evaluation, we can borrow the concept of an `IO` monad.
- only functions may return `IO`-qualified types. Such mutating functions must be called with a `!` between func and 
  args, e.g. `set_position!(1, 2)`
    - the `!` can be thought of as applying the side-effects of an `IO` monad
    - calling a function that returns `IO` without a `!` results in a compile-time error
    - curried functions would always apply effects last.
- we can model this using `pure/impure {...}` chain specifiers
    - each chain may admit a `pure` or `impure` keyword specifier that controls mutability in the chain and determines
      return type.
    - `pure` chains do not permit any assignment to memory pushed outside this chain
        - that includes pointers in-scope from an outer pure chain
        - thus, must `push` inside a chain to set this memory
    - `impure` chains allow assignment willy-nilly
    - if a specifier is absent, default to `pure`
    - we can change this so `pure` is the default, and we need `mut` to enable mutation.
- **thus, each pure scope limits mutability to within that scope**
- **thus, each external function can be annotated for mutability**
    - once we can annotate function signatures with side-effects,
    - we can map external symbols to in-language symbols with the appropriate type specified by the user in a wrapper.
    - this type information can then be used 'at face value', or, in the future, verified.

We can further expand the `IO` monad into different monads depending on their type of side-effect.
- E.g. F-star uses 4 such monads: 
- E.g. can have a different monad for system calls and for memory, such that some re-ordering and insight into 
  performance is possible.
- How do these monads compose together?

Compare from F-star:
- see: https://fstar-lang.org/tutorial/tutorial.html#sec-access-control
  
  ```
  (...) in F*, we infer (canRead "foo.txt" : Tot bool). This indicates 
  that canRead "foo.txt" is a pure total expression, which always evaluates 
  to a boolean. 
  For that matter, any expression that is inferred to have type-and-effect Tot t, 
  is guaranteed (provided the computer has enough resources) to evaluate to a t-typed
  result, without entering an infinite loop; reading or writing the program's state; 
  throwing exceptions; performing input or output; or, having any other effect whatsoever.

  On the other hand, an expression like (read "foo.txt") is inferred to have 
  type-and-effect ML string, meaning that this term may have arbitrary effects (it may 
  loop, do IO, throw exceptions, mutate the heap, etc.), but if it returns, it always returns a 
  string. 
  The effect name ML is chosen to represent the default, implicit effect in all ML programs.

  Tot and ML are just two of the possible effects. Some others include:
  - Dv, the effect of a computation that may diverge;
  - ST, the effect of a computation that may diverge, read, write or allocate new references 
    in the heap;
  - Exn, the effect of a computation that may diverge or raise an exception.
  ```

  ```
  The primitive effects {Tot, Dv, ST, Exn, ML} are arranged in a lattice, 
  with Tot at the bottom (less than all the others), ML at the top (greater 
  than all the others), and with ST unrelated to Exn. This means that a 
  computation with a particular effect can be treated as having any other 
  effect that is greater than it in the effect ordering—we call this feature 
  sub-effecting.
  ```
- F-star further allows defining one's own effects, but I think this is already bordering on
  impossible for me.
  
- We can ~~steal~~ learn from this effects-lattice system:
- `TOT < DV < {ST, EXN} < ML`
  - what if we used these as keywords to denote type monads
  - need to bundle constructor and chain together
        - e.g. `Int32{0}`
  - can then allow user to drop type specifier in favor of just effects monad keyword
- need to make this keyword or type-spec mandatory for chains...
    - defaulting to `TOT` seems smart.
    - so the keyword `TOT` is optional...
    - still, force type specifiers to include it
- these names are hard to beat (so concise, so precise).
  - `PURE` is worse than `TOT`
  - `UNSAFE` is worse than `ML`

```
mod tfae {
    hello1 = (x, y) -> {x + y};
    hello2 = (x, y) -> TOT {x + y};
    hello3 = (x, y) -> Int32 {x + y};
    hello4 = (x, y) -> TOT Int32 {x + y};

    hello1 :: (Int32, Int32) -> TOT Int32;
    hello2 :: (Int32, Int32) -> TOT Int32;
    hello3 :: (Int32, Int32) -> Int32;
    hello4 :: (Int32, Int32) -> Int32;
};
mod boop {
    it = () -> TOT mut[Int32] {
        # return a pointer without diverging, causing any side-effects, or raising a run-time exception.
        # e.g. a global variable         
    };
};
```

- we can perform checks on the scope at the top of the stack while typing
  - so effects specifiers apply to chains
  - different expressions evaluated in a chain affect the chain's effects
  - the chain's effect must be checked against a parent chain/context
- we then combine the effects-specifier with the data-type returned to obtain the chain's return type
- any function with non-`TOT` return effect must be invoked using `!`
- when a chain gets evaluated within another chain and outside a function, it is like an IIFE, but does not need `!`,
  only a compliant parent chain.

This scheme excellently complements the `new` statements `push/make`.
- `push/make` and `:=` expressions interact with the top-most effects specifier
    - `push` is okay in `TOT` blocks, but `make` is not
    - closures of pointers ~~must be carefully used~~ can be carelessly used in nested `TOT` blocks
      - consider a pushed pointer, enclosed in a lambda that is returned.
      - our escape-analysis should rule this out as a compiler error
      - but in general, should be OK as long as no assignments
- **note: the effects-specifier never needs to be inferred, only checked, for nested expressions**
  - i.e., for each chain, we know what the effects-specifier is while handling each expression within
  - so, we just check if the effects-specifier allows the specified behavior
  - checking for divergence must be handled after the typer, but we can then use this to 'validate'
  - we do not need to defer information and perform checks later

This scheme lets us add compile-time-checked exceptions in the future.
- since exceptions can be faster than branching for uncommon paths,
- this could enable a whole class of optimizations by the programmer
- statistical analysis can encourage conversion of if/match into exceptions

IMPLEMENTATION

**In practice, we can view effects-specifiers as a property of the function type.**
This is because an effects-specifier can be used either to qualify a lambda's return or within a chain to qualify a 
sub-chain.
When used within a sub-chain, the effect-specifier is validated against the parent chain's effect-specifier, 
**just like an assignment expression, an allocator, or a throw statement**. 
Thus, in correct code, the most general effects-specifier bubbles up inductively to the function return type.
Upon execution, the function upholds the specified effects until it returns.

PROPOSED CHANGES:
1. merge constructor and chain statements, and allow the user to only write the effects-specifier without a type.
2. amend type specifiers to allow a primitive effect monad
