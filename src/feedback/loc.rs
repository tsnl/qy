use super::*;

#[derive(Clone, Copy)]
pub enum Loc {
  File(source::SourceID),
  FileSpan(source::SourceID, Span),
  Builtin(intern::IntStr),
}

#[derive(Clone, Copy)]
pub struct Span {
  first_pos: Cursor,
  last_pos: Cursor
}

#[derive(Clone, Copy)]
pub struct Cursor {
  line_index: i32,
  column_index: i32
}

impl Span {
  pub fn new(first_pos: Cursor, last_pos: Cursor) -> Span {
    Span{first_pos, last_pos}
  }
  pub fn first(self) -> Cursor {
    self.first_pos
  }
  pub fn last(self) -> Cursor {
    self.last_pos
  }
}

impl Cursor {
  pub fn new(line_index: i32, column_index: i32) -> Cursor {
    Cursor {line_index, column_index}
  }
  pub fn line(self) -> i32 {
    1 + self.line_index
  }
  pub fn column(self) -> i32 {
    1 + self.column_index
  }
}


