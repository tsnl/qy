# Qy 3.1 (future)

> This is a spec for a language that may or may not manifest as its own, separate successor to Qy, or whose features may be integrated into Qy if possible.


Source file transformations are a painful necessity. They are required to...
-   Insert pre-computed/configured results into source code (like compile-time evaluation).
-   Get information at compile-time to generate key data-structures or definitions.


Existing solutions include...
-   Dynamic programming languages
-   Templates, constexpr in C/C++
-   Racket/PLT Scheme's extensible reader/lexer/parser system: use a shebang-like line to specify a module that
    transforms the rest of the file into a Racket module.
    -   This would allow users to integrate various input files as Racket modules. XML? JSON? Datalog? 
        All transformed into statements that instantiate the ASTs of these files. 


Why not...
-   make source code transformation passes a part of the code base?
-   allow the user to emit arbitrary languages


**Qy 3.1 is a macro-focussed language that produces independent `.so` modules.**
Macros and modules form the core of Qy. 

-   The user only writes and composes macros and base language statements, much like in LISP.

    Unlike LISP, the base language is much closer to an out-of-order LLVM IR than a high-level interpreted language.

-   Each base language instruction inserts, modifies, or deletes a low-level output object file. (`.so|.dll`)
    -   A source file without any macros directly specifies how to build a single position-independent object file 
    -   These shared objects can be easily statically linked if required.

-   Macros are expanded recursively into base language instructions.

Like Racket, we can specify modules to act as readers and parsers in custom languages.
-   **This combination of arbitrary parsers and a low-level backend in a single compiler is what makes Qy valuable.**

In the tradition of Qy, manual memory management would be preferred over garbage collection. Embrace static regional allocation.
-   Mandating a little planning can trivialize memory management while improving performance significantly,
    even over RAII.
-   We can allow the user to evaluate any code at compile-time efficiently using generational compilation.
    -   Each output shared object is the descendant of zero or more ancestors that will trigger a specific trap if a value is computed from
        invalid inputs.
        -   Global variables are usually specified by pointers to the heap. Setting a `nullptr` would trigger a trap. Setting a trap handler
            would allow us to intercept any such errors and report them as compile-time errors.
    -   Alternatively, a VM could be used to evaluate these results. This would produce superior debug output.
-   The idea is that the user runs arbitrarily sophisticated code to pre-calculate the size of different regions.
    Regions are scoped, constant-size slabs of memory that are associated with stack frames.

Finally, Qy can also be used to generate other kinds of output.
-   Compile-time execution can be used to write output files.
-   Emitted modules are basically linkable executables. 
    Certain modules can be generated such that they contain an entry point that, by accepting flags, prints output in various formats.

