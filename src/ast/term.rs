use super::*;

pub struct Term {
  data: TermData,
  loc: fb::Loc
}
pub enum TermData {
  Self_,
  LiteralInt(String, LiteralIntBase),
  LiteralFloat(String),
  LiteralString(String, LiteralStringKind),
  Unary(UnaryTermOperator, Box<Term>),
  Binary(UnaryTermOperator, Box<Term>),
  GetProperty(Box<Term>, intern::IntStr),
  Send(Box<Term>, intern::IntStr, Vec<Term>),
  EvalSuite(Suite)
}

pub enum UnaryTermOperator {
  LogicalNot,
  BitwiseNot,
  Posate,
  Negate
}
pub enum BinaryTermOperator {
  Multiply, Divide, FloorDivide, Modulo,
  Add, Subtract,
  LeftShift, RightShfit,
  LessThan, GreaterThan, LessThanOrEquals, GreaterThanOrEquals,
  Equals, NotEquals,
  Update
}

pub enum LiteralIntBase {
  Decimal,
  Hexadecimal
}
pub enum LiteralStringKind {
  EscapedDoubleQuotedString
}
