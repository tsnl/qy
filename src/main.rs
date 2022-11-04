use std::collections::*;

mod ast;
mod fb;
mod source;
mod intern;
mod parser;

fn main() {
  let filepath = "test/lexer_test_01.txt";
  println!("Begin token dump");
  for token in parser::scan(filepath) {
    println!("- {:#?}", &token);
  }
  println!("End token dump");
}
