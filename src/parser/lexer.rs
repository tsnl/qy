use super::*;

pub struct Lexer<'a> {
  reader: Reader,
  intern_manager: &'a mut intern::Manager,
  cursor_state: CursorState,
}

pub enum CursorState {
  StartOfFile,
  EndOfFile,
  InFile(Token)
}

const DEFAULT_IDENTIFIER_CAPACITY: usize = 10;
const DEFAULT_HEXADECIMAL_INT_CHUNK_CAPACITY: usize = 10;
const DEFAULT_DECIMAL_INT_CHUNK_CAPACITY: usize = 10;

impl<'a> Lexer<'a> {
  pub fn new(intern_manager: &'a mut intern::Manager, source_text: String) -> Self {
    let mut lexer = Self {
      reader: Reader::new(source_text),
      intern_manager: intern_manager,
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

impl<'a> Lexer<'a> {
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

    panic!("Unexpected character: {}", self.reader.peek().unwrap().to_string());
  }
}

impl<'a> Lexer<'a> {
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

impl<'a> Lexer<'a> {
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

impl<'a> Lexer<'a> {
  fn scan_word(&mut self) -> Option<Token> {
    let first_pos = self.reader.cursor();
    let opt_first_char = self.reader.peek();
    if self.reader.match_byte_if(|b| b.is_ascii_alphabetic() || b == b'_') {
      let first_char = opt_first_char.unwrap();
      let mut chars = Vec::with_capacity(DEFAULT_IDENTIFIER_CAPACITY);
      chars.push(first_char);
      loop {
        let opt_later_char = self.reader.peek();
        if self.reader.match_byte_if(|b| b.is_ascii_alphanumeric() || b == b'_') {
          chars.push(opt_later_char.unwrap())
        } else {
          break;
        }
      }
      Some(self.select_word_token(first_pos, chars))
    } else {
      None
    }
  }
  fn select_word_token(&mut self, first_pos: feedback::Cursor, id_chars: Vec<u8>) -> Token {
    let id_is_value = Self::is_value_identifier_chars(&id_chars);
    let id_string = String::from_utf8(id_chars).unwrap();
    let id_intstr = self.intern_manager.intern(id_string);
    Token::new(
      self.span(first_pos), 
      if id_is_value {
        TokenInfo::ValueIdentifier(id_intstr)
      } else {
        TokenInfo::TypeIdentifier(id_intstr)
      }
    )
  }
  fn is_value_identifier_chars(chars: &Vec<u8>) -> bool {
    for character in chars {
      if character.is_ascii_uppercase() {
        return false;
      }
      if character.is_ascii_lowercase() {
        return true;
      }
    }
    return true;
  }
}

impl<'a> Lexer<'a> {
  fn scan_number(&mut self) -> Option<Token> {
    let first_pos = self.reader.cursor();
    let opt_first_char = self.reader.peek();
    
    // If '0x' or '0X' detected, then should scan a hex integer chunk, no
    // hex floating point numbers.
    // Else should scan a decimal integer chunk;
    // decimal suffix is '[.<decimal-integer-chunk>][(e|E)<decimal-integer-chunk>]',
    // if suffix empty then just an integer, else float.
    
    match opt_first_char {
      Some(first_char) =>
        Some(self.scan_nonempty_number(first_pos, first_char)),
      None =>
        None
    }
  }
  fn scan_nonempty_number(&mut self, first_pos: feedback::Cursor, first_char: u8) -> Token {
    let is_hex_number = 
      first_char == b'0' && 
      self.reader.match_byte_if(|b| b == b'x' || b == b'X');
    if is_hex_number {
      self.scan_nonempty_hex_number(first_pos)
    } else {
      self.scan_nonempty_decimal_number(first_pos, first_char)
    }
  }
  fn scan_nonempty_hex_number(&mut self, first_pos: feedback::Cursor) -> Token {
    let hex_int_mantissa = self.scan_hex_int_chunk();
    Token::new(
      self.span(first_pos), 
      TokenInfo::LiteralInteger(hex_int_mantissa, IntegerFormat::Hexadecimal)
    )
  }
  fn scan_nonempty_decimal_number(&mut self, first_pos: feedback::Cursor, first_char: u8) -> Token {
    let mut is_float = false;
    let mantissa = {
      let mut mantissa = self.scan_decimal_int_chunk(Some(first_char));
      if self.reader.match_byte(b'.') {
        let post_point_int = self.scan_decimal_int_chunk(None);
        is_float = true;
        mantissa.reserve_exact(1 + post_point_int.len());
        mantissa.push('.');
        mantissa += post_point_int.as_str();
      };
      mantissa
    };
    let opt_exponent =
      if self.reader.match_byte_if(|b| b == b'e' || b == b'E') {
        is_float = true;
        Some(self.scan_exponent_suffix())
      } else {
        None
      };
    let token_info =
      if is_float {
        TokenInfo::LiteralFloat { mantissa: mantissa, exponent: opt_exponent } 
      } else {
        TokenInfo::LiteralInteger(mantissa, IntegerFormat::Decimal)
      };
    Token::new(self.span(first_pos), token_info)
  }
  fn scan_exponent_suffix(&mut self) -> String {
    let exponent_has_neg_prefix = self.reader.match_byte(b'-');
    let exponent_int = self.scan_decimal_int_chunk(None);
    if exponent_int.is_empty() {
      panic!("Expected valid exponent after 'e/E' exponent");
    }
    if exponent_has_neg_prefix {
      let mut neg_exponent_int = String::with_capacity(1+exponent_int.len());
      neg_exponent_int.push('-');
      neg_exponent_int += exponent_int.as_str();
      neg_exponent_int
    } else {
      exponent_int
    }
  }
  fn scan_hex_int_chunk(&mut self) -> String {
    let mut hex_int_chunk_chars = Vec::with_capacity(DEFAULT_HEXADECIMAL_INT_CHUNK_CAPACITY);
    loop {
      let opt_int_chunk_char = self.reader.peek();
      if self.reader.match_byte_if(|b| b.is_ascii_hexdigit() || b == b'_') {
        hex_int_chunk_chars.push(opt_int_chunk_char.unwrap());
      } else {
        break;
      }
    };
    String::from_utf8(hex_int_chunk_chars).unwrap()
  }
  fn scan_decimal_int_chunk(&mut self, opt_first_char: Option<u8>) -> String {
    let mut decimal_int_chunk_chars = Vec::with_capacity(DEFAULT_DECIMAL_INT_CHUNK_CAPACITY);
    if let Some(first_char) = opt_first_char {
      decimal_int_chunk_chars.push(first_char);
    }
    loop {
      let opt_int_chunk_char = self.reader.peek();
      if self.reader.match_byte_if(|b| b.is_ascii_digit() || b == b'_') {
        decimal_int_chunk_chars.push(opt_int_chunk_char.unwrap());
      } else {
        break;
      }
    };
    String::from_utf8(decimal_int_chunk_chars).unwrap()
  }
}

impl<'a> Lexer<'a> {
  fn span(&self, first_pos: feedback::Cursor) -> feedback::Span {
    feedback::Span::new(first_pos, self.reader.cursor())
  }
}
