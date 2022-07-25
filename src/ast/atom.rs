use super::*;

#[derive(Debug)]
pub enum Atom { 
    Bool(bool), 
    Str(String), 
    Chr(i32), 
    Int(u64, bool), 
    Float(f64),
    Symbol(IntStr) 
}

impl fmt::Display for Atom {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Bool (v) => {
                write!(f, "{}", if *v {"#t"} else {"#f"})
            }
            Self::Str(v) => {
                write!(f, "{}", &v)
            }
            Self::Chr(v) => {
                write!(f, "{}", v)
            }
            Self::Int(v, is_neg) => {
                write!(f, "{}{}", if *is_neg {"-"} else {""}, v)
            },
            Self::Float(v) => {
                write!(f, "{}", v)
            }
            Self::Symbol(i) => {
                write!(f, "#{}", i)
            }
        }
    }
}
impl Atom {
    
}