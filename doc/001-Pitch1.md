A Java/C#-level language with... 
- extensive support for type inference and automatic ad-hoc interfaces for that 
  duck-typed feel.
- reference counting and automatic destructors, including weak references
- classes
  - the 'class' definition is actually identical to a 'trait' definition in 
    other languages; constructors must provide anonymous record instances that
    must satisfy a specified trait. <br/>
    A basic implementation uses dynamic dispatch to resolve all fields and
    methods, but for function calls, we can optimize by treating the trait/class
    as a typeclass (static polymorphism) rather than a dynamic one.
  - if 'self' keyword is the first argument, then method, else 
    static/classmethod.
- mutability specifiers (`mut` is the opposite of C# `readonly`)

Note that both `mut` is a variable-level property that affects whether a slot 
can be re-bound.

Note that `weak` is a type-level property that may return `None`.

```
class Vec2(Object):
  x: Int
  y: Int

  def new(cls, x, y):
    Vec2 { x: x, y: y }

  def add(self, other):
    Vec2.new(self.x + other.x, self.y + other.y)

# angle in radians * 1e-3
class Robot(Object):
  mut position: Vec2
  mut angle: Int
  mut is_pen_down: Bool
  
  def pen_down(self):
    self.is_pen_down := True

  def pen_up(self):
    self.is_pen_down := False

  def walk(self, distance_px):
    src_x = self.x
    src_y = self.y
    dst_x = self.x + distance_px * Math.cos(self.angle * 1e-3)
    dst_y = self.y + distance_px * Math.sin(self.angle * 1e-3)
    src_pt = Vec2(src_x, src_y)
    dst_pt = Vec2(dst_x, dst_y)
    if self.is_pen_down then
      Gfx.draw_line(src_pt, dst_pt)
    self.position := dst_pt

  def turn_ccw(self, rotation_deg):
    # 2pi = (2 * 3.14159) = 6.28318, rounded to 3 places
    max_heading = 6283
    self.angle := (self.angle + Math.radians(rotation_deg) * 1e-3).to_int()
    self.angle := self.angle % max_heading

  def draw_square():
    robot = Self {
      position: Vec2.new(0, 0),
      angle: 0,
      is_pen_down: false
    }
    robot.pen_down()
    for _ in range(4):
      robot.walk(side)
      robot.turn_ccw(Int.from_float(Math.pi / 2 * 1000))
    robot.pen_up()


def main():
  Robot.draw_square()
```

```
class FileLoc:
  def to_xml_string(self)
  get magic_attribute(self)
  def describe()

class FilePosition(FileLoc):
  source_file: SourceFile
  line_index: Int
  column_index: Int

  def to_string(self):
    "{}:{}".format(self.line, self.column)

  get line(self):
    1 + self.line_index

  get column(self):
    1 + self.column_index
  
  set column(self, value):
    assert value >= 1
    self.column_index = value - 1

  get magic_attribute(self):
    line_index + column_index

  def to_xml_string(self) -> String:
    (
      "<position>"
        "<line>{}</line>"
        "<column>{}</column>"
        "<source-file>{}</source-file>"
      "</position>"
    ).format(
      self.line,
      self.column,
      self.source_file.to_xml_string()
    )
  
  # Static methods are indicated by a missing `self` keyword.
  # They can be accessed with the `Self.<method>` accessor.

  def describe() -> String:
    "FilePos"


class FileSpan(FileLoc):
  source_file: SourceFile
  first_pos: FilePosition
  last_pos: FilePosition

  def to_string(self):
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

  get magic_attribute(self):
    first_pos.magic_attribute + last_pos.magic_attribute

  # ...
```

---

## Ideas/Requests

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
not eliminate the `vtab` field. Each `vtab` instance is implemented as an array
lookup table. Offsets are determined at compile-time.

By default, each record instance is allocated in a box and is aliased on 
assignment. To support automatic unboxing for immutable/readonly slots, we need
a special flag to indicate when instances are allocated in-line with other
instances (or on the stack). We still run a destructor when strong refcount goes
to 0, return None for any persistent weak references; just don't free the memory
occupied by this object directly. E.g. call `CAN_DEALLOCATE_PTR` flag. Automatic
unboxing fails when (1) slot is marked 'mut', or (2) unboxing this slot would
result in an infinite-size type.

Type-specifiers are used to restrict the types of specific values and are 
checked against user types. If a type-specifier is omitted, the compiler infers
a suitable type, creating 'union' instances rather than joining. This forbids
all dynamic dispatch, but serves as a powerful optimization tool.

Thus, a typical user story is to begin with un-annotated arguments for a 
function, then to specify type arguments as monomorphic records, refactoring as
required.

Re polymorphic types, omitting the polymorphic arguments tells the typer to 
solve for an appropriate type argument, effectively making this unspecified.

Summary of built-in types:
- `Char`, `Int`, `Long`, `Float`, `Double`
- `String`
- `List[T]` `HashSet[T: ?]`, `HashMap[K: ?, V: ?]`
- `weak T`

NOTE: function signatures include argument names so that the `(name: val)` 
pattern works correctly. This is also used to supply arbitrary arguments to
templates for parametric polymorphism.
