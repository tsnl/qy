May 26

After getting C++ code emitted, I took a break to work on a project in Python/C++ to determine how this language can be 
useful.

A few minor language tweaks:
1. remove syntax in grammar for templates (for now)
    - we will look at ways to specify template args later.
2. use `::` for typing, `:` to access methods, and `.` to access data members (including module members)
    - the `!` character is just too long. `:` is much easier on the eyes, and is a good fit for such a frequent symbol.
    - added `by` keyword to make extension a little clearer.
3. use `[]` (in the future) for template calls, and the `:at(index)` method to get elements by index.

A big philosophical tweak:
- as initially planned, use this language as a C++ pre-processor.
- this means modules need a well-defined, source-level C++ interface
    - would allow C++ code to call language code
    - would allow language to call C++ code
    - defer checking C++ dependencies are defined until later.
- one approach: compile each module into a `.hh/.cc` file
    - can place defs in header or source as required
    - can include from other modules
    - IDEA: 
        - in event of cyclic import (detected by include guard),
        - _instead_ produce forward declarations
        - _instead_ do nothing (since guaranteed to have been imported before?)
- remove cyclic imports
    - inhibits interop with C++ since interdependent classes need each other's definitions
    - any other decision makes it impossible/very hard to emit C++ classes in all cases. 
    - IDEA: may not be necessary if we emit in reverse dependency dispatch order-- must test.

Approach to emitting C++ without templates:
- first, emit module class beginning
- then, emit ALL type-definitions recursively
    - if cycle detected, error: type non-reifiable
    - order may be garbled, but valid in C++
        - print children before self (post-visit order)
- then, emit ALL value-declarations 
    - turn lambda bindings into function declarations
    - turn value bindings into var declarations
    - note these symbols must all be marked `static` in C++
- close module class
- NOTE: must emit ALL modules' classes before any defs (see below)
- after all classes, emit all VALUE DEFS as STATIC INITIALIZERS/FNs
    - non-lambda bindings get initialized to constant expressions/func calls
    - lambda bindings get C++ function definitions
    - bodies of lambdas contain expressions-- get evaluated here.
    - NOTE on destination:
        - if template class, all initializers must be in header, with `inline` spec
        - else, can put all initializers in `.cc` file.

KEY IDEA: emit class definitions before any function definitions.
- if we bundle endpoints into a single `CC/HH` file-pair, we prevent all ordering issues.
- this allows us to keep cyclic imports.
- consuming in an acyclic way from C++ is a C++ problem.
- for C++ interop, we can generate a partial header and require the user to provide 
  implementations in C++ that are invoked
    - thus, C++ header is replaced/supplemented by an Astropod FFI header.
    - can implement this later.

Finally, fold checking into C++ emitter
- can write a separate 'checker' backend later
- only check what needs to be checked to emit code at first

## Adding back Cyclic Imports

Cyclic imports disallowed before, because...
- consider a polymorphic module M with a type field T that depends on another polymorphic module N with a type field U.
- if typeof(U) depends on T (e.g. Vector<T.thing>) but M imports N, `N.U` will resolve to an unknown type.
- THUS, we need a declaration of all module member types before any type-definitions.
- However, we cannot re-define the same module class in C++.

If we expand modules instead of mapping them to template classes at first,
- each polymorphic module field would accept its own template arguments
- **we can declare (but not necessarily define)** all static module fields before any type-defs

After this, we can map these granular definitions back to C++ static classes (with a nice user-interface).

Thus, we still achieve the _same_ export interface as the previous part, but can keep cyclic imports
- declarations for all modules precede all type definitions

Thus, **final order for bundles**:
1. emit all `granular type declarations` for all modules
    - use expanded, mangled names and per-item templates for each module type-binding element
    - goal is just to declare (not define) all types so indirect references will work
2. emit all `granular type definitions` for all modules
    - define all the types declared in step (1)
    - might be in a wonky order, but order guaranteed to exist
    - still no value definitions, but guarantee types all defined OK
    - even class method declaration should succeed when `extensions` are a thing because...
        - methods are just declared here, so indirect types okay, all declared above
        - any contained types can be emitted before
        - NOTE: method template args must match module where defined.
3. emit all inline class definitions
    - bind class type defs to granular type declarations
    - emit value and function **declarations**-- all variables & functions `static`
4. emit all function definitions
    - includes definitions for methods for all types & static methods for modules
    - includes templated and non-templated functions

**SUBTLETY:** when extending a method, template args can be used to define a class of methods.
- how does this affect VTable performance?
- we need to determine if template or not by whether a polymorphic type or value is bound in the def.
- **ISSUE:** if a polymorphic value is defined in an extension, we have no way to pass it template args
    - since it is invoked via an object and not the defined module
    - since it is defined in a module and implicitly captures all args
    - **SOLN:** include template arg closure in extension so user can pass args to functions? 
        - template args usable to satisfy several interfaces
        - OR can pass template args when invoking methods?

**SUBTLETY:** astropod modules, once exported, may have different versions of the same type
- e.g. `Unit` in one module may have a method not defined on `Unit` in another
- this is up to C++ programmers to handle. Too confusing? Just integrate in Astropod instead.

**TODO:** implement this
- first, get imports working, and ensure cross-module imports are correctly typed
    - this will help us test that import cycles are still generated correctly
    - `.` could refer to a module or a struct, and `struct` is invalid in typing contexts 
- then, ensure `.` operators function correctly on structs, tuples, AND MODULES.
    - this rounds out monomorphic typing
- then, add polymorphic types, like `Ptr` or `Array`
    - allows us to test typer on polymorphic type solving
- then, add templates for modules
    - extend polymorphic type solving to anything
    - NOTE: need to determine if methods are polymorphic or not, and if so, if 
- finally, can implement C++ emitter with checks and printing
- then, can implement another backend with checks only
