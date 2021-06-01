# 020 - Del Scoper

May 13

## Del Scoper

While implementing Algorithm W of HM type inference, 
I realized that the type-checker handles lookup up IDs.

Since we re-compute these frames/contexts anyway, exploit mutability
and nesting.
- since bound variables are not replaced, can use a `parent` pointer to track
  context chains, as in scoper.
- substitutions that apply to the parent context are totally valid. Keeping a copy
  means new substitutions must be returned.
- INSTEAD, use one mutating dictionary.

THIS MEANS the scoper can be erased in favor of a single type analysis pass that
also checks if symbols are defined.

NOTE: may be easier to keep existing scoper code and build typer on top of it.

## Out-of-order definitions > Shadowing

Since this feature is only supported in modules, and since submodules are removed,
the only case where symbols may be accessed out-of-order is for a module/source file.

This creates an issue where typing statements in chains may not have an LHS to refer to.

Cannot defer typing statements to the end of a scope because of shadowing rules.
If shadowing is removed, can simply 'delay' typing statements.

REMOVE SHADOWING IN CHAINS. This allows chains to be typed as naturally as modules.

## Prohibit Nonlocal Typing

As a code-hygiene safety measure, prohibit typing symbols UNLESS in the table they
are defined/initialized
- allows us to use `x: T` to unambiguously denote fields in `struct{}`, `enum{}`
    - otherwise, what if typing something in outside scope?
- almost every use-case involves using both in the same table
- still works to type function arguments individually, while typing function symbols
  outside
    - creates 1 unambiguous way to do the same thing from inside or outside a function

## Templates

Permit templates for modules/source-files using a `params <...>` declaration.
- This is required for efficient containers: imagine `Vector[T]` storing boxed pointers...
  like Java.

Instantiate templates in modules using `mod_name<...>::mod_id`.

## Memory Management

Provide a standard library module called `allocate<T>` with at least 3 endpoints:
- `stack`: allocate memory for `T` on the stack
- `heap`: allocate memory for `T` on the heap, must call `free` to dispose.
- `gc`: allocate memory for `T` on the managed heap (`bdmgc`), optionally can call `free` to dispose.
- note `free` must be re-entrant, i.e. a pointer, once freed, becomes `nullptr`, and freeing `nullptr` alone is OK.

Thus, the language offers _optional_ garbage collection as well as very nitty-gritty
memory management capabilities. This creates a smooth ramp between prototypes and 
production code.

```
imports {
    alloc from "$/std/alloc" exposing {stack, heap, gc, free}
};
```

## TODOs

1. Remove the scoper, leaving behind only the typer and its sub-modules in the modeler
2. Implement the typer
    - (rename 'scoper' to 'typer' and merge with existing typer)
    - change `p2_typer.context.Context` to work in a stack/linked-list/tree fashion
    - allow typer to push/pop contexts
    - no need for `ContextStrip` as in scoper since shadowing removed (see above)
    - each 'typer' instance has an active `Context` that can be used for substitutions
        - every parent context has substitutions applied too (sub-contexts)
        - changing 'top' can exclude 'popped frames' from substitutions with ease
    - continue following YouTube guide for HM type inference
        - can use type schemes for monads like ptr, mut, or struct/tuple/enum...
        - keep general `Scheme` system rather than hacking on more
        - apply typing rules + unify
        - NOTE: when multiple modules, all one binding group
        - NOTE: even if holes present, can still solve with `IAny`
        - NOTE: since this inference is wholly local, the final/assignable type should be known at the end of a context/table
    - assign/store finished types on AST nodes

Once typing is complete, still need to verify that...
1. type solutions have finite size
2. mutability rules are respected
3. invalid pointer uses or fatal errors/exceptions do not occur (using Z3)

Despite this, will have sufficient information to emit C++ code if input is valid.
- i.e., despite imperfect checking, type synthesis for valid cases will mostly be in place.
