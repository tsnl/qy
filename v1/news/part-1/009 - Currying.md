Basic allows the user to omit parentheses when calling a unary function.

Extending this idea, what if all functions were unary, and accepted tuple arguments?
- fits into the idea of 'streamlining'-- arg packs are just expressions
- simplifies syntax when ~~defining, typing, and~~ calling unary functions.
- creates possibility for currying in the future
- easy to parse (in correct order of application) thanks to ANTLR
 
Currying can be a very useful feature. Not so in the below example. My apologies.

The only complication is that lambdas may accept more than
one argument pattern.
- it is imperative that return expressions use chains to distinguish pattern args from
  return body without a separator.
  - the 'first' of a pattern is always a paren
  - the 'first' of a chain expression is always `{`

IDEA: keep 'unsimplified' postfix function call syntax.
- then function-call chains explicit
- looks like C/Python
- while preserving all the power of Currying from functional programming.
- `f(...)` with parentheses strongly connotes a function call.
  this makes it more readable during definition and use.
- always using parentheses means that as expressions expand, they do not need to be parenthesized correctly.
  - avoids some arguments looking different than others.
  - makes nested evaluation supremely obvious
- always use parentheses for all args when defining.
- always use parentheses for all arg types when specifying.

A useful decomposition step is that each function is UNARY, meaning
it accepts an argument of 1 unique data-type.
- if only one argument type is provided at definition or as a pattern arg, this is
  the argument type itself.
- if multiple types are provided (e.g. comma separation), then a tuple is the argument.
- we can encode postfix function call as:
  - `expr tupleOrParenExpr`
- we can encode lambdas with the `->` binary operator
  - if `=>`, will clash with `=`, impairing readability.
  - note args must be wrapped in parens, even if only 1.
- we can encode type specifiers with the `=>` binary operator
  - does not clash with `=` since not used by type specs.
- binary lambda operator is easy to desugar to.

How do lambdas specify closures? 
- Always by value, always immutable (but may be pointers)
- Want to close over a value mutably? 
  Take an immutable pointer and use that. 

NOTE: once tuples play an important role, 
we **need a way to unwrap tuples** while binding.
- currently, the bind operator assigns only one element.
- can be expanded to do so easily, but changes a few assumptions.

```
hello = module {
    flat_sum (x) (y, z) = {
        x + y + z
    };
    
    encode_pair (x, y, z) = {
        flat_sum x (y, z)
    };
    
    decode_pair (pair) = {
        # unwrapping 'bind' syntax:
        (x, (y, z)) = pair;
    }
    
    y_plane (point_list) (y_value) = {
        # below lambda just to demo multi-arg lambdas,
        # could also use `filter_fn px (py, pz)` as above.
        filter_fn = (px) -> (py, pz) -> {
            py == y_value
        };
        point_filter(point_list)(filter_fn)
    };
    
    point_filter (point_list) (filter_fn) = {
        adapter_filter_fn (px, py, pz) = {
            # unwrapping 'bind' syntax:
            (x, yz) = encode_pair(px, py, pz);
            filter_fn(x)(yz)
        };
        filter(point_list)(adapter_filter_fn)
    };

    # type specifiers written after the fact,
    # usually written on top for clarity:
    Point = (Float32, Float32, Float32);
    
    flat_sum :: (Float32) => (Float32, Float32) => Float32;
    encode_pair :: (Float32, Float32, Float32) => Float32;
    decode_pair :: (Float32, (Float32, Float32)) => Float32;
    y_plane :: (IList[Point]) => (Float32) => Point;
    
    # point_filter :: 
    #   (IList[Point]) => 
    #   ((Float32) => (Float32, Float32) => UInt1)) => 
    #   IList[Point];
    FilterFnType = (Float32) => (Float32, Float32) => UInt1;
    point_filter :: (IList[Point]) => (FilterFnType) => IList[Point];
};
```
