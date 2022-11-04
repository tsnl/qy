use std::collections::*;

use crate::parser::TokenInfo;

mod ast;
mod fb;
mod source;
mod intern;
mod parser;

fn main() {
  let filepath = "test/lexer_test_01.txt";
  println!("Begin token dump");
  let mut intern_manager = intern::Manager::new();
  for token in parser::scan(&mut intern_manager, filepath) {
    match token.info() {
      TokenInfo::ValueIdentifier(id_intstr) => {
        println!("- VID {}", intern_manager.lookup(*id_intstr));
      },
      TokenInfo::TypeIdentifier(id_intstr) => {
        println!("- TID {}", intern_manager.lookup(*id_intstr));
      }
      _ => {
        println!("- {:?}", &token);
      }
    };
  }
  println!("End token dump");
}
