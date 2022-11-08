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

mutable record Robot:
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
interface IFileLocation:
  source_file: SourceFile
  to_string() -> String

record FilePosition:
  source_file: SourceFile
  line_index: Int
  column_index: Int

extend FilePosition with IFileLocation:
  function to_string():
    "{}:{}".format(self.line_index, self.column_index)

record FileSpan:
  source_file: SourceFile
  first_pos: FilePosition
  last_pos: FilePosition
  
extend IFileSpan with IFileLocation:
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

interface IXmlSerializable:
  function to_xml_string() -> String

extend FilePosition with IXmlSerializable:
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