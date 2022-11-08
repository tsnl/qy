use super::*;

//
// Interface
//

impl ParserContext {
  pub fn new(tokens: Vec<Token>) -> Self {
    ParserContext { tokens }
  }
}

//
// Implementation
//

struct ParserContext {
  tokens: Vec<Token>
}
struct Parser<'a> {
  context: &'a ParserContext,
  offset: usize
}
