Every object has a virtual table that is...
- shared for all instances of a type
- const, meaning it is fully determined at compile-time, used for type-
  inference, and can be optimized out for monomorphic type instances.

Rather than any interfaces or subtyping to resolve joins, use type-inference and
unions. If a field or method is accessed on a union type, we check at 
compile-time that all instances of that type possess the used field or method.
Can match out type instances with the `v is T` operator and smart-casts 
(any variable references are automatically shadowed in conditional blocks).

Every type definition is just a record type. By default, every instance is an
object of the form `struct { VirtualTable* vtab; Content content; }` where 
`vtab` is common for all objects and `content` is type-dependent. 
Monomorphs can be optimized by pre-computing all `vtab` lookups, but this does 
not eliminate the `vtab` field. Each `vtab` instance is implemented as a 
hash-table keyed by interned symbols.

When a field or method is accessed in a `record` type, we resolve the field by
invoking a method from the virtual-table. This field lookup can be performed at
compile-time, so the hash-map lookup is guaranteed to be elided.

When a field or method is accesed in a `union` type, the type-checker ensures 
that all disjunctand types have the accessed field or method at compile-time.
At run-time, we perform dynamic dispatch, looking up the specific field or 
method's function using the virtual table. Any typing information about 
arguments and return types is also broadcast to all fields and methods of 
disjunctands. This technique is used for operator overloading too.

Type-specifiers are used to restrict the types of specific values and are 
checked against user types. If a type-specifier is omitted, the compiler infers
a suitable type, creating 'union' instances rather than joining. This forbids
all dynamic dispatch, but serves as a powerful optimization tool.

Thus, a typical user story is to begin with un-annotated arguments for a 
function, then to specify type arguments as monomorphic records, refactoring as
required.

```
Vector3_V1 (x, y, z)
Vector3_V2 (x Float32, y Float32, z Float32)
```

```
Vector2(x Int, y Int)

Float = Float32 | Float64
Number = Int | Float

Vector2 has:
  fn add (other Vector2) -> Vector2:
    Vector2(self.x + other.x, self.y + other.y) 

  fn scale (other Number) -> Vector2:
    if other is Int:
      Vector2(self.x * other, self.y * other)
    else:
      assert other is Float
      Vector2(Int(self.x * other), Int(self.y * other))

  fn dot (other Vector2) -> Int:
    self.x * other.x + self.y * other.y

  property length Int:
    get:
      self.dot(self)

Flags(v Int)

is_pen_down_flag = 0x1

Flags has:
  property is_pen_down Bool:
    get:
      self & is_pen_down_flag
    set:
      if value:
        self.v := self.v | is_pen_down_flag
      else:
        self.v := self.v & ~is_pen_down_flag
```

A more aggressive optimizing compiler can implement virtual tables using arrays
instead of hash-maps, but this is hard!
- this can be modeled as generating an automatic interface instance used by
  several union types.
- transforming from one interface instance to another interface instance is 
  expensive, but if we avoid this by unifying interfaces, we risk extremely 
  sparse interfaces in most cases.

Built-in data-types:
- `Char`, `Int`, `Long`, `Float32`, `Float64`
- `List{T: ?}`, `Dict{K: ?, V: ?}`
