Jul 11, 2021

Been working on detecting non-local ID use and implications.
- each `LambdaExp` now stores a map of all non-local IDs, courtesy `typer.inference`
    - we can implement closures by giving every function an extra arg, turning each func ptr into a fat ptr
    - extra arg represents 'context'
- each function type is associated with a `ClosureSpec`, to enforce `ClosureBan`
    - formerly known as `NoClosure {...}`
    - this specifies whether the caller must support calling fat pointers, NOT whether the function itself needs one.
        - e.g. a curried function whose inner function uses the outer function's local variable
            - even though the outer function does not need a closure pointer,
            - it returns a fat pointer that does
    - if a function type-spec is wrapped in `ClosureBan {...}`, it means no function in the curried chain can use/have
      a closure pointer.
    - only functions with `ClosureBan` can be called from C, or general FFIs
    - SURPRISE: currying still works, albeit without closures?
        - note that the inner function does not use `value`, the only local defined in the outer func
        - so, the inner function satisfies the `ClosureBan`
        - kind of useless, but nothing stopping the user from expanding the outer function (e.g. logging)
        - this is possible because we verify whether every function actually needs a closure pointer        

        ```
        dm currying_in_c {
            f :: ClosureBan { (F32) -> (![F32]) -> () };
        
            f = (value) -> (ptr) -> {
                ptr := 42f;
            };
        };
        ```
      
Another breakthrough came in the `unify_existing_def` function of `typer.inference`: 
- after unifying, we can compare TIDs to see which has more info
- we update the context with the richer TID
- this could cause issues, but is an extension of context rewriting

Finally, the `!` character has been introduced to connote 'mutability' or 'divergence'.
- use it before arguments of a function to specify non-total function call
- use it in `new` expressions (`make!` and `push!`) to allocate a mutable (rather than immutable) pointer
- `@p` de-references the pointer `p`-- `@!p` does the same, but expects `p` to be a mutable pointer.
    - exactly the same operation, just different types of arguments.

More work on inference required:

- TODO: for pointer expressions, determine set of RelMemLoc the pointer can point to.
    - this allows us to decide if assignment is `TOT` or `ST`
    - implement with ANOTHER returned value from `infer_exp`
        - what about a function that returns a pointer?
            - a function passed a stack pointer may return a stack pointer
            - however, returning stack-local pointer is an error
        - maybe encode optional RML on function, but relative to caller?
        - maybe use a symbolic approach, with RML variables?

- TODO: figure out why sub-mod types are wrong, and seeded file mod never changes.
    - after typing, accumulate `ElemInfo` list immutably rather than assembling/subbing on-the-fly

- TODO: typing 'size' specifiers in slice, array `new` expressions.
    - they could change the `SES` (side-effects-specifier) or `CS` (closure specifier)

Plan after this:
- get `if` expressions working: last native piece before we can write real programs, if only using recursion.
- work on topological sort of global initializers
- work on template instantiation
- work on adding extern functions
- work on emitting LLVM IR
- work on SMT analysis, `assert` and `free` statements.

NOTE: also need to test, test, test.

---

Jul 7, 2021

Scope-based SES checks working (testing pending), using type inference rather than basic checks.

Now that typer is in place, lots of stuff that was skipped must be implemented. 

List of **technical debt:**
- **parser todo** must be completed
    - pointers, arrays, slices
    - make/push
    - no more 'struct' expressions, rather Cast + tuple
    - consider: `assert` statements
    - consider: various kinds of loops, as imperative statements
        - might be wise to make 'force-eval' statement simply `do`,
          such that an optional `while` repeater may be provided afterward
- **typer todo**...
    - checking mutability also straightforward using the typer
    - must implement typing for various unary and binary ops
    - determine whether to use `.ptd` field for pointers
        - would need to amend `GetElemByName` typer
- after this, can proceed to **PTC checks**
    - includes checking for stack pointer memory leaks
    - includes checking that every allocated variable is freed
