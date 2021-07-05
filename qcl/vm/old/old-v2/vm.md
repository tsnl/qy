# VM Specification

This document specifies how the interpretation VM works.

It allows us to interpret polymorphic code (i.e., templates) using just-in-time compilation.
- we compile as much code as possible into a byte-code
- the VM lazily evaluates templates

This lets us bake all templates by evaluating the constants needed to generate monomorphic forms.

This makes an excellent debug environment, since code hot-loading is easily achieved.
- currently, we use a fixed-size, linear heap allocator
- this can be swapped out for a `malloc` wrapper or `BDM GC`
- when run in server mode, the compiler can interpret output and hot-load source files as they change,
  allowing users to preview changes.
- with some analysis, we can even identify which state may have been changed to make state-correct reload anywhere a 
  reality.

A monomorphic reduct of this IR is the foundation of 2 key subsequent passes, termed **finishing passes** in this 
document:
1. Z3 analysis: verify termination, no run-time exceptions
2. LLVM IR generation

Note that finishing passes only need to be run when testing or exporting code to users.

Thus, this JIT could be the key to making this language usable:
- use the VM to run the application in debug, and for static evaluation
- use the Z3 analysis to plug away at verifying code in the background
    - ideally, the compiler daemon constantly validates code, even if it takes a while
- only Z3-verified code can be published/exported as LLVM IR, at which point it is guaranteed to not cause any
  runtime errors.
    - this is only possible with strict bounds on maximum stack size
    - this does not guarantee against divergent execution
        - it is up to the user to ensure code does not stall
        - divergent sections are clearly ear-marked, and the compiler will complain if code may diverge
    
## The Virtual Machine

Our model of execution is a virtual machine with several 8-byte (64 bit) registers, a well-defined
byte-code format, and a mutable code segment. 
All work in this module uses a virtual machine as a shared context object.
In other words, it contains (encapsulates) all resources used for interpretation.

### Registers

Each VM possesses 32 integer registers and 32 floating point registers.
We name these registers `x0...x31` and `f0...f31`.

Each register serves a specific purpose.
For simplicity, we use the RISC-V register naming scheme and calling convention, with these restrictions:
- no support for 128-bit, double-register structures.
- no support for `gp` (global pointer) and `tp` (thread pointer), instead used as call-clobbered registers.

These restrictions may be relaxed over time.

A summary of these registers:
- integer registers (`x0`...`x31`)
  - `x0` => `ra`: return address
  - `x1` => `sp`: stack pointer
  - `x2-x11` => `t0-t9`: temporary registers, i.e. caller-saved/call-clobbered
  - `x12` => `s0/fp`: frame pointer (a callee-saved/call-preserving register)
  - `x13-x23` => `s1-s11`: callee-saved/call-preserved registers
  - `x24-x25` => `a0-a1`: caller-saved/call-clobbered arguments, store return values
  - `x26-x31` => `a2-a7`: caller-saved/call-clobbered arguments
- floating point registers (`f0`...`f31`)
  - `f0-f11` => `ft0-ft11`: caller-saved/call-clobbered temporaries
  - `f12-f23` => `fs0-fs11`: callee-saved/call-preserving registers
  - `f0-f1` => `fa0-fa1`: caller-saved/call-clobbered arguments, store return values
  - `f2-f11` => `fa2-fa7`: caller-saved/call-clobbered arguments

### Functions & Basic Blocks

Users can create **functions** in the virtual machine, which are simply a collection of basic blocks identified by a 
`FunctionID`. The user can select an entry point basic block for each function, append more basic blocks, and build 
instructions in each basic block to manipulate registers and break to other basic blocks. In other words, each function
is a small control-flow graph in terms of basic-blocks.

Note that a basic block is definitionally a sequence of control-flow without any branching. Thus, a `br` or `ret`
instruction must be the last instruction inside a basic block.

Instructions exist (`allocate`, `push`, `pop`, `ret`) to allocate (and optionally, de-allocate) memory.

**Note that this memory model is inherently untyped.** This means that all polymorphism, that is, variation in type or
value, is turned into mutating values that we must track dynamically and externally.

**TODO:** rely on **reflection** to dynamically maintain information about defined variables, their location in source
code, and their type (so we can use the right arguments for, say, `lea` instructions)

#### PHI instructions

PHI instructions are borrowed from LLVM (which in turn borrows them from SSA theory).

The result of a PHI branch is always stored in the `ra` or `fa0` register. 
Thus, each 'if' expression is like a function. 

### Poking

While functions can be loaded and executed, the VM may still need to be configured before executing code, or may need to 
be queried for state during debug or emission.

This is achieved using the `poke` family of functions which allow manipulating the VM's state from outside the VM.

### No bit-masking

The VM does not support any bit-masking, allowing the user to load and store only 64-bit words.

All bit-masking can be performed on the host CPU based on the data-type of the value at run-time.
This is a hacky way of evaluating 64-bit arithmetic modulo some constant that is a power of 2, which is theoretically 
sound way of viewing integer overflow.

