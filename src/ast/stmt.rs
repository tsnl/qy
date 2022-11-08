use super::*;

pub struct Stmt {
  data: StmtData,
  loc: fb::Loc
}
pub enum StmtData {
  Use { prefix: NamespacePrefix },
  Const { const_name: intern::IntStr, const_type: TypeSpec, const_initializer: Term },
  Interface { interface_name: intern::IntStr, requirements: Suite },
  Record { data_members: Vec<FormalArgSpec>, is_mutable: bool },
  Variant { disjunctands: Vec<VariantStmtDisjunctand> },
  Extend { bound_vars: Vec<intern::IntStr>, extended_ts: TypeSpec, interfaces: Vec<TypeSpec> },
  Property { getter: Suite, setter: Option<Suite> },
  FunctionDeclaration { fn_name: intern::IntStr, formal_args: Vec<FormalArgSpec>, ret_ts: Option<TypeSpec> },
  FunctionDefinition { fn_name: intern::IntStr, formal_args: Vec<FormalArgSpec>, ret_ts: Option<TypeSpec>, body: Suite },
  Let { bound: LPattern, initializer: Term },
  While { condition: Term, body: Suite },
  For { bound: LPattern, iterator: Term, body: Suite },
  Assert(Term),
  Expr(Term),
  Return(Term),
  Break,
  Continue
}
pub struct VariantStmtDisjunctand {
  disjunctand_name: intern::IntStr,
  disjunctand_args: Option<Vec<FormalArgSpec>>
}