- finally, can use either **SMT analysis** to...
    - ensure convergence if `TOT` rather than `DV` or stronger
        - consider recursion
        - consider loops
    - ensure slice indices are always valid
        - slices are dynamically sized, so need to check that
          indices access within them.
        - can also ensure signed indices are never negative.
    - verify `assert` statements
        - user-provided `assert` statements force the compiler to
          prove a predicate is always true in order to compile
          successfully.
        - this is a 'starring feature', and is easy to add.
    - note that...
        - would need to add `assert` statements to the language
        - can add loops to the language, BUT not required to work on SMT
            - `for`, `while`, `do {} while ()`, `loop {}`
            - can still check for infinite recursion
            - need to **impose a stack size limit**
        - challenge in verifying loop bounds are OK

- after this, can proceed to interpreted checks
    - purpose is to generate template arguments while evaluating
    - can annotate source code  
- after this, can emit LLVM IR

---

NOTE:

**`.ptd` fields** (ON HOLD)
- rather than `*ptr`, we can use the `.ptd` field to access a pointer's data.
- this is the only field a pointer supports.

**allow constructors for struct expressions too**
- very similar initially to a chain
- does not admit side-effects-specifier
- may be easier to mandate effects-specifiers for chains
    - so need to write at least `TOT` for a chain
    - still not required for function return type to facilitate concise currying

**require empty template args `[]`**

**`extern` statements in source code**
- imagine having top-level `extern link` and `extern load`, so we get syntax highlighting and checking in source code instead of
  writing type signatures for loaded functions in strings in JSON
- EVEN IF the user must load symbols at run-time, we can...
    1. move any definitely dynamically loaded symbols into a nice, AoT structure
    2. provide a library to dynamically load compiled native modules, which can `extern load` or `extern link` 
       platform-dependent libraries 
- can start with `extern link <mod_name> {...}`, then add `load`

- IDEA: inspired by our monads, use explicit module constructors and allow one for external modules. 
- still only one place such a constructor can be used, but here's an example:
    
  ```
  mod sdl2 [] = link "C" using {
      recipe {
          primary_header = "SDL.h",
          core_args = CoreLinkArgsInfo {
              include_dirs = [
                  "./dep/include/"
              ],
              link_files = [
                  "./sdl2_helpers.c"
              ]
          },
          platform_dependent_args = PlatformDependentArgs {
              ms_nt_args = MsNtLinkArgsInfo {
                   link_files = [
                       "./dep/ms-nt/SDL2main.lib",
                       "./dep/ms-nt/SDL2.lib"
                   ]
              },
              posix_args = PosixLinkArgsInfo {
                  link_files = [
                      "./dep/posix/lib/SDL2.a"
                  ]
              }
          },
      };
      name_map {
          init from "SDL_Init";
          quit from "SDL_Quit";
          Event from "SDL_Event";
      };
      interface {
          sdl_init :: (UInt32) -> ML Int32;
          sdl_quit :: () -> ML ();
      };
  };
  ```

- note: EXN can handle OS signals rather than built-in interfaces
  - TODO: ask Nitin if this violates 'the lattice'
  - but `signal` is supported on Windows and Linux
  - C++ forbids throwing exceptions in signal handlers, likely because it uses signals too
      - signals invoke a separate stack, and cannot be recursed
  - if we restrict signal handlers to `Tot` rather than `Dv`, we can pre-determine the maximum
    size of the signal stack ahead of time.
      - if we can determine the signal stack is quite small, this could make a whole class of
        asynchronous, signal-based programming very, very efficient
      - signal handlers receive the stack as an argument: we can forward this stack pointer 
        to support continuations using exceptions in the future.

---

Jun 13

Standard Library Ideas:

- consider a template-based multithreading model based on Intel TBB
  - https://software.intel.com/content/www/us/en/develop/documentation/onetbb-documentation/top.html

- consider USD (Universal Scene Descriptor) support in the standard library?

- consider a Vulkan wrapper?

- allow imports relative to the working directory using `$`
  - just substitute the `$` character for the project working dir path