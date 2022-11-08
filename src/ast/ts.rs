use super::*;

pub struct TypeSpec {
  data: TypeSpecData,
  loc: fb::Loc
}

pub enum TypeSpecData {
  IdRef(Option<NamespacePrefix>, intern::IntStr),
  SchemeInstantiation(Box<TypeSpec>, Vec<TemplateActualArg>)
}
