use super::*;

pub struct Reader {
  source_bytes: Vec<u8>,
  line_index: i32,
  column_index: i32,
  offset: usize,
  source_id: source::SourceID
}

impl Reader {
  pub fn new(source_id: source::SourceID, source_text: String) -> Reader {
    Reader {
      source_bytes: source_text.into_bytes(),
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
  pub fn peek(&self) -> Option<u8> {
    if self.offset < self.source_bytes.len() {
      Some(self.source_bytes[self.offset])
    } else {
      None
    }
  }
  pub fn skip(&mut self) -> Result<(), feedback::Error> {
    if let Some(peek1) = self.peek() {
      if peek1 == b'\r' {
        self.offset += 1;
        if let Some(peek2) = self.peek() {
          if peek2 == b'\n' {
            // CR LF
            self.offset += 1;
            self.line_index += 1;
            self.column_index = 0;  
            return Ok(());
          } 
        }
        let msg =
          feedback::Message::new(
            String::from("Invalid text file: CR without LF immediately after")
          ).with_ref(
            String::from("CR occurs here"), 
            feedback::Loc::FilePos(self.source_id, self.cursor())
          );
        return Err(feedback::Error::new().with_msg(msg));
      } else if peek1 == b'\n' {
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
  pub fn match_byte(&mut self, c: u8) -> Result<bool, feedback::Error> {
    if let Some(peek) = self.peek() {
      if peek == c {
        self.skip()?;
        return Ok(true);
      }
    }
    return Ok(false);
  }
  pub fn match_byte_if<F: Fn(u8)->bool>(&mut self, cp: F) -> Result<bool, feedback::Error> {
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
      true
    } else {
      false
    }
  }
}
impl Reader {
  pub fn cursor(&self) -> feedback::Cursor {
    feedback::Cursor::new(self.line_index, self.column_index)
  }
}
