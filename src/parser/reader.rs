use super::*;

pub struct Reader {
  source_chars: Vec<char>,
  line_index: i32,
  column_index: i32,
  offset: usize,
  source_id: source::SourceID
}

impl Reader {
  pub fn new(source_id: source::SourceID, source_text: String) -> Reader {
    Reader {
      source_chars: source_text.chars().collect(),
      line_index: 0,
      column_index: 0,
      offset: 0,
      source_id
    }
  }
  pub fn source(&self) -> source::SourceID {
    self.source_id
  }
}
impl Reader {
  pub fn peek(&self) -> Option<char> {
    if self.offset < self.source_chars.len() {
      Some(self.source_chars[self.offset])
    } else {
      None
    }
  }
  pub fn skip(&mut self) -> fb::Result<()> {
    if let Some(peek1) = self.peek() {
      if peek1 == '\r' {
        self.offset += 1;
        if let Some(peek2) = self.peek() {
          if peek2 == '\n' {
            // CR LF
            self.offset += 1;
            self.line_index += 1;
            self.column_index = 0;  
            return Ok(());
          } 
        }
        let msg =
          fb::Message::new(
            String::from("Invalid text file: CR without LF immediately after")
          ).with_ref(
            String::from("CR occurs here"), 
            fb::Loc::FilePos(self.source_id, self.cursor())
          );
        return Err(fb::Error::new().with_message(msg));
      } else if peek1 == '\n' {
        // LF line ending
        self.offset += 1;
        self.line_index += 1;
        self.column_index = 0;
      } else {
        // non-line-ending
        self.offset += 1;
        self.column_index += 1;
      };
      Ok(())
    } else {
      // EOF
      Ok(())
    }
  }
  pub fn match_char(&mut self, c: char) -> fb::Result<bool> {
    if let Some(peek) = self.peek() {
      if peek == c {
        self.skip()?;
        return Ok(true);
      }
    }
    return Ok(false);
  }
  pub fn match_char_if<F: Fn(char)->bool>(&mut self, cp: F) -> fb::Result<bool> {
    if let Some(peek) = self.peek() {
      if cp(peek) {
        self.skip()?;
        return Ok(true);
      }
    }
    return Ok(false);
  }
}
impl Reader {
  pub fn at_eof(&self) -> bool {
    if let Some(_) = self.peek() {
      false
    } else {
      true
    }
  }
}
impl Reader {
  pub fn cursor(&self) -> fb::Cursor {
    fb::Cursor::new(self.line_index, self.column_index)
  }
}
