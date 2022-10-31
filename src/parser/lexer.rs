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
        CursorState::EndOfFile => {
          CursorState::EndOfFile
        }
        CursorState::StartOfFile | CursorState::InFile(_) => {
          self.scan_next_token_and_get_new_cursor_state()
        }
      }
  }
}
impl Lexer {
  fn scan_next_token_and_get_new_cursor_state(&mut self) -> CursorState {
    if !self.reader.at_eof() {
      let next_token = self.scan_next_token();
      match next_token {
        Some(next_token) => CursorState::InFile(next_token),
        None => CursorState::EndOfFile
      }
    } else {
      CursorState::EndOfFile
    }
  }
}
impl Lexer {
  fn span(&self, first_pos: feedback::Cursor) -> feedback::Span {
    feedback::Span::new(first_pos, self.reader.cursor())
  }
}
impl Lexer {
  fn scan_next_token(&mut self) -> Option<Token> {
    // Reading out any leading spaces, tabs, and line comments.
    // After this, the cursor position is the correct start-of-token
    // position for a span.
    self.skip_any_spaces_and_line_comments();

    // terminating if at EOF
    if self.reader.at_eof() {
      return None;
    }

    // punctuation:
    if let Some(token) = self.scan_punctuation() {
      return Some(token);
    }
    
    // keywords and identifiers:
    if let Some(token) = self.scan_word() {
      return Some(token);
    }

    // number literals: int or float:
    if let Some(token) = self.scan_number() {
      return Some(token);
    }

    panic!("Unexpected character");
  }
}
impl Lexer {
  fn skip_any_spaces_and_line_comments(&mut self) {
    loop {
      // non-newline whitespace
      if self.reader.match_byte(b' ') {
        continue;
      }
      if self.reader.match_byte(b'\t') {
        continue;
      }      
      // line comments
      if self.reader.match_byte(b'#') {
        self.skip_any_bytes_until_newline();
        continue;
      }
      // neither whitespace nor line comments left; break.
      break;
    }
  }
  fn skip_any_bytes_until_newline(&mut self) {
    loop {
      if let Some(peek) = self.reader.peek() {
        if peek == b'\n' {
          break;
        } else {
          self.reader.skip();
        }
      } else {
        // EOF
        break;
      }
    }
  }
}
impl Lexer {
  fn scan_punctuation(&mut self) -> Option<Token> {
    let first_pos = self.reader.cursor();
    macro_rules! token_span {
      () => { self.span(first_pos) };
    }
    if self.reader.match_byte(b'.') {
      return Some(Token::new(token_span!(), TokenInfo::Period));
    }
    if self.reader.match_byte(b',') {
      return Some(Token::new(token_span!(), TokenInfo::Comma));
    }
    if self.reader.match_byte(b':') {
      return Some(Token::new(token_span!(), TokenInfo::Colon));
    }
    if self.reader.match_byte(b'<') {
      if self.reader.match_byte(b'<') {
        return Some(Token::new(token_span!(), TokenInfo::LeftShift));
      } else if self.reader.match_byte(b'=') {
        return Some(Token::new(token_span!(), TokenInfo::LessThanOrEquals));
      } else {
        return Some(Token::new(token_span!(), TokenInfo::LessThan));
      }
    }
    if self.reader.match_byte(b'>') {
      if self.reader.match_byte(b'>') {
        return Some(Token::new(token_span!(), TokenInfo::RightShift));
      } else if self.reader.match_byte(b'=') {
        return Some(Token::new(token_span!(), TokenInfo::GreaterThanOrEquals));
      } else {
        return Some(Token::new(token_span!(), TokenInfo::GreaterThan));
      }
    }
    if self.reader.match_byte(b'=') {
      if self.reader.match_byte(b'=') {
        return Some(Token::new(token_span!(), TokenInfo::Equals));
      } else {
        return Some(Token::new(token_span!(), TokenInfo::Assign));
      }
    }
    if self.reader.match_byte(b'!') {
      if self.reader.match_byte(b'=') {
        return Some(Token::new(token_span!(), TokenInfo::NotEquals));
      } else {
        return Some(Token::new(token_span!(), TokenInfo::ExclamationPoint));
      }
    }
    if self.reader.match_byte(b'*') {
      return Some(Token::new(token_span!(), TokenInfo::Asterisk));
    }
    if self.reader.match_byte(b'/') {
      if self.reader.match_byte(b'/') {
        return Some(Token::new(token_span!(), TokenInfo::Quotient));
      } else {
        return Some(Token::new(token_span!(), TokenInfo::Divide));
      }
    }
    if self.reader.match_byte(b'%') {
      return Some(Token::new(token_span!(), TokenInfo::Modulo));
    }
    if self.reader.match_byte(b'+') {
      return Some(Token::new(token_span!(), TokenInfo::Plus));
    }
    if self.reader.match_byte(b'-') {
      return Some(Token::new(token_span!(), TokenInfo::Minus));
    }
    return None
  }
}
impl Lexer {
  fn scan_word(&mut self) -> Option<Token> {
    let opt_first_char = self.reader.peek();
    if self.reader.match_byte_if(|b| b.is_ascii_alphabetic() || b == b'_') {
      let first_char = opt_first_char.unwrap();
      None  // TODO: finish this!
    } else {
      None
    }
  }
}
impl Lexer {
  fn scan_number(&mut self) -> Option<Token> {
    // TODO: implement this
    None
  }
}