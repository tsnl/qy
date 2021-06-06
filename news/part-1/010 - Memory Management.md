How do we move/copy data?
- highly inefficient to copy-construct
- highly inefficient to box & move
- only efficient path seems to be providing 'move' semantics

The primary issue with Rust is its restrictive borrow-checker,
which goes against the "I just wanna hack" mentality favored by Scheme.
However, these 'move' semantics are an extremely efficient way of
achieving the 'boxed copy' behavior of Java.

IDEA 1: runtimey Rust
- _rather than guarantee all moves correct, relax_
- implement move constructors, throw a runtime error if invalid move made
- run Z3 to catch runtime errors more flexibly than a borrow-checker
  - plays well with a user-facing exception system (cf. Actor model failure system),
    can fail the input if an exception may go uncaught at runtime.

IDEA 2: flattened boxes
- expose data structures as boxed pointers, like Java. 
- where only one reference is provably held statically, elide pointer hop and
  push into stack.
  - such heap -> stack optimization is a known feature of garbage collectors
- even without elision, moves still really fast (just pointer copies)

SUMMARY 1:
- this language will not compete with Rust or C++ while simplifying.
  - it would be much harder to do so
  - radical innovation, a lot of time and testing
  - Go 2 introduced generics, C++ introduced concepts while we were at work, leaving most work useless:
    how can we stay ahead, or at least abreast?
  - at the end, worse buy-in
- focus on boxed memory model
  - the issue with boxing is memory fragmentation
  - what about **boxing + allocators**?
    
INQUIRY
- how to allocate boxed elements in a flat vector?

IDEA 1: `emplace` aka placement new, never `malloc`
- rather than make `new` a global function, make it a method.
- the only way to allocate memory is using a container data-structure.
- destructors deterministically called.
  - however, this means references can be invalidated.
- ISSUE: how to return a stable reference?
  - IDEA: like allocator, use 'handle' to drill down
    - each object has an allocator pointer that can be queried for a 2-tuple key:
      - the allocator's stable ID
      - a stable ID within the allocator
    - note this could be recursive
    - handles cannot go stale because instance would not exist to query with since allocated by container
  - IDEA: don't! use Z3 to verify references stay valid.
    - broadly associated with scopes.
    - **user can still take pointers to stack variables**
- ISSUE: how to allocate one boxed element?
  - Box data-structure! It's explicitly inefficient.

IDEA CONCLUSION:
- the above `emplace` system will only work if we can use Z3 to check that
  all pointers remain valid.
  - not just destructor, but even `push_back`
- Java was designed to solve segmentation fault issues, and it really did.
- Perhaps the key is to deal with **global tables** instead of individual objects.
  - so allocator data-structures must be global
  - even if allocator changes memory, we can store KEYs instead of pointers

---    

IDEA 2: Generic `Handle`

- user can specify `Vector[T]` allocators that accept integer keys.
  - only admits elements of one data type, but contiguously packed
  - `emplace` to allocate returns a special `Handle` object
  - the `Handle` can be used like a stable pointer to the element in the vector
  - cannot delete/reclaim memory
- so `Handle` is like a pointer, except with a statically associated global container variable
- if we model global variable pointers as constant, this can be done as a standard library feature
  - a `Handle` accepts a template value pointer parameter to a generic container
  - `Handle` implements `operator 1*` to access members
    - how do 'set' semantics work without references? A different operator?
- different containers can be used to reclaim memory, serve different threads.
  - using **multiple GCs** at once? A good way forward!
- can be refined to `SlotMap[T]` to add delete-able IDs.

What about copy and move constructors?
- we always use the default copy constructor
- to get around this, use pointers or handles
- why 'reconstruct' from an existing instance when a pointer reassignment will do?

This proposal would not need any new features, cooperates well with C++, and would eliminate
implicit 'move' semantics. 
However, it would require robust interface support, both for dynamic dispatch and as a form of
compile-time classification.
- interfaces let us express various constructor, the destructor
- interfaces used to express containers

Rather than `emplace`, this may work better as `push` since no
constructors other than default copy are required in language.