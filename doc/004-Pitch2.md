Instead of an `Any` type, consider instead an `Auto` type
- when type specifiers are omitted, default to `Auto` which creates a fresh type
  variable.
- switch to an OO-style model to achieve qualified subtyping polymorphism;
  only support `abstract`, `type` instances, can define methods either in the
  `type` body or an `amend` block
  - traits are a set of constraints on a type; may intersect
  - abstract constraints require either methods or fields
- the `Auto` type solves to a concrete type if possible, else a `Trait` that may
  be anonymous/ad-hoc.

```
abstract FileLocation =
  source_file: SourceFile
  to_string(self) -> String

type FilePosition(source_file: SourceFile, line_index: Int, column_index: Int) with FileLocation =
  to_string(self) =
    "{}:{}".format(self.line_index, self.column_index)

type FileSpan(source_file: SourceFile, first_pos: FilePosition, last_pos: FilePosition) with FileLocation =
  to_string(self) =
    if (self.first_pos.line_index == self.last_pos.line_index)
      if (self.first_pos.column_index == self.last_pos.column_index)
        self.first_pos.to_string()
      else
        "{}:{}-{}".format(
          1+self.first_pos.line_index,
          1+self.first_pos.column_index,
          1+self.last_pos.column_index
        )
    else
      "{}:{}-{}:{}".format(
        1+self.first_pos.line_index,
        1+self.first_pos.column_index,
        1+self.last_pos.line_index,
        1+self.last_pos.column_index
      )

amend FilePosition
  line(self) =
    1 + self.line_index
  column(self) =
    1 + self.column_index

abstract XmlSerializable =
  to_xml_string(self) -> String

amend FilePosition with XmlSerializable
  to_xml_string(self) -> String =
    "<position><line>{}</line><column>{}</column><source-file></source-file></position>".format(
      self.line(),
      self.column(),
      self.source_file.to_xml_string()
    )
```

```
type List[TContent] =
  head: TContent
  tail: List[TContent] | Null
```
