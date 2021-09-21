# May 16 - Review 1

My friend Nitin has agreed to mentor me and review my work with weekly meetings.

## Elevator Pitch

Identifiers MUST contain at least one letter.
- if the first letter is Uppercase, TypeID
- if the first letter is lowercase, value_id

Key terms:
- module: a single source file containing code, can be template polymorphic
- expression: a part of a program with unambiguous instructions about how to evaluate a value from other values
- type spec: a part of a program used to identify a type, usually 'algebraically'

Issues to solve:
1. typeclasses were too general a solution to a specific problem: polymorphism
2. polymorphism still didn't work too well
3. 'hackability' lost-- overly pedantic
    - good systems to have
    - how can we elide more writing?
    
SOLN: gradual typing
- allow the user to hack together definitions describing the system's behavior
- types offer an additional, optional level of validation
- without type specification, looks/feels an awful lot like Python
   - evidence-based: number of characters typed and purpose nearly identical
   
## Key Decisions

Intentionally simplified language
- templates only offered at module level (i.e. script)
- interfaces (cf Rust traits) and 'method' implementation used for polymorphism
   - cf typeclasses for polymorphism: much, much, much easier
     - e.g. operator overloading
     - e.g. collections of class elements
   - crucially because offer fallback to dynamic dispatch by interface name
   - providing a worst-case that is like Java's best case and similar to boxing performed by Python
- still offers manual memory management
   - no clear plans, but idea is to offer instantiable heaps
   - e.g. bdm gc, linear stack allocator, etc
   - each module can pick the best solution for its needs
   - prototypes can use a built-in GC module and can be ramped into production code with manual memory allocation if 
     required
   - let hardcore programmers and code consumers share the same language => shared type system + verification
- no static methods
   - think of 'objects' as explicit closures
   - simply define methods on the unit type for static methods
- no overloading
   - can 'override' interface behavior pretty easily though

Emit to C++, now and forever
- cf Haxe: very wise choice
- compiler becomes easier to implement
   - can lower over time
   - performance benefits unclear
   - can implement standard library, language features in C++
- easy interoperability with existing C++ code bases
- easily emit to basically any platform
   - can go from C++ to LLVM, so can target everything LLVM targets and more
- I don't know enough about low-level optimization to exploit lower-level target

This language is one of a kind
- it is intended for people who want a lower-level version of Java, Python, or similar high-level languages
- STAY AWAY from notions like 'interpreted', 'scripting', 'high-level', or 'low-level'
   - they are severely limiting
- Wherever possible, use the 'interpreter' version of language analysis to contend with the strongest case
   - e.g. we declare variables in a chain together without shadowing, rely on later verification to check all OK
   - e.g. using Z3 to check pointers rather than ownership checking
   - e.g. template fallback ALWAYS possible using RTTI and dynamic dispatch
      - if you pass a value arg as a template, easy to convert to runtime
      - if you pass a type, bake one instance where the type arg is the interface specifying that type
         - by default, `IAny`
         - if user provides a narrower type or uses properties, can refine
      - redirect calls for unknown types (at compile-time) to the general interface-based version
         - ideal for things like plugins, extensions
         - incentive to recompile from source, benefit from 'extended analysis'

## Open Questions

1. C++ interop
   - how to call C++ code? Important for short-term
      - wrapping C code is straightforward enough
      - how does Rust do this?
   - how to call from C++ code? Important for short-term selling
      - easier to implement
      - but less important
   - TODO: how does Haxe do it?
   - Nitin suggests: first use a C FFI.
     - can then work more complex C++ FFI through C FFI
2. Special method-call operator
    - call it `!` (used to be `:`)
    - note `::` used for static module access, cf templates `mod<...>::`
3. Any shortcomings?
   - things unseen


## Scratch


```
IVector2f = interface {
    requires {
        x: (Self) -> F32;
        y: (Self) -> F32;
    };
    provides {};
};

Vector2f: ICopy {
    copy = (self) -> {
        
    };
};

(): IProgram {
    main = () -> {
        v = Vector2f {0f, 0f}; 
    };
    
    add_vec2f = (v) -> (w) -> Vector2f {
        v.x + w.x,
        v.y + w.y
    }; 
    
    add_vec2f: (IVector2f) -> (IVector2f) -> IVector2f;
};
```

## Clever Show-off Points

1. using `()` as extending method from unit
    - cf Scala, implicits
2. no variables, just pointers to mutable data
    - no global variables
    - no local variables either
    
## What to Work on Next

What to work on next?
- just implement base features first

On SMT analysis?
- several language bindings
- just use the Scheme version:
    - easy to generate
    - don't need a fancy library
- if familiar with SMT libs, go for it
- for ADTs, create a constructor for each constraint important
- when looking at Z3, unintuitive what will get optimized away
    - stare at constraints to understand what Z3 will not deal 
      with
    - Z3 analysis is undecidable, so make sure you give Z3 good
      constraints.

Still have static functions through modules.
- to truly remove static functions, disallow value bindings at 
  module scopes.
- removing templates and 'include'-like import semantics may work,
  but would sacrifice template polymorphism.

Per-module allocators?
- what happens when a module returns a pointer?
- do functions include allocators by 'static closure'?
- better still: just generalized allocators, like functions
- perhaps use 'implicit' allocators?
