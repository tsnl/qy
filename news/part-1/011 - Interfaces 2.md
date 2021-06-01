Interfaces smell an awful lot like type-classes/concepts.
What is the difference?
- by exposing 
  (1) a `virtual_table(Type)` typing expression, and 
  (2) the ability to dynamically refer to a typeclass instance, 
  we could fold interfaces into type-classes.
- by eliminating type-classes, we can still check if types satisfy an interface for a template.
  - 'getter' & 'setter' methods inefficient, but optimizable

IDEA: replace typeclasses with interfaces.
- this means using interfaces to specify template args
- this means using an `IWhatever` object as an alias for `tagged(void*)`
- currying out,
  - every field is accessed with a function that returns that field
  - even a method is a function data field returned by a function

When a field is accessed with `.`, we look up the container type's
field list.
- if the container is a tuple, we expect the key to be an int.
- if the container is anything else, we expect the key to be a string name.
- if the container has any data fields, these are searched first.
- if the container has any 'impl'-ed methods, they are called
  - if the container is not an Interface instance, static lookup suffices.
  - if the container is an Interface instance, 
    - if the method is non-static, use DD table
    - note method may be static

Use `[for ...] extend` to define methods. This gets very tricky.
- for non-interface types, 1-1
- for interface types, must also apply methods to all that satisfy
  the interface using templates rather than DD.
- for `impl/aug` syntax, stick to Rust. 
  
TL;DR: use DD for interface objects, templates for static.

```
VECTOR = Interface [Scalar, dim] {
    Scalar :: NUMBER;
    dim :: Index;
    Index = Int32;
    
    # abstract value fields: must be implemented
    pi :: abstract (Self) -> (Index) -> Scalar;
    
    # provided methods:
    add   :: (Self) -> (Self) -> Self;
    scale ::  (Self) -> Scalar) -> Self;
    dot   :: (Self) -> (Self) -> Scalar;
    length :: (Self) -> Scalar;
    length_sqr :: (Self) -> Scalar;
    dimension :: (Self) -> Index;
};

# Note: Scalar, dim are formal args, reused from `Interface` definition
# and **strictly matching in name**
extend VECTOR [Scalar, dim] {
    # ...
    
    dimension (self) = {
        dim
    };
    
    operator 2+ (self) (other) = {
        self.add(other)
    };
    
    length_sqr (self) = {
        self.dot(self)  
    };
    
    length (self) = {
        self.length_sqr().sqrt()
    };
};

Vector3 = Struct {
    x :: Float32;
    y :: Float32;
    z :: Float32;
};

# this typing must hold true, though the methods may be
# extended from anywhere.
Vector3 :: VECTOR[Float32, 3];
extend Vector3 {
    pi (self) (index) = Float32 {
        if index == 0 {
            self.x
        } else if index == 1 {
            self.y
        } else if index == 2 {
            self.z
        } else {
            # `fail` excludes branch from static analysis
            # by forcing compiler to guarantee will not always run.
            # A kind of imperative symbol that has an effect on the whole chain?
            fail "Invalid index";
        }
    };
};

main () = {
    v1 = struct { x = 0; y = 0; z = 0; };
    v2 = Vector3 { 0, 0, 0 };
    product = v1.dot(v2);
    ok = (product == v1.length());
    if ok {1} else {0} 
};
```

IMPLEMENTATION

- Every datatype gets a `class` data-type in C++.
- Implementation is performed by class mixin
  - need to ensure all methods are virtual
  - C++ optimizes function calls as required
- Represent interface type as ABC, instances with ABC-ptr
  - can access interface methods with ease
  - can expose data members using methods
- Can implement copy constructors for key data-types
  easily (cf. `= default`)

QUESTION
- how do we go from an interface type back to the pointee type?
- in C++, we can `dynamic_cast` back to the sub-most type
- this problem may require solving later.

QUESTION
- how do static methods work?
- need support for `TId.vid` static accessors
- gets increasingly confusing

QUESTION
- would it be better to peel `class` and `abstract`
  into its own thing?
- using methods <=> boxed data-type

QUESTION
- can member-related stuff use a different operator, e.g. `->`?
  - `->` currently used for lambdas
  - `:` was tried before and is too ugly
- `.` refers to...
  - struct fields / tuple fields / enum fields first
  - then any methods that may be defined
  - defined methods that conflict in name should **cause an error**-- but how?
    - if fn defined for all elements satisfying empty interface...
    - just DO it, costly (slow) as it may be
  - then, no overlap is possible, so no confusion
- if accessed member is not a data field, simply forward to C++'s method resolution.
  - should pick up a virtual override implementation
  - we can track implementation to ensure overall typing is correct.
    
QUESTION: how can interfaces be combined?
```
INTERFACE = Interface {
    Self :: BASE_INTERFACE1;
    Self :: BASE_NTERFACE2;
};
``` 
- Rather than allow `|`, just use this for now.
- then `extend INTERFACE` => base class extension 
- then `extend Type :: INTERFACE` => add super-class, check all methods here

QUESTION: why no 'impl ... for X' like in Rust?
```
# this statement checks that the desired interface is 
# satisfied (among others).
# TODO: ensure this block cannot be empty while this interface
#       definition is satisfied, i.e. all definitions cannot be elsewhere,
#       i.e. all abstract methods for this interface must be defined here.
#  - this way, intersecting interfaces cannot even be implemented without
#    explicitly subclassing the origin interface
#  - this creates a sort of 'global uniqueness' of methods that could be 
#    very desirable
#  - on the other hand, could be very bothersome when goal is to implement
#    overlapping interfaces...
#  - thoroughly confusing 
```
Instead, use regular typing operators:
```
Vector3 :: VECTOR[Float32, 3];
```

### Brass Tacks

Implementing this is as straightforward as changing how
type-classes work and adding support for methods.

Unfortunately, intersecting interfaces create an issue for C++
with every interface getting its own base class.
- diamond problem rears its head
- potential solution: each method gets its own ABC, with us static-casting before use.
- renders code basically unusable from C++.
