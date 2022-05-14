# Base Language

_Oct 29, 2021_

**WHY:** a PL for iteration and prototyping that runs faster than Python.

When writing prototypes...
- must be able to write code quickly-- want **duck typing**
    - (REVISION) duck-typing is inefficient, because all data must resolve core attributes at run-time via a 
      type-independent interface
    - instead, aim for manifest typing with interfaces and implementation (like Go)
    - interfaces are also too static! Can we build automatic interfaces? Yes! (See rambles-pt4)
- want low-level memory access
    - C-level data-types => can directly interface with C programs
    - emphasis on pointers and memory rather than 'objects' and messages feels more like an array-programming
      language.

Thus, design
- type system, semantics identical to C
    - means we can directly interface with C programs, e.g. via `libffi`
    - means we can acquire objects from C, pass objects to C and expect it to be freed with `free`
    - in debug builds, we can track the bounds of pointers using fat pointers
    - instead of `const` to be immutable, use `mut` for mutability
    - all stack variables are immutable, but `alloca` returns a mutable pointer.
- **~~no~~ few type specifiers, but manifestly typed**
    - source libraries only, use type unification to fill in holes and exploit whole-program optimization
    - since we have all the source code, unification errors are type-checking errors
    - must use templates, but means programs look like they're written in a dynamic programming language
    - since we have all the source code, if we cannot infer a type, it must not matter to the program we're generating.
      - after living with interpreted language standards for checking, lax AoT type-checking standards > just scoping
- rely on user-defined RTTI
    - just like in C, user must define their own 'kind' tags
    - instead of one-size-fits-all solution, which makes general trade-offs rather than more efficient, specific ones.

For typing, cf ML
- (REVISION) also allow _partial_ type-specifiers in function definitions: compiler unifies these against top-level decl
  and inference.
  - This allows writing declarations+definitions in either Scala style or C/OCaml style.

https://courses.cs.washington.edu/courses/cse341/04wi/lectures/06-ml-polymorphic-types.html

```
; Qy-v2.1 uses the same type-system as C
;   - in debug mode, pointers are also checked for bounds
;   - functions cannot accept implicit params*
;       - may change, GNU extensions do allow this in C using trampolines, which require an OS that supports allocating
;         writable and executable pages.
;   - this ensures compatibility with any DLLs that use the C ABI, provided we can un-mangle names.
;       - e.g. C/C++
;       - e.g. Python extensions
```

---
