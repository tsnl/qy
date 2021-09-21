May 26


## Piecemeal Template Spec

Templates are proving to be a huge problem.
- can't get rid of them: need them for efficient data-structures
- **but template arguments bleed into extensions** 
- need to make them per-binding
    - removes all ambiguity about defining templated methods
    - can still use shared-scope typing by name?
- revive an old idea: explicitly specify the minimum number of formal arguments necessary
- revive an old idea: template args before `=` so identity difference is clear.

IDEA: use `:` for typing _and_ method access.
- because we have separate `vid` and `tid`, we know that `vid` suffix means a method call, while `tid` suffix means a 
  typing op.
- this can be resolved by the parser.
- in practice, the two are not very confusing, even when tersely written.
- similarly, use `::` for static member access _and_ extension
    - extremely effective use of symmetry-- use `::` to extend methods and access them
    - relates `:` as a dynamic sibling, a shorthand for `T::v(x:&T|&mut T)`
    - note we cannot use `:` since `vid:TId` is ambiguous between getting a static type field and typing a VID.
        - strictly relegates `:` to method calls, where RHS is always a value.
    - prioritizes type qualifiers, which affect all variable qualifiers: longer is better in this case.

IDEA: support static methods for types easily by...
- giving each type a namespace (required to check methods anyway)
- allowing all functions to be called in `static` style
- note that `IAnything:method_call(self)(args...)` uses dynamic dispatch thanks to `IAnything`
    - so determined in typer
- note that method existence must be passively checked, 
    - i.e. using an order system since methods could be used before they are defined even in DD order.

NOTE: `Self` must be defined in the RHS of a type extension.
- see below example

NOTE: use `&Interface` and `&mut Interface` to refer to interface instances
- makes more sense, since we pass it a pointer to construct
- may already be in-spec, just reinforcing. :)

TODO: must add back extension-less type typing statement to qualify template variables.

NOTE: if modules no longer accept template arguments, then we can use namespaces.
- namespaces use `vid::ANYTHING` semantics.
- structures automatically ruled out in type-spec queries since they cannot bind types.
    - wouldn't hurt to let the user use value IDs accidentally, since we can point this out.

NOTE: extensions do not accept formal args-- intentional
- an extension type can only depend on the formal args of the type being extended
- see `derp` below

**Thus, each module consists of a sequence of scheme definitions.**

```
Vector2 [Scalar] = struct {
    Scalar :: INumber;
    x: T;
    y: T; 
    z: T;
};
Vector3 [Scalar] = struct {
    Scalar :: INumber;
    x: T;
    y: T;
    z: T;
};

Vector2 [Scalar] :: IField[Scalar] by {
    Scalar :: INumber;

    zero = Self(0, 0);
    one = Scalar::from_float_literal(1f);
    scale_by = (v, s) -> { Self(v.x * s, v.y * s) };
    add = (v, w) -> { Self(v.x + w.x, v.y + w.y) };
    
    zero: Self;
    one: Scalar;
    scale_by: (Self, T) -> Self;
    add: (Self, Self) -> Self;
};
```


## Derp

The above is an unnecessary solution.

- each module accepts some template arguments
- the old spec restricts us to extending one monomorphic type at a time
    - if the extended type is defined in this module, it may be a polymorphic symbol, 
      **but all in-scope template args are shared between the extension body and the extended type**
    - if the extended type is not defined in this module, the type specifier **must select** a unique monomorph
      in terms of the defined typing variables
      
        ```
        Dict[String, PolyValueType] :: IContext by {
            # ...
        }
        ```
    - this means that every module instantiation **produces monomorphic methods only.**
- when a method involving polymorphic symbols is invoked, either:
    1. it was invoked **statically**, through an instantiated scheme (so formal args reified before), OR
    2. it was invoked **dynamically**, using an instantiated type (aka a value)
        - but since methods are only defined on monomorphic instances
        - and since the type of the instance is known
        - we can infer the types of all needed variables from context

BUT What about...

```
params [...]

T = I32;

T :: IAnything[Param1, Param2, Param3] in {
    do_something = (param1) -> {
        param1: Param1;
    };
};
```

In the above example, the type of `T::do_something` cannot be inferred from the type of `T` alone.

HOWEVER, it _can_ be inferred from the type of `module[args...]::T::do_something`
- and furthermore, since `T` instances do not depend on these formal args, any instantiation should
  require the user to fill these args in.
- this is **an interesting way to preserve contextual information**

**THUS** we encode template args in values for method calls, and it all seems to work out just fine?

I will take the syntax changes from above, though, regarding `:` and `::`.

---

## CONCLUSION

- maintain existing module-level template system
- use [024 - Back to Work.md](024 - Back to Work.md) to start adding features, building up to emitting C++ code.
    - crude versions at first will do.
- can then focus on Z3, testing, and adding more features.
