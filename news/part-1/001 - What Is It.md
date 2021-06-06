Astropod is an interpreted programming language with a static type system.

In the future, we want to include the ability to generate C++ code from Astropod without compromising on expressivity.

## Basic Spec

- S expressions
  - Symbols are `[A-Za-z0-9-+*%/<>=_]+`
  - top-level just executed for compilation
  - can orchestrate symbols to write in top-level
  - can write symbols in top-level
  - can import modules in top-level (will automatically be written)
- separators group terms into S-expressions
  - use ':' as a pair builder: make pair of LHS, parse RHS until ',' or ';'.
  - terminate each pair with a ',' or a ';', but be consistent!
  - ~~the last item may accept an optional 'tail terminator' separator which may have meaning.~~
  - `;` must always be terinated, whereas `,` must not. Quirky, but useful.
  - need explicit `return` statement for 'enums' if functions specify return types.
  - ~~use new-line as the lowest precedence separator unless between parentheses~~
- no unary or binary operators.
- mutation
  - 'let', 'var', 'set'
- type specification
  - 'val id <typespec>' to specify type
  - types and classes are kinds of expressions that translate into assertions
  - the compiler's job is using these tautological assertions to generate efficient code
- function calls as in scheme
  - no currying by default, can chain lambdas
- beware:

- that's it. no binops, unops, or anything sugary.

- Multiple targets inherent to the language
  - cf `make`

