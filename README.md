# Qy Lang

(WIP, highly unstable)

Qy is a gradually-typed programming, message-based programming language that 
aims to provide the convenience of Python without compromising on control or
performance.

Gradual typing is the union of dynamic and static typing. Variables lacking any
user type specifiers rely on type inference or dynamic typing to be determined.

It is compiled ahead-of-time and can be deployed anywhere that languages like
C, C++, Rust, Swift, or Zig can be deployed.

## Setup

Qy is a compiled programming language. The compiler is written in Rust.

Use the `cargo` build tool to compile `qbt`, the Qy build tool. Once built, the
`qbt` executable can be used to build Qy packages.

## Usage

Run `qbt --help` to print help, and go from there (WIP).
