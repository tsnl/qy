use super::*;

pub struct Token {
  span: fb::Span,
  info: TokenInfo
}

impl Token {
  pub fn new(span: fb::Span, info: TokenInfo) -> Token {
    Token { span, info }
  }
  pub fn loc(&self) -> fb::Span {
    self.span
  }
  pub fn info(&self) -> &TokenInfo {
    &self.info
  }
}

#[derive(Clone)]
pub enum TokenInfo {
  TypeIdentifier(intern::IntStr),
  ValueIdentifier(intern::IntStr),
  LiteralString(String),
  LiteralInteger(String, IntegerFormat),
  LiteralFloat { mantissa: String, exponent: Option<String> },
  
  Period, Comma, Colon,
  LeftParenthesis, RightParenthesis,
  LeftSquareBracket, RightSquareBracket,
  LeftCurlyBrace, RightCurlyBrace,
  
  Assign, Update,
  
  ValueSelfKeyword, TypeSelfKeyword, 
  InKeyword, 
  MutKeyword, WeakKeyword,
  UseKeyword,

  Asterisk, Divide, Quotient, Modulo,
  Plus, Minus, ExclamationPoint,
  LeftShift, RightShift,
  LessThan, GreaterThan, LessThanOrEquals, GreaterThanOrEquals,
  Equals, NotEquals,
  BitwiseXOr, BitwiseAnd, BitwiseOr,
  LogicalAnd, LogicalOr,

  Indent, Newline, Dedent,
}

#[derive(Clone)]
pub enum IntegerFormat {
  Decimal,
  Hexadecimal
}
