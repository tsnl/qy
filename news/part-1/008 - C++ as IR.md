May 2, 2021

### Haxe

A lot of decisions in this language (like compiling to C++, targeting multiple platforms) 
are influenced by Haxe.

Why does Haxe use a VM? It makes targeting different platforms easier.
- Each platform implements a few functions
- The VM runtime provides all the functionality for a black-box VM on a platform-by-platform basis
- Generating an executable as simple as bundling the VM implementation with its bytecode data input
- Interfaces between platform and language very clear: interpreter is the mediator.

Haxe compiles to source code or byte code, thereby creating a platform-agnostic target layer.

### First Emitting C++

C++ is an excellent candidate to emit to because...
- it supports polymorphism via templates
- it is compatible with a rich ecosystem of libraries
- it is one of the fastest languages in existence

### C++ as IR

Using C++ as an intermediate representation (akin to a bytecode) offers 
these key advantages:
- can import and use C++ in source code and link to C++ source in IR step
  - Haxe exposes different constructor semantics as static functions
- can export C++ headers & libraries
  - first for C++ interop: include astropod code from C++ with ease
  - but also for C interop: `extern C`
  - but also for scripted language interp, e.g. Python
- can debug emitted C++ more easily than LLVM IR
- WIDER compatibility than LLVM IR
  - Emscripten expects C++ input, likely transforms libraries, not as easy with LLVM IR
  - There exist C/C++ compilers/linkers for platforms not built on LLVM IR, but there exist excellent cpp to LLVM IR compilers
  - C/C++ is so prolific that it is extremely unlikely systems will not work with these targets
- can write different PLATFORMs and FEATUREs in C++
  - this means that adding a new standard library module is pretty straightforward
  - this means that maintaining and fixing standard library modules is pretty straightforward
  - this means adding language features is much easier
    - e.g. adding interfaces easily achieved using C++ classes with multiple superclasses.

The only issue to solve is how to handle cyclic imports.

Create a header/header/source triplet for each module
- `module-name.decl.hh`: declarations, includable
- `module-name.impl.hh`: inline implementations (like templates)
- `module-name.impl.cc`: source implementations

All files only include the `decl` header file.
- to avoid/handle circular dependencies, may need to expand ourselves
- can also perform visit-once expansion via C pre-processor

Consider two modules: `Vec2` and `Vec3` with the ability to convert one to another.
- **does not work**

Alternative: independent 'decl' headers
- no 'include' in 'decl' headers. 
- explicitly/inline forward declare everything required in 'decl'
- only 'decl' can be imported
- 'decl' may contain repetitions, but only forward declarations, so ok
- can include from 'decl' in 'impl' header for 
  - type definitions
  - inline function definitions (esp. templates)

Then,
- Vec2 forward declared for Vec3 header and vice-versa-- ok
- Vec3 impl.hh includes Vec2 decl.hh and vice-versa-- ok

If not the above system, a more organic product of generating all
data and separating it may work.

### Sunsetability

C++'s verbosity ultimately makes it a great compilation target.

When designing a language, ensuring it can be 'sunset' by making it
easy to generate can be an important consideration.
When done poorly (e.g. SQL), can create security vulnerabilities,
overhead, and more.

### Import C++ code

If we import from a C++ header, we need a way to translate calls.

QUESTION: without overloading, how do we consume overloaded C++ code?

Maybe importing C++ is not a good idea... or maybe overloads are?