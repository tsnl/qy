use super::*;

pub struct TypeSpec {
  data: TypeSpecData,
  loc: fb::Loc
}

pub enum TypeSpecData {
  IdRef { name: intern::IntStr, opt_prefix: Option<NamespacePrefix> },
  SchemeInstantiation { scheme: Box<TypeSpec>, arguments: Vec<TemplateActualArg> }
}
