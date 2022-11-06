Instead of an `Any` type, consider instead an `Auto` type
- when type specifiers are omitted, default to `Auto` which creates a fresh type
  variable.
- switch to an OO-style model to achieve qualified subtyping polymorphism;
  only support `abstract`, `type` instances, can define methods either in the
  `type` body or an `amend` block
  - traits are a set of constraints on a type; may intersect
  - trait constraints require either methods or fields
- the `Auto` type solves to a concrete type if possible, else a `Trait` that may
  be anonymous/ad-hoc.

```
IFileLocation: interface =
  source_file: SourceFile
  to_string(self) -> String

FilePosition with IFileLocation =
  source_file: SourceFile
  line_index: Int
  column_index: Int

  to_string(self) =
    "{}:{}".format(self.line_index, self.column_index)

FileSpan with IFileLocation =
  source_file: SourceFile
  first_pos: FilePosition
  last_pos: FilePosition

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

extend FilePosition
  line(self) =
    1 + self.line_index
  column(self) =
    1 + self.column_index

IXmlSerializable: interface =
  to_xml_string(self) -> String

extend FilePosition with IXmlSerializable
  to_xml_string(self) -> String =
    "<position><line>{}</line><column>{}</column><source-file>{}</source-file></position>".format(
      self.line(),
      self.column(),
      self.source_file.to_xml_string()
    )
```

```
List[TContent] =
  head: TContent
  tail: List[TContent] | Null
```

The following two functions are identical; note that 'Auto' will probably
resolve to an ad-hoc trait bearing methods `__mul__`, `__eq__`, 
`__sub__` based on usage in definition.

Cannot default resolve to an ad-hoc trait for monomorphic binding cases; 
should try to find the most monomorphic type satisfying a join.

```
factorial1(x) =
  if (x == 0 or x == 1)
    1
  else
    x * factorial1(x - 1)
  
factorial2(x: Auto) -> Auto =
  if (x == 0 or x == 1)
    1
  else
    x * factorial2(x - 1)
```

Implementation
- every instance is boxed by default; keep `*T` notation to forcably unbox, `*v`
  to copy.
- instances of `abstract` are exactly like `interface` instances in Go; when
  converting to an `abstract` instance, we specify a V-table at compile-time.

**Cast-free programming = dynamic feel, statically typed implementation** <br/>
Casts are only required if static type information affects behavior.
Dynamically typed languages do not support casts because all behavior is 
purely dependent on runtime type information, e.g. dynamic dispatch.
A manifestly typed language without any casts feels like a dynamically typed
language.
