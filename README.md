# Qy Lang

(WIP, highly unstable)

Qy is a gradually-typed, message-based programming language that aims to provide 
the convenience of Python without compromising on control or performance. 

Gradual typing is the union of dynamic and static typing. Variables lacking any
user type specifiers rely on type inference or dynamic typing to be determined.

Python applications are brittle until exhaustively tested, painful to deploy, 
and are not efficient enough to scale to many use-cases, e.g. games, 
simulations, and other low-latency applications. Qy aims to solve these 
problems. Static type-checking improves robustness before any tests are run.
Ahead-of-time compilation enables easy and compact binary distributions. 
Gradual typing automatically allows the user to blend dynamic and static typing
with confidence that the compiler/runtime will use any available constraints for
optimization. This is a better set of trade-offs than pure dynamic typing or 
rigid static typing for most applications.

## Setup

Qy is a compiled programming language. The compiler is written in Rust.

Use the `cargo` build tool to compile `qbt`, the Qy build tool. Once built, the
`qbt` executable can be used to build Qy packages.

## Usage

Run `qbt --help` to print help, and go from there (WIP).
