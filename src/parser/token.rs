use super::*;

pub struct Token {
  loc: feedback::Span,
  info: TokenInfo
}

impl Token {
  pub fn new(loc: feedback::Span, info: TokenInfo) -> Token {
    Token { loc, info }
  }
  pub fn loc(&self) -> feedback::Span {
    self.loc
  }
  pub fn info(&self) -> &TokenInfo {
    &self.info
  }
}

pub enum TokenInfo {
  TypeIdentifier(intern::IntStr),
  ValueIdentifier(intern::IntStr),
  LiteralString(String),
  LiteralInteger(String, IntegerFormat),
  LiteralFloat(String),
  
  Period, Comma, Colon,
  LeftParenthesis, RightParenthesis,
  LeftSquareBracket, RightSquareBracket,
  LeftCurlyBrace, RightCurlyBrace,
  Indent, Newline, Dedent,
  Assign, Update,
  
  ValueSelfKeyword, TypeSelfKeyword, 
  InKeyword, 
  MutKeyword, WeakKeyword,
  UseKeyword,

  Asterisk, Divide, Quotient, Modulo,
  Plus, Minus, Bang,
  LeftShift, RightShift,
  LessThan, GreaterThan, LessThanOrEquals, GreaterThanOrEquals,
  Equals, NotEquals,
  BitwiseXOr, BitwiseAnd, BitwiseOr,
  LogicalAnd, LogicalOr,

  BackslashEscape
}

pub enum IntegerFormat {
  Decimal,
  Hexadecimal
}
