A Java/C#-level language with... 
- extensive support for type inference and automatic ad-hoc interfaces for that 
  duck-typed feel.
- reference counting and automatic destructors, including weak references
- support for `struct` and `record` datatypes
- mutability specifiers (`mut` is the opposite of C# `readonly`)

Note that both `mut` is a variable-level property that affects whether a slot 
can be re-bound.

Note that `weak` is a type-level property that may return `None`.

```
use Gfx
use Math

const MAX_HEADING: Int = 6283   # (3.14159 * 2) = 6.28318, rounded to 3 places

record Vec2[T]:
  x: Float
  y: Float

variant Bool:
  True
  False

record Robot:
  position: Vec2[Int]
  angle: Int    # in radians * 1e-3
  is_pen_down: Bool

extend Robot:
  function pen_down():
    self.is_pen_down := Bool.True
  
  function pen_up():
    self.is_pen_down := Bool.False
  
  function walk(distance_px):
    src_x = self.x
    src_y = self.y
    dst_x = self.x + distance_px * Math.cos(self.angle * 1e-3)
    dst_y = self.y + distance_px * Math.sin(self.angle * 1e-3)
    src_pt = Vec2f { x: src_x, y: src_y }
    dst_pt = Vec2f { x: dst_x, y: dst_y }
    if self.is_pen_down:
      Gfx.draw_line(src_pt, dst_pt)
    self.position := dst_pt

  function turn_ccw(rotation_deg):
    self.angle := (self.angle + Math.radians(rotation_deg) * 1e-3).to_int()
    self.angle := self.angle % MAX_HEADING
```

```
record FilePosition:
  source_file: SourceFile
  line_index: Int
  column_index: Int

extend FilePosition:
  function to_string():
    "{}:{}".format(self.line_index, self.column_index)

record FileSpan:
  source_file: SourceFile
  first_pos: FilePosition
  last_pos: FilePosition
  
extend IFileSpan:
  function to_string():
    if self.first_pos.line_index == self.last_pos.line_index:
      if self.first_pos.column_index == self.last_pos.column_index:
        self.first_pos.to_string()
      else:
        "{}:{}-{}".format(
          self.first_pos.line,
          self.first_pos.column,
          self.last_pos.column
        )
    else:
      "{}:{}-{}:{}".format(
        self.first_pos.line,
        self.first_pos.column,
        self.last_pos.line,
        self.last_pos.column
      )

extend FilePosition:
  property line:
    get:
      1 + self.line_index
    set:
      assert value >= 1
      self.line_index := value - 1
  property column:
    get:
      1 + self.column_index
    set:
      assert value >= 1
      self.column_index := value - 1

extend FilePosition:
  function to_xml_string() -> String:
    (
      "<position>"
        "<line>{}</line>"
        "<column>{}</column>"
        "<source-file>{}</source-file>"
      "</position>"
    ).format(
      self.line(),
      self.column(),
      self.source_file.to_xml_string()
    )
```

---

## Ideas/Requests

- (MAYBE) <br/>
  Support two different kinds of assignment with operators: by reference and by 
  value.
  - e.g. 
    - use `<-` to copy data from RHS to LHS, use `:=` to alias
    - PROBLEM: how to specify definitions?
    - PROBLEM: unpredictability when interface instance is used
- Support for more common features
  - exceptions, try/catch
  - reflection, at least getting a `__class__` instance

## Type system

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
