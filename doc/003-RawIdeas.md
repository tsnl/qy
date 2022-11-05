## Indentation Based Syntax (APPROVED)

Both curly braces and do-end blocks suffer two disadvantages:
- poor vertical space density: 'end' or '}' typically occupies its own line.
- incongruence with indentation, which is what we use to read

The only advantage provided is the ability to stack multiple blocks in
the same indentation level-- not used, and better served by functions.

Instead, implement indentation based syntax.

Since this requires a custom lexer and since ANTLR's generated indentation
handler is very slow, it would be better to write this lexer and parser by
hand in Python or C. This would allow us to compare Qy vs. Py in good faith 
since Python's great strength is being able to use C extension modules where Python is lacking. I have no interest in self-hosting. Maybe start with 
Python, then move to C if needed? 

This also opens up using `{...}` as a new compound term.

## Refinements & type-states

How do we model the following case without subtyping:

```
class Requirement(abc.ABC):
    pass

class GitRequirement(Requirement):
    pass

class FilesystemRequirement(Requirement):
    pass
```

Can use composition to make the specialized types encapsulate an object with
properties shared by all requirements.

Can use refinements on a single field to further sub-divide variations of a
value. This would probably be checked at run-time (at least until the 
distant future), but allows us to encode type-states and allows us to 
minimize run-time type-checking overhead for such cases automatically.

## Cast-free programming

Casts are only required if static type information affects behavior.
Dynamically typed languages do not support casts because all behavior is 
purely dependent on runtime type information, e.g. dynamic dispatch.
A manifestly typed language without any casts feels like a dynamically typed
language.

See [004-Pitch2.md](./004-Pitch2.md).

## Missing Features/questions

Exceptions?
- destructors means stack unwinding, otherwise could use signals
- see: https://mapping-high-level-constructs-to-llvm-ir.readthedocs.io/en/latest/exception-handling/index.html

Global variables?
- not supported => safe, but inconvenient
- supported, maybe with a Scala-style object

Control flow?
- break, continue in loops
- short-circuiting return

Variadic arguments? Keyword arguments?
