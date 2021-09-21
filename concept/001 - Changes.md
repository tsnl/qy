# Changes

This is Qy v2. Unfortunately, Qy v1 was little more than a compelling prototype.
Qy `v2` will be a smaller, more efficient version of the same in C++.

## Updates

### Templates -> Preprocessor

Unfortunately, templates were a huge problem area for the previous language.

Templates use a lot of 'black magic' to make things work. 
This means that the compiler performs a lot of complex functionality to make things easy.
This creates a system that is seamless, but hard to reason about.

Instead, emphasize trait-implementation systems from the beginning (like Go) since they are
more useful when developing large-scale applications.

Then, use compile-time macros to provide template functionality.

### Load source files from JSON

Rather than use imports, use a nestable 'crate' system similar to Rust.

Namespaces are generated from the directory structure.

Emphasize scriptable toolchains using declarative JSON.

### No more effects-specifiers

Work on something more general and extensible, such as AST tags.

### Top-level only functions or types

Top-level declarations and definitions only deal with types and functions.

## Example

```

```