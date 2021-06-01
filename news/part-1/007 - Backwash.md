May 2, 2021

I've had ideas about `1.0` given the ideas discussed for `1.1`.

## Simpler Type-classes

Typeclass declarations can be simplified using the `Self` keyword, and by
eliminating the module parameter.

Rather than use `=` like TID and VID, instead use `:-` to bind.

## WIP

Added a lot more AST functionality, this time building the tools we need for
the rest of compilation early.

- todo: complete parsing type-specs
- todo: complete parsing class-specs

Added ability to read command line args.

Should transition to a server-based model to implement good feedback.
- cf. LSP (Language Server Protocol) REST API for VSCode integration, general architecture.
- generate feedback messages as a tree of notes/annotations
- consider how feedback is re-generated as new modules are parsed
- not a high priority: use 'print' and 'todo' until the guts work.