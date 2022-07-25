pub mod ast;
pub mod fb;
pub mod intern;
pub mod tune;
pub mod src;

mod frontend;
mod error;

mod compiler;
use std::str::FromStr;

use compiler::*;

extern crate pest;
#[macro_use]
extern crate pest_derive;

fn main() {
    let mut compiler = Compiler::new();
    compiler.compile(String::from("/home/nti/Workshop/qy/qy-v7.0/sandbox/eg002.qlib"));
    println!("Hello, world!");
}
