# Qy v4

Qy v4 is a high level, manifestly typed, object-oriented, systems programming language.

Despite its manifest typing, writing code in Qy is more similar to writing code in Java or Python than C++, without any significant performance degradation.

It can easily be interpreted or compiled, compiles quickly, and easily supports high-level concepts like reflection, iterative compilation, compile-time evaluation, refined types, persistent variables, and more over time.

## Language Description

### USER MODEL

To the end user, Qy is an interpreted front-end to describe how the compiler will work.

In Qy, all data-types are either primitives (e.g. int, float, pointers, etc) or objects (always referenced by pointers). 
Furthermore, all pointers are guaranteed to be of the same size.
Note that types are first-class objects.

The Qy static type system is exceedingly simple, checking that only primitive types line up:
all 'refined' type checking based on the contents of pointers is pushed into user space.

Given a script, Qy sequentially executes each line, such that
-   single pass: the compiler/interpreter is strictly sequential
-   function definitions: generate LLVM bitcode as we process the definition
-   type definitions: generate LLVM bitcode as we process the definition
-   NOTE: types and functions may also be exported within function bodies: compiling these will be a challenge.

Supporting these features are two more ideas:
-   object-based semantics: the user can only define methods on boxed datatypes, be they sealed classes or interfaces with typed hole-methods.

    This facilitates message passing, polymorphism, `const` tagging, etc.

-   metatyping: types are just constructor objects that use more primitive constructor objects.

    In other words, types are just weird 'allocator' instances that expose ways for the compiler to query about a (static?) layout.

Thus, while traditional programming languages (like C, C++, Java) can be thought of as providing
a declarative scripting interface to a compiler, we provide an imperative one.

### COMPILER MODEL

In reality, we don't interpret code at all, but rather compile it to machine code along with an embedded runtime library.
-   the TAILS experiment highlighted how all ADTs and their associated type information can be computed computed, stored, and distributed at run-time.
-   if we enforce a single-pass restriction, we can compute these results at run-time, and then use them to generate all future assembly at a quality level matching statically compiled programming languages.
-   this compiler interface can eventually become the heart of arbitrarily many DSLs powered by macros.
-   can use shadowing, forward declarations, and more to convert interpreted code into compiled code.
-   we perform static type verification based on type information available at the start of each statement.

    we can use similar closure verification to even generate template instantiations.

Implementation-wise, this means switching to a statement-by-statement compilation model with the ability to evaluate/call into already compiled code. Maybe LLVM ORC is the way?

### EXECUTION FLOW

Since we may still compile code while loading a script, the user should define a `main` callback that is invoked by the compiler after all code-loading is finalized.

This doesn't mean the user can't evaluate things at compile-time: indeed, all types are generated/referenced using compile-time evaluation. It just means this slower mechanism should be disabled once we know things like the type system are frozen.

