# Emitting Dynamic Dispatch

May 14

Since C++'s overlapping interfaces should be explicitly forbidden
by the spec, it would be wise to implement dynamic dispatch/virtual
tables ourselves, even if in C++ at first.

## Use interfaces by pointer

To emphasize the fat-pointer nature of interfaces,
make the following changes:

- always use interface elements as `&Interface` or `&mut Interface`
- this makes it more intuitive to pass a pointer to construct an interface object
- this allows us to specify direct interface instances as an option for templates in the future
    - with a fallback to taking a pointer and DD-ing instead
    - since an interface specifies a typeclass, we can choose the best option case-by-case.

## Impl interface for interface

### Rejected

NOTE: interfaces can extend other interfaces.
- `Self: IBase` in `requires`: 
  copies over `IBase`'s required and provided methods.
- `Self: IBase` in `provides`:
  checks that `Self` satisfies `IBase`'s requirements,
  copies over `IBase`'s provided methods.

This can be followed with implementation like:

```
ICube3d: IShape3d {
    
};
```

BAD: too complicated, nuanced.

### Rusty Composition

Take the union of two interfaces using the `|` operator.

Must be assigned to an ID that also starts with `I`.
- cannot implement a `|` expression: must have a name first
- this improves error reporting significantly.


## How do we Compute VTables?

PROBLEM: How to arrange methods so that casting to interfaces
works.
- if a datatype satisfies 3 separate nontrivially intersecting interfaces, there is no way
  to allocate one array without repetitions such that sub-slices can be used as interface 
  vtables
- INSTEAD, want to compile a different `vptr` instance for each base interface. 

Every type may implement multiple interfaces.

Every interface may implement multiple interfaces.

If we decompose the space of all methods into a basis, then
each basis element is a function (name, signature) pair.

We can then express interfaces and types as sums of basis elements.
- this is just exploiting commutativity of (+) to express a set of methods
- we do not need to deal with the order-restricted case since we create bespoke
  tables for each interface satisfied by a type.

Now, for each interface implemented for that type,
- the interface must have a name, since implementing anonymous `|`/(+) interfaces is forbidden.
- each named interface is either...
    - an interface definition
    - an interface composition
        - so inherit from each composed interface

We can now generate a set of all interfaces against which a type may be used.

We can then generate a set of all virtual tables that instances of the type may require
when being cast to interface pointers.
- when a type is converted to an interface pointer, we can select the interface pointer
  satisfied by that type against the specified interface
- when an interface pointer is converted into a base interface pointer,
  things get more complicated.
  - we need to know the original type so we can obtain a 'smaller' vtable pointer
    for the smaller interface.
  - so rather than just track vptr for active interface, must track RTTI
  - so we can go to type-info, query the right interface, and go back
- so when a type is converted to an interface pointer,
  - first obtain the type's rtti pointer
  - store on the fat pointer
- when an interface method is invoked, 
  - lookup the appropriate vtable for the statically known interface type,
  - call the appropriate method
- when an interface is converted to a base interface,
  - change nothing
  - method calls under the base interface name will automatically look-up a different vtable
- thus, the second pointer is not a vtable pointer, but a `vtables/rtti` pointer.
  - these can get very bulky, or will need a BST for each method call
  - each type must support several virtual table pointers
  - only alternative is copying on-demand at run-time
  - if we want every function to have the same address, can also just store
    table of basis-method pairs.

These virtual table instances are just structs.

THUS, after emitting C++ code, we can lower further to templated C by
eliminating C++ classes in favor of structures.

THUS, will need to rethink C++ interop, since we would need to generate
C++ wrapper classes around this functionality all over again.
- should not be too tough: can even use aliases of <void*, void*>
- importing C++ >> exporting to C++, and this situation is still not really solved
- this move only creates the option of a better-specified FFI against C++ in the future

