use super::*;

//
// Interface
//

// pub fn parse_file(filepath: &str) -> ast::Module {
  
// }

impl Parser {
  pub fn new(tokens: Vec<Token>) -> Self {
    Parser { tokens }
  }
}

//
// Implementation
//

struct Parser {
  tokens: Vec<Token>
}
struct ParserState<'a> {
  context: &'a Parser,
  peek_token_offset: usize
}

// impl<'a> ParserState<'a> {
//   pub fn parse_literal_int() -> ParserState {

//   }
// }