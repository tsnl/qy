use super::*;

pub struct Term {
  data: TermData,
  loc: fb::Loc
}
pub enum TermData {
  Self_,
  IdRef { name: intern::IntStr, prefix: Option<NamespacePrefix> },
  LiteralInt { mantissa: String, base: LiteralIntBase },
  LiteralFloat { mantissa: String, exponent: Option<String> },
  LiteralString { content: String, kind: LiteralStringKind },
  Unary { operator: UnaryTermOperator, operand: Box<Term> },
  Binary { operator: BinaryTermOperator, left_operand: Box<Term>, right_operand: Box<Term> },
  GetProperty { container: Box<Term>, property_name: intern::IntStr },
  Send { receiver: Box<Term>, message_name: intern::IntStr, message_args: Vec<Term> },
  EvalSuite(Suite)
}

#[derive(Clone, Copy)]
pub enum UnaryTermOperator {
  LogicalNot,
  BitwiseNot,
  Posate,
  Negate
}
#[derive(Clone, Copy)]
pub enum BinaryTermOperator {
  Multiply, Divide, FloorDivide, Modulo,
  Add, Subtract,
  LeftShift, RightShfit,
  LessThan, GreaterThan, LessThanOrEquals, GreaterThanOrEquals,
  Equals, NotEquals,
  Update
}
#[derive(Clone, Copy)]
pub enum LiteralIntBase {
  Decimal,
  Hexadecimal
}
#[derive(Clone, Copy)]
pub enum LiteralStringKind {
  EscapedDoubleQuotedString
}
