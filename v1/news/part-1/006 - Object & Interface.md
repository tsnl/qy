May 1

Re [005 - Constructors](005 - Constructors.md),

### Part 1: `Object` -> `Module`

**REJECTED:**
1. rename `Object` -> `Module` such that
   - modules now expand to encompass pre-described Object behavior
     - consider `self` and `Self`
     - consider accessing module members using `.`
   - modules can be instantiated and assigned to, but not moved, since...
   - modules are **reference counted**
   - modules now support initializers.
2. rename `module` -> `new` such that instantiating modules invokes
   a module constructor by type name.
3. allow `new Module {...}` for singletons.
4. operator overloading shadows an operator 

**WHY REJECT:**
- operator overloads on modules? icky
- modules implementing interfaces seems like a good idea, but not really; keep modules like singleton value namespaces.
- most modules don't need a value constructor-- static args better 
  for aot analysis.

**GOOD THOUGH:**
reference counting modules creates a risk of creating cycles that may
never get disposed.
- orphaned cycle disposal must be performed in a well-defined order
  at the end of scopes, when the user expects destructors to run.

### Part 2: Rusty Traits

What does an interface look like?
- `Struct` relies on the user typing an unbound variable.
- `Interface` may rely on the same principle?

Perhaps better if both also acquired a `self` context?
- disallow `self.TId` => structs cannot have type fields
- but creates incongruity with modules
- perhaps better to explicitly annotate `nonlocal/global` typing ops.

What if no objects, just traits?
- interface data-type automatically boxes pointers to contents
- implement with `<interface> for <type-name>`
- give structures, enums their own constructors

So,
1. implementation defines to a special, compiler-managed module
2. module is looked up for operator overloads (without vtable based on static type)
3. pointer to module & pointer to data => fat ptr for interface data-type.
4. interfaces are not reference-counted by default, use DD for dtor.
5. allow templates for struct, 

```
IShape2D = Interface [Scalar] {
    Scalar :: NUMBER;

    BoundingBox = Struct {
        min_x :: Scalar;
        min_y :: Scalar;
        max_x :: Scalar;
        max_y :: Scalar;
    };

    area :: Fn () Scalar;
    perimeter :: Fn () Scalar;
    bounding_box :: Fn () BoundingBox;
};

Rectangle = Struct [Scalar] {
    width :: Scalar;
    height :: Scalar;
};

# The `:: <interface> {...}` operator is used to implement traits 
# for a type
Rectangle :: IShape2D[Scalar] {
    # can name 'Scalar'----^ something else too

    area :: Fn (Self) Scalar;
    perimeter :: Fn (Self) Scalar;
    bounding_box :: Fn (Self) BoundingBox;

    area (self) = {
        width * height
    };
    perimeter (self) = {
        2 * (width + height)
    };
    bounding_box (self) = struct {
        min_x = 0;
        min_y = 0;
        min_x = width;
        min_y = height;
    };
};

print_shape :: Fn (IShape[Int32]) Void; 

print_shape (shape) = {
    print_str("Area: ");
    print_i32(shape.area());
    print_ln();

    print_str("Perimeter: ");
    print_f32(shape.perimeter());
    print_ln();
};
```
