use crate::intern::IntStr;

use super::*;

//
// LPatterns
//

pub struct LPattern {
  data: LPatternData,
  loc: fb::Loc
}
pub enum LPatternData {
  Singleton(FormalArgSpec),
  Destructured { sub_patterns: Vec<LPattern> }
}

//
// Namespace prefices
//

pub struct NamespacePrefix {
  names: Vec<IntStr>,
  loc: fb::Loc
}

//
// Template actual arg = value | type
//

pub struct TemplateActualArg {
  data: TemplateActualArgData,
  loc: fb::Loc
}
pub enum TemplateActualArgData {
  TypeExpr(TypeSpec),
  TermExpr(Term)
}

//
// Suite = a sequence of statements
//

pub struct Suite {
  items: Vec<Stmt>,
  loc: fb::Loc
}

//
// Formal arg specifiers
//

pub struct FormalArgSpec {
  name: intern::IntStr,
  type_spec: Option<TypeSpec>,
  loc: fb::Loc
}