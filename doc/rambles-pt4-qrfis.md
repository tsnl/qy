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

## QRFI p1: first-class functions

GNU-C extensions actually support this, so we can just generate function definitions locally.

A more refined approach would involve building our own 
system to capture implicit variables.
- each 'closure' object is just 2 pointers: 
  (proc-code-handle, args)

## QRFI p2: dynamic dispatch and traits

Library level DD is possible using existing 'type' system

Alternatively, may be able to do DD with JAI-'using'-style statements (cf embedding structs in Go)

Alternatively, may be best to use custom DD system for efficient method dispatch.

## QRFI p3: template generics

Pretty straightforward, but only admit literal constants for evaluation.

**NOTE:** this may go against the spirit of the language, which seeks polymorphism via run-time facilities.

**NOTE:** this may be a good way to do duck-typing (cf templates in C++).

## QRFI p4: static evaluation/multi-phase compilation

Iteratively build and execute the program to evaluate
constants at compile-time.

## QRFI p5: A C FFI mechanism

This is vital to interop with existing C libraries.

## QRFI p6: Python interop (maybe via `libffi`)

Allow the user to transparently interoperate with 
Python libraries and code.

## QRFI p7: A macro system

This would enable us to turn many QRFIs into libraries.