```
import String {cat};
import LinAlg {id1, id2, id3, id4};

target "say-hello" [
    prefix = "Hello "
    name = "John Doe"
    print (String.cat prefix name)
];

target "fibonacci" {
    let n 42;

    let fibonacci: fn (x) {
        if (or (= x 0) (= x 1)) 
            (1)
            (fibonacci(x-1) + fibonacci(x-2))
    };

    print (fibonacci n);
};

target "typed-fibonacci" {
    let n: 42;

    val fibonacci (Fn (Int32) Int32);
};

#
# what about a purely object oriented system?
# - treat instances like entities supported by class 'systems', so no subclassing issues
# - allow operator overloading... the dream.
#
# like Python, treat a Vector3 class like a runtime object, but include enough typing 
# metadata to deterministically construct types or overrides as required.
#
# C++ is this language's primary emission target, so can emit polymorphic, overridden code
# thanks to C++'s impressive strengths.
#

# in this case, we can determine all types from:
# 1. initializer
# 2. usages
# 3. typing specifiers
class Vector3 {
    # even if these are not specified, should still type correctly.
    # val x: Float32,
    #     y: Float32,
    #     z: Float32,
    #     
    #     constructor: Fn (Float32 Float32 Float32) This,
    # 
    #     '+': Fn (This This) This,
    #     dot: Fn (This This) Float32;  
    
    let x: float32(0),
        y: float32(0),
        z: float32(0);

    let constructor: fn (x y z) {
        set x.this x;
        set y.this y;
        set z.this z;
        this
    };

    # can also just specify a string for an ID
    let '+': fn (u v) {
        Vector3 (+ x.u x.v) (+ y.u y.v) (+ z.u z.v)
    }
    let dot: fn (u v) {
        let x-prod (* x.u x.v)
        let y-prod (* y.u y.v)
        let z-prod (* z.u z.v)
        (+ x-prod (+ y-prod z-prod))
    }
};

# OOP-ness gives us...
# 1. consistent type system: 'class' really is a type, and we talk about infinite subtypes of the pointer type when discussing objects.
# 2. 'Class' declarations are instances of a builtin class.
# 3. Operator overloading!

# In module land, how can we achieve dynamic operator overloading?

module Vector {
    let Vector3: struct {
        x: Float32,
        y: Float32,
        z: Float32
    };

    let new_vec3: fn (x y z) {
        Vector3 x y z
    };

    let +: fn (v w) {
        Vector3 
            (+.Float32 v.x w.x)
            (+.Float32 v.y w.y)
            (+.Float32 v.z w.z)
    }
};

# Rethink: use function return values + composable operators to specify types?
# - everything is a value of some sort, and everything is interpreted
# - the interpreted language provides reflection info that makes typing trivial
# - can 'check' for different errors
# - a stock 'check' & emit function can be...
#   1. combined with existing functions to augment static analysis
#   2. used to emit efficient C++ code corresponding to the system in use.

# Assume single-quoted symbols are interned strings, and substitutable for 
# identifiers, unlike double-quoted strings or other string expressions.

# Assume '->' specifies a function

# Assume params must start with '&' or '^' to indicate 'inout' and 'out' resp.
# Assume '.' is postfix specified.

# Note 'or' means a discriminated union of possibilities

let Actors: module () {
    
    let new-actor: (name init-pos) -> struct {
        name: name,
        init-pos: init-pos,
        children: []
    };

    let new-child-of-actor: (&parent child-name child-init-pos) -> Actor {
        let child-actor (new-actor child-name child-init-pos);
        append &parent.children child-actor
    };

};

# What about templates?
# When the type is indeterminate, we can leave it as a free (template) variable
# in C++ which we emit.

# 'assert' remains the only way to validate input.

# templates are not exposed to the user.

# Ok, so how do we specify interfaces?
# - in an ad-hoc way? seems dissatisfying
# - would be great to define dynamic type-classes using 'test' functions
# - this may be the key-- rather than signatures, being able to assert things about functions

# Need to assume 'fn' body and 'val/var' body may be a chain

let RefinedFib: module {

    let positive-int: fn (int) {
        let int: int32 int;
        assert (>= int 0);
        int
    };

    # unary functions can be used as type-specs.
    # their return type is used as the specified type.
    # any assertions that hold in that type's body or called functions adhere as refinements.
    # in case of ambiguity, the compiler generates a union type.
    
    # 'val' type-checking must be kept separate from 'assert' value checking.
    # - if assert is missing a field and 'val' does not check for it, user error.

    # val fibonacci: (Fn (positive-int) positive-int);

    let fibonacci: fn (x) {
        # ...
        # todo: use let x: ...
    }
};

let WeirdRefine: module {

    # creates a function that accepts a unary argument of any of these types,
    # passes it to the appropriate constructor,
    # returns the result as a 'number'.
    let number: (float32 | float64 | int32 | int64 | uint32 | uint64);
    
    # are struct constructors unary operators or N-ary?
    # unary if passed a struct value,
    # which is itself an associative map of IDs to data

    # cannot stress this enough: 'number' is a sum ADT in interpreter world.
    # e.g. Crystal

    # Note that decomposing sum ADTs for efficiency by inlining is an optimization
    # So we can 'template out' our enums for efficiency under the hood-- or not to begin with.
    
    let point: struct {x: number, y: number};

    let pos-point: fn (it) {
        # rather than 'val' or any typing, exploit shadowing + conversion behavior:
        let it: point it;
        assert {
            or
            {and (it.x > 0) (it.y > 0)}
            {and (it.x < 0) (it.y < 0)}
        };
        return it
    };

    let do-something-with-pos-pt: fn (pt) {
        let it: point pt;
        # do something
        return 0;
    };

    let weirdly-typed: fn (pt) {
        cond {
            # FIXME: returns a 'pt', not a boolean, so doesn't work with 'cond'
            (pos-point pt): {
                # is 'pt' now automatically typed as a 'pos-point'? Yes it is!
                # a static analysis tool can use an immutable context set to track changing information
            },
            'else': {
                # in this branch, we know (not (pos-point pt)) from context statically.
                # should this---v function call produce a compile-time type error? If so, how?
                do-something-with-pos-pt pt
            }
        };
    };
};
```

The idea I'm getting at above is...
1. write a simple to interpret but monomorphically typed programming language
2. analyze value types and bounds until they converge to a fixed point
   - just two identical cycles is all it takes.
   - maybe inlining is a bad idea, but we'll figure it out
3. perform this analysis in the language itself via exposed reflection using S-expressions
   - may be difficult initially
   - need a few features first
   - but should be cheap/easy to implement in an interpreter
4. allow the language to use the output of this detailed reflection to generate C or C++ code.
   - Haxe has taught me that adding source targets with a 'platform' requirement is easier than 
     targeting relatively obscure LLVM.
