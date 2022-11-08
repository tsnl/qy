use super::*;

pub struct Term {
  data: TermData,
  loc: fb::Loc
}
pub enum TermData {

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
  Equals, NotEquals
}
