use super::*;

#[derive(Debug)]
pub enum Form {
    List (Vec<Form>),
    Atom (Atom),
    Quote (Box<Form>),
    QuasiQuote (Box<Form>),
    QqEscape (Box<Form>)
}

impl fmt::Display for Form {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Self::List(elements) => {
                write!(f, "(")?;
                for (i, elem) in elements.iter().enumerate() {
                    write!(f, "{}", elem)?;
                    if i < elements.len()-1 {
                        write!(f, " ")?;
                    };
                };
                write!(f, ")")
            },
            Self::Atom(atom) => {
                write!(f, "{}", atom)
            }
            Self::Quote(form) => {
                write!(f, "{}", form.as_ref())
            }
            Self::QuasiQuote(qq) => {
                write!(f, "{}", qq.as_ref())
            }
            Self::QqEscape(es) => {
                write!(f, "{}", es.as_ref())
            }
            // _ => { write!(f, "???") }
        }
    }
}
