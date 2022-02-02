# `Q4` - Version 4 of the Qy Programming Language

> (WIP)

> (May be renamed to 'Backus', while Qy-v2.1 retains the 'Qy' name).
> see:
> https://en.wikipedia.org/wiki/FP_(programming_language)

Q4 is a verified systems programming language that is designed to enable 
-   safety, for any program you could write in assembly
    -   the compiler checks both types and values to ensure your program proves it computes the expected output
    -   the compiler does not impose any stylistic check: if you can prove it, you can use it
    -   e.g. refinement types and dependent types, which incorporate static or dynamic values resp. into type definitions with a predicate
    -   elides as many run-time type checks as possible, try to guarantee no runtime errors unless hardware issue.
-   time-saving compiler-driven inference
    -   in conjunction with DSLs and/or custom parsers/loaders/translaters, the Q4 compiler can be extended to check arbitrary logic.
    -   the theorem prover can be used to solve for arbitrary unknowns at compile-time, saving error-prone hard-coding where unrequired
-   10x productivity on small and medium size projects
    -   these goals should result from improved error messages, autocomplete, but mostly finding pitfalls as early as possible.
    -   these proof systems have trouble scaling up to larger projects, piecewise analysis of crates/packages/modules is the only way to go
-   the next generation of programs
    -   Programs are just a series of bits, and the ways we assemble programs now need to get better if we want to assemble better programs.
    -   Encoding value information at compile-time empowers the compiler to infer much more about program structure.
        -   e.g. awareness of IO interfaces provided by an OS/platform like files, sockets, websockets, ports, etc.
            -   the crucial next-step to smarter inference
            -   vital for distributed systems
        -   e.g. awareness of hardware interfaces provided by a piece of hardware
        -   e.g. solving high-level constraints using the most efficient, provably correct low-level code possible
        -   e.g. probabilistic approaches to programming, which will yield the best performance optimizations
            -   key is to embed an algebra describing random variables into the type solver
            -   e.g. describing real-world phenomena (this interrupt has 0.0000005% probability of being triggered per us, that interrupt has 85% probability per us, but more granular)
            -   e.g. generating (maybe even weighted) hints for branch prediction, using iterative compilation and POGO in its ultimate form
            -   e.g. zero-error/error-acceptable approximate data-representations
            -   e.g. true error estimates for things like time, failure rates, etc.
    -   We need ways to run higher-level languages faster: why not embed in a low-level languages?
        -   e.g. latent typing is traditionally hard to infer and hard to check: but a boxed data model in Q4 is first proved to be correct with invariants by the programmer.
            -   latent typing relies on using the same base-type for all/many instances, and querying values to determine typing
            -   a-ha! **refinement types can be used to encode latent type systems in a manifest type-system, and in a verifiably safe way!**
        -   this would allow transparent data-sharing between different ecosystems
            -   certain parts of the application can be written in a simpler sub-language, while performance-sensitive areas are coded in a language at C-level.

You, the user, define 'refinement types', which are sets of values that, in addition to being of the same base-type, _always_ obey some invariants you choose.
To check these, Q4 uses liquid types, a type-checking technique that uses the following steps:
-   first, a 'base-type', which describes only data layout but not (much) semantics, is determined using conventional type-checking and type-inference rules.
    -   e.g. this is a pointer, this is an int, this is a struct that was defined on line X, etc.
    -   if any errors are detected, the compiler halts.
-   next, 'liquid types' are initialized for each value 'slot' in the program: these are variables we can reason about using the Z3 theorem-prover.
    -   using the rules of liquid type inference, we can systematically verify that our invariants hold just like a type-checker ensures that typing-invariants hold.
    -   e.g. constraining the range of an integer to prevent overflow
    -   e.g. parsing memory stored at an opaque object handle/a tagged union object handle
-   if the program can be proved successfully, then LLVM IR can be emitted using base-types, and refinements can be used to help the backend/optimizer.
    -   e.g. eliminating dynamic checks for conditions we know to be true
    -   e.g. eliminating unreachable pieces of code or always-true branches
