use super::*;
// use std::collections::*;
use std::fmt::{self, Debug};

pub struct FeedbackManager {
    lb: Letterbox,
}
impl FeedbackManager {
    pub fn new () -> FeedbackManager {
        FeedbackManager { 
            lb: Letterbox::new(), 
        }
    }
    
}


//
// Letters
//

type LetterSeverity = i32;
mod sev {
    use super::LetterSeverity;
    pub const ERROR:   LetterSeverity = 5;
    pub const WARNING: LetterSeverity = 4;
    pub const INFO:    LetterSeverity = 3;
    pub const DEBUG:   LetterSeverity = 2;
    pub const TRACE:   LetterSeverity = 1;
}
pub struct Letterbox { letters: Vec<Letter>, threshold: LetterSeverity }
pub struct Letter { message_thunk: fn()->String }

impl Letterbox {
    fn new () -> Letterbox {
        Letterbox::new_with_threshold(sev::INFO)
    }
    fn new_with_threshold (threshold: LetterSeverity) -> Letterbox {
        Letterbox {
            letters: Vec::with_capacity(tune::EXPECTED_MAX_FB_LETTER_COUNT),
            threshold: threshold
        }
    }
    fn post (&mut self, severity: LetterSeverity, letter: Letter) {
        if severity >= self.threshold {
            self.letters.push(letter)
        }
    }
    fn letter_count (&self) -> usize {
        self.letters.len()
    }
    fn print (&self) {
        for letter in &self.letters {
            println!("ERROR:\n{}", (letter.message_thunk)());
        }
    }
}

//
// FileLoc
//

#[derive(Clone)]
pub struct FileLoc { file_id: src::FileID, loc: Loc }

#[derive(Clone)]
pub enum Loc { SpanLoc(Span), PosLoc(Pos) } 

impl Loc {
    pub fn new_filewide() -> Loc {
        Loc::SpanLoc(Span::new(Pos::new(0, 0), Pos::new(0, 0)))
    }
}
impl Debug for Loc {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::SpanLoc(span) => { 
                f.write_fmt(format_args!("{}", span)) 
            },
            Self::PosLoc(pos) => { 
                f.write_fmt(format_args!("{}", pos)) 
            }
        }
    }
}

#[derive(Clone)]
pub struct Span { beg: Pos, end: Pos }

impl Span {
    fn new(beg: Pos, end: Pos) -> Span {
        Span { beg: beg, end: end }
    }
}


#[derive(Clone)]
pub struct Pos { line_index: usize, column_index: usize }

impl Pos {
    fn new(line_index: usize, column_index: usize) -> Pos {
        Pos { line_index: line_index, column_index: column_index }
    }
}

impl fmt::Display for Loc {
    fn fmt (&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match &self {
            Self::SpanLoc (span) => {
                span.fmt(f)
            },
            Self::PosLoc (pos) => {
                pos.fmt(f)
            }
        }
    }
}
impl fmt::Display for Pos {
    fn fmt (&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}:{}", 1 + self.line_index, 1 + self.column_index)
    }
}
impl fmt::Display for Span {
    fn fmt (&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        if self.beg.line_index == self.end.line_index {
            if self.beg.column_index == self.end.column_index {
                self.beg.fmt(f)
            } else {
                write!(
                    f, "{}:{}-{}", 
                    1+self.beg.line_index, 1+self.beg.column_index, 1+self.end.column_index
                )
            }
        } else {
            write!(
                f, "{}:{}-{}:{}", 
                1+self.beg.line_index, 1+self.beg.column_index, 
                1+self.end.line_index, 1+self.end.column_index
            )
        }
        
    }
}

impl Pos {
    pub fn new_default() -> Pos {
        Pos { line_index: 0, column_index: 0 }
    }
}