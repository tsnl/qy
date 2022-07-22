# Qy-v7.0

A language that mimics the look and feel of latently typed programming languages, 
but that performs static typechecking.

STATICALLY TYPED LANGUAGES <br/>
Languages like ML that rely on Hindley-Milner typing achieve polymorphism
with a 'typeclass' (maybe qualified via a trait/interface) that bounds 
monomorphs. E.g. in Rust, trait bounds compose to form a predicate on types that is
checked at compile-time. All argument types must satisfy that trait's bounds, meaning
a statically total predicate must hold true on these types. If the trait bounds are
violated, then instances of that type cannot replace a formal variable qualified by a
typeclass/trait, so the compiler raises an error.

LATENTLY/DYNAMICALLY TYPED LANGUAGES <br/>
Languages like Python, JS, and to a certain extent Java/C#/... rely on polymorphism
via dynamic dispatch (as opposed to purely static methods). In Python or JS, every
instance has the same static type, namely `object`, which exposes enough interfaces
at run-time to resolve object attributes and features. E.g. in Python 3, everything
is an object, and the `__dict__` member of a class is a hash-map mapping field names
to their values. Instead of `lea`-ing a static offset into a struct, we query for
an 'offset' into a immutable slot-vector at run-time using this hash-map. Python also
supports a fallback method when members cannot be found in `__dict__`.

THE LATENT ADVANTAGE <br/>
The advantage of the latter approach is that there is no typing overhead: the user
does with objects what they want, leaving analysis and specialization to the toolchain,
which includes a compiler, a runtime, and a GC tuned for the language's allocation
patterns. (E.g. I read once that Haskell's GC is more efficient when there's more garbage
on a frame (ig it is copying); this is a very different solution than would be ideal
for a language that embraces mutability and mutable semantics (and hence, object pooling
and reuse) like C#, Java, Python, ...)

THE LATENT DISADVANTAGE <br/>
The problem with latent typing in a monotype system is that it is impossible to assert
that two instances have the same most-derived type at compile-time.
E.g. we would like to make a contiguous (flat) vector of square matrices.
Unfortunately, we can only specify a vector of slots, since there is basically no way
to guarantee that two types are equal at compile-time.

```python
# what is the type of 'item'? Without context, we must be conservative and default to 'object',
# meaning we have to box instances.
def push_to_vector(vec, item):
    vec.push(item)
```

GOAL <br/>
Create a language that has the ergonomics of a latently typed PL, but that uses compile-time
analysis to specialize and check each function ahead-of-time. Aim to replace C with ~Python.
- offer the user a monotype system at first: our goal is to find wp refinements on these 
  boxes, sometimes `assert`-ed or `assume`-ed by the user.
- create types and metatypes as values: 
  - do not need to infer this at compile-time! contains all the same info a 'type-info' struct
    in a compiler would contain
  - e.g. `array(t)` can dynamically query the size of `t` when allocating flat
    - note (future): would be more idiomatic to use `array[t](n)`, but this is still possible
- embrace bind-once & update semantics for `flexi-slot` compilation
  - the idea is that...
    - all bindings are permanent: every slot is initialized with its final value.
    - all classes are sealed: it is impossible to 'inject' a member after-the-fact (no hash maps!).
    - => when a value is bound to a slot, that slot will only ever point at that value
    - => when a value is of type 'T', instead of making a slot `void* ~= T*`, we use a `T`-slot instead;
      **thus, we initially assume all slots are the same size, then try to specialize by unboxing sets**
      **of 'connected' slots (connected by runtime value flow)** 
  - to enable mutability, introduce an 'assignment' operator that is similar to `operator=` in C++;
    this (with sealed class property) guarantees that the underlying 'shape' of the slot will never change.
- enable polymorphism inspired by 'static inline caching'
  - in 'inline caching', each argument is accompanied by a type; the compiler identifies repeated instances
    of the same type (hidden class in JS) and specializes up to 4 variants per arg.
  - force all type values to be constant (only allowed in 'pure' in top-level scope, i.e. no globals)
  - => we can peval until type arguments are known, then monomorphize using the value information, not the type data.
  - => way more flexible polymorphism
  - => refinement typing predicates are the 'residue' and can be evaluated as predictable 'guards' or 'contracts' at
    run-time.
- composition over inheritance
  - inheritance forces us to box instances: this is very bad.
  - instead, encourage users to go the 'C' way and compose/delegate their values instead
- dynamic dispatch like Lua/Rust
  - since types are constant, can easily inject methods onto a type expression
- powerful macro system via partial evaluation
  - functions can be forcibly partially evaluated using `[...]` 
    - formal args must be declared using square brackets `[...]` instead of regular `(...)`
    - invocations must use `[...]`, and if this substitution cannot be made at compile-time, this is a compiler error.
  - this lets us guarantee that certain operations are evaluated at compile-time: super super useful.
  - this in conjunction with 'everything is a value' gives us a macro system via residualization:
    the parameters are substituted hygienically (since that's what a function call does), but since we do this peval
    at compile-time, it has the same effect as a macro system.

FEATURES <br/>
- language feels monotype, but actually each type is a free var, we solve for it obeying constraints else compile-time error.
  - a convenient and high-level replacement for C
- no type specifiers, rather types are first-class constexpr values.
- force compile-time evaluation/residualization using `[...]` calls instead of `(...)` calls (each func can take both)
- no inheritance, but dynamic dispatch is supported
  - dynamic dispatch is critical to growing the language
  - may support traits/typeclasses too; or should these be arbitrary predicates with `[T]` args?
- compiler monomorphizes everything, no exceptions, with the goal of doing as much `peval` and checking as possible.
- functions are not closures, though both supported
  - functions are only top-level, do not accept any 'ctx' slot by default.
  - closures cannot take constant arguments, but can bind values in-context
- manual memory management via RAII
  - need to support copy-constructors, move constructors, etc.

CHALLENGES <br/>
- write a polymorphic flat vector 
- serialization and de-serialization, especially binary stuff, especially for networks.
  - we can do more than 'marshalling'
- interface with C libraries, especially requiring pointers

IDEA: steal C's type-system (or Go's).
- can interoperate between C and Qy pointers.
- can use a mark-and-sweep GC with a radix-tree-based page-lookup to only mark own pointers
- great synergy like Python: do low-level stuff in C, high-level stuff in Qy.

