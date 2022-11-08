use super::*;

pub struct Stmt {
  data: TermData,
  loc: fb::Loc
}
pub enum StmtData {
  Use,
  Const,
  Interface,
  Record,
  Variant,
  Extend,
  Property,
  Function,
  Let,
  Expr
}
