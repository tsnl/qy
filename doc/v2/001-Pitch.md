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
const MAX_HEADING: Int = 6283   # (3.14159 * 2) = 6.28318, rounded to 3 places

struct Vec2[T]:
  x: Float
  y: Float

variant Bool:
  True
  False

record Robot:
  mut position: Vec2[Int]
  mut angle: Int    # in radians * 1e-3
  mut is_pen_down: Bool

extend Robot:
  pen_down(self):
    self.is_pen_down := Bool.True
  
  pen_up(self):
    self.is_pen_down := Bool.False
  
  walk(self, distance_px):
    src_x = self.x
    src_y = self.y
    dst_x = self.x + distance_px * Math.cos(self.angle * 1e-3)
    dst_y = self.y + distance_px * Math.sin(self.angle * 1e-3)
    src_pt = Vec2f { x: src_x, y: src_y }
    dst_pt = Vec2f { x: dst_x, y: dst_y }
    if self.pen_down:
      Gfx.draw_line(src_pt, dst_pt)
    self.position := dst_pt

  turn_ccw(self, rotation_deg):
    self.angle := (self.angle + Math.radians(rotation_deg) * 1e-3).to_int()
    self.angle := self.angle % MAX_HEADING
```

```
interface IFileLocation:
  source_file: SourceFile
  to_string(self) -> String

record FilePosition:
  source_file: SourceFile
  line_index: Int
  column_index: Int

extend FilePosition with IFileLocation:
  to_string(self):
    "{}:{}".format(self.line_index, self.column_index)

record FileSpan:
  source_file: SourceFile
  first_pos: FilePosition
  last_pos: FilePosition
  
extend IFileSpan with IFileLocation:
  to_string(self):
    if self.first_pos.line_index == self.last_pos.line_index:
      if self.first_pos.column_index == self.last_pos.column_index:
        self.first_pos.to_string()
      else:
        "{}:{}-{}".format(
          1+self.first_pos.line_index,
          1+self.first_pos.column_index,
          1+self.last_pos.column_index
        )
    else:
      "{}:{}-{}:{}".format(
        1+self.first_pos.line_index,
        1+self.first_pos.column_index,
        1+self.last_pos.line_index,
        1+self.last_pos.column_index
      )

extend FilePosition:
  line(self):
    1 + self.line_index

  column(self):
    1 + self.column_index

interface IXmlSerializable:
  to_xml_string(self) -> String

extend FilePosition with IXmlSerializable:
  to_xml_string(self) -> String:
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
