The following changes are being batched and deferred.

IDEA: separate stack and heap pointer types
- e.g. `^mut[T] => MutStackPointer[T]` and `&mut[T] => MutHeapPointer[T]` 
- i.e. slice becomes a first-class type, `push/alloc` always creates one element only.
- advantages:
  1. can augment heap pointers with information about allocations, e.g. reference counting
     - reference counting looks really attractive, but how to do weak refs? maybe `WkHP`?
  2. can detect many errors as typer errors
     - pointers can point to either the stack or the heap, but not both
     - reduces work to detect errors involving invalid pointer assignment

IDEA: in future versions, introduce...
- interfaces and method implementation + dynamic dispatch
- interfaces as type-classes
- exceptions
