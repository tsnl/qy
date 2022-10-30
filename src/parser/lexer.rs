use super::*;

pub struct Lexer {
  reader: Reader,
  cursor_state: CursorState,
}

pub enum CursorState {
  StartOfFile,
  EndOfFile,
  InFile(Token)
}

impl Lexer {
  pub fn new(source_text: String) -> Lexer {
    let mut lexer = Lexer {
      reader: Reader::new(source_text),
      cursor_state: CursorState::StartOfFile
    };
    lexer.skip();
    lexer
  }
  pub fn skip(&mut self) {
    self.cursor_state =
      match self.cursor_state {
        CursorState::EndOfFile => CursorState::EndOfFile,
        CursorState::StartOfFile => self.skip_impl(),
        CursorState::InFile(_) => self.skip_impl(),
      }
  }
}
impl Lexer {
  fn skip_impl(&mut self) -> CursorState {
    if !self.reader.eof() {
      let next_token = self.scan_next_token();
      CursorState::InFile(next_token)
    } else {
      CursorState::EndOfFile
    }
  }
}
impl Lexer {
  fn scan_next_token(&mut self) -> Token {
    Token::new(
      feedback::Span::new(
        feedback::Cursor::new(0, 0),
        feedback::Cursor::new(0, 1),
      ), 
      TokenInfo::Newline
    )
  }
}
