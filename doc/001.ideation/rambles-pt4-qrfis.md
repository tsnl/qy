# Proposed Extensions: QRFIs

Rambles 1 to 3 describe core language functionality.

Since I have little time, I must carefully prioritize features.

Inspired by PEPs and SRFIs, I will write 'enhancement proposals' for features that
can be implemented _**after**_ the base language is ready.

These will be called `QRFI`s or `Qy Requests for Implementation`, where I am requesting
an implementation of myself.

Not all of these need be approved, and since they are optional in a distribution, 
they must be things the user can **turn on or off**
- easiest way to do this: **feature integers**
- each new `QRFI` is given a singe unique integer.
- each new `QRFI` depends on all prior to it and is extended by all after
- cf std=C11 or C99, but much more granular

Note that the ordering is not significant. The `p#` notation indicates `prototype number`.

I think QRFIs p5, p2, p1 are most important (most to least).

---

## QRFI p1: first-class functions

GNU-C extensions actually support this, so we can just generate function definitions locally.

A more refined approach would involve building our own 
system to capture implicit variables.
- each 'closure' object is just 2 pointers: 
  (proc-code-handle, args)

---

## QRFI p2: dynamic dispatch and traits

In this language, 'interface' is replaced with 'class', as in a category.

Classes are defined in terms of methods they support. 
They do not encapsulate any data. 
Classes may extend other classes.

Any concrete datatype may be 'added' to a class by implementing all the class' methods for the datatype.

Classes are of two kinds: Normative Classes (NClass) and Positive Classes (PClass).
Although both kinds of classes use the same data representation, they are defined in different ways.
-   NClasses admit one fixed set of methods, after which the class' definition is sealed.
    
    If an NClass instance invokes a method that is not included in this body, the compiler generates an error.
-   PClasses automatically expand to allow all used methods.
    
    The compiler will only generate an error if a method is not defined.

PClasses are ideal for writing code in a dynamic style. They facilitate duck-typing.

NClasses are ideal for providing robust interfaces to third-parties.

Note that PClasses admit partial definition blocks that can be aggregated into an NClass later.

Note that in practice...
- all class instances **must be boxed in practice**
- methods must be annotated with `->` instead of `.` for PClass inference to work well.
  - maybe some methods can be 'getters'? 0 arg procedure automatically if method?

```
Vector = class(p);

add_vec_in_place: (&Vector, &Vector) => void;
add_vec (v, w) {
    if v->dim() != w->dim() {
        panic("Whoops");
    } else {
        for i = 0; i < v->dim()-1; i = i+1 {
            v->set_data(v->data(i) + w->data(i));
        };
    };
};
```

**IDEA:** how to go beyond C++?
-   sometimes, method overrides are used to return simple data that could be variables.
-   what if 'classmethods' and 'classdata' were unified, such that the user had more control over the vtable?
-   interfaces would then be typing specifiers upon the vtable.

---

## QRFI p3: template generics

Pretty straightforward, but only admit literal constants for evaluation.

**NOTE:** this may go against the spirit of the language, which seeks polymorphism via run-time facilities.

**NOTE:** this may be a good way to do duck-typing (cf templates in C++).

---

## QRFI p4: static evaluation/multi-phase compilation

Iteratively build and execute the program to evaluate constants at compile-time.

**IDEA:**

If we build a separate 'compile-time' program and execute it, we would have
an efficient way to evaluate code at compile-time, even with a compiler in Python.

The problem is that information is tricky to pass between the compiled program and
the final program.

Perhaps FlatBuffer IDL files can be generated from user data-types for constant 
evaluation, such that...
- each phase except the last uses a generated interface to write its output to a binary file
- each phase except the first may open the previous phase's binary file

---

## QRFI p5: A C FFI mechanism

This is vital to interop with existing C libraries.

---

## QRFI p6: Python interop (maybe via `libffi`)

Allow the user to transparently interoperate with 
Python libraries and code.

---

## QRFI p7: A macro system

This would enable us to turn many QRFIs into libraries.
