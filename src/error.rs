use crate::*;

#[derive(Debug)]
pub struct Error { pieces: Option<Box<ErrorPiece>> }

#[derive(Debug)]
struct ErrorPiece { loc: fb::Loc, desc: String, prev: Option<Box<ErrorPiece>> }

impl Error {
    pub fn new () -> Error {
        Error { pieces: None }
    }
    pub fn compose (self, loc: fb::Loc, desc: String) -> Self {
        let tos_piece = ErrorPiece {
            loc: loc, 
            desc: desc,
            prev: self.pieces
        };
        let new_stack = Some(Box::new(tos_piece));
        Error { pieces: new_stack }
    }
}

impl Error {
    pub fn print (&self) {
        if let Some(head) = &self.pieces {
            head.print();
        }
    }
}
impl ErrorPiece {
    fn print (&self) {
        // printing all prior messages first:
        if let Some(prev) = &self.prev {
            prev.print();
        }

        // printing this message:
        println!("ERROR: {}", &self.desc);
        println!("... see: {}", &self.loc);
        println!("");
    }
}