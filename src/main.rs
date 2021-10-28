// pest tutorial:
// https://pest.rs/book/examples/csv.html

extern crate pest;

#[macro_use]
extern crate pest_derive;

use pest::Parser;

#[derive(Parser)]
#[grammar = "qy3.pest"]
pub struct Qy3Parser;

fn main() {
    println!("Hello, world!");
    run_first_tests();
}

fn run_first_tests() {
    let successful_parse_1 = Qy3Parser::parse(Rule::file, "");
    println!("\nPARSE 1 (expect OK):\n{:?}", successful_parse_1);

    let successful_parse_2 = Qy3Parser::parse(Rule::file, "zero = 0");
    println!("\nPARSE 2 (expect OK):\n{:?}", successful_parse_2);

    let successful_parse_3 = Qy3Parser::parse(Rule::file, "a () => return 0 b = 13");
    println!("\nPARSE 3 (expect OK):\n{:?}", successful_parse_3);
}

