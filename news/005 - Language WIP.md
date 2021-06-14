NOTE:

**`.ptd` fields**
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