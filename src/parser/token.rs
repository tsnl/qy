use super::*;

use std::fmt::Debug;

#[derive(Debug)]
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

#[derive(Clone, Debug)]
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

  GetKeyword, SetKeyword,
  ValueSelfKeyword, TypeSelfKeyword, 
  InKeyword, 
  MutKeyword, WeakKeyword,
  UseKeyword,
  AssertKeyword,

  Asterisk, Divide, Quotient, Modulo,
  Plus, Minus, ExclamationPoint,
  LeftShift, RightShift,
  LessThan, GreaterThan, LessThanOrEquals, GreaterThanOrEquals,
  Equals, NotEquals,
  BitwiseXOr, BitwiseAnd, BitwiseOr,
  LogicalAnd, LogicalOr,

  Indent, EndOfLine, Dedent,
}

#[derive(Clone, Debug)]
pub enum IntegerFormat {
  Decimal,
  Hexadecimal
}
