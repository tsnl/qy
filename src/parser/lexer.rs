use super::*;

pub struct Lexer<'a> {
  reader: Reader,
  intern_manager: &'a mut intern::Manager,
  cursor_state: CursorState,
  keyword_map: HashMap<intern::IntStr, TokenInfo>
}

pub enum CursorState {
  StartOfFile,
  EndOfFile,
  InFile(Token)
}

const DEFAULT_IDENTIFIER_CAPACITY: usize = 10;
const DEFAULT_HEXADECIMAL_INT_CHUNK_CAPACITY: usize = 10;
const DEFAULT_DECIMAL_INT_CHUNK_CAPACITY: usize = 10;
const KEYWORD_MAP_CAPACITY: usize = 6;

impl<'a> Lexer<'a> {
  pub fn new(intern_manager: &'a mut intern::Manager, source_id: source::SourceID, source_text: String) -> Result<Self, fb::Error> {
    let keyword_map = Lexer::new_keyword_map(intern_manager);
    let mut lexer = Self {
      reader: Reader::new(source_id, source_text),
      intern_manager: intern_manager,
      cursor_state: CursorState::StartOfFile,
      keyword_map
    };
    lexer.skip()?;
    Ok(lexer)
  }
  fn new_keyword_map(intern_manager: &'a mut intern::Manager) -> HashMap<intern::IntStr, TokenInfo> {
    let mut kw_map = HashMap::with_capacity(KEYWORD_MAP_CAPACITY);
    kw_map.insert(intern_manager.intern(String::from("self")), TokenInfo::ValueSelfKeyword);
    kw_map.insert(intern_manager.intern(String::from("Self")), TokenInfo::TypeSelfKeyword);
    kw_map.insert(intern_manager.intern(String::from("in")), TokenInfo::InKeyword);
    kw_map.insert(intern_manager.intern(String::from("mut")), TokenInfo::MutKeyword);
    kw_map.insert(intern_manager.intern(String::from("weak")), TokenInfo::WeakKeyword);
    kw_map.insert(intern_manager.intern(String::from("use")), TokenInfo::UseKeyword);
    kw_map
  }
}
impl<'a> Lexer<'a> {
  pub fn skip(&mut self) -> Result<(), fb::Error> {
    self.cursor_state =
      match self.cursor_state {
        CursorState::EndOfFile => {
          CursorState::EndOfFile
        }
        CursorState::StartOfFile | CursorState::InFile(_) => {
          self.scan_next_token_and_get_new_cursor_state()?
        }
      };
    Ok(())
  }
  fn scan_next_token_and_get_new_cursor_state(&mut self) -> Result<CursorState, fb::Error> {
    if !self.reader.at_eof() {
      let next_token = self.scan_next_token()?;
      match next_token {
        Some(next_token) => 
          Ok(CursorState::InFile(next_token)),
        None => 
          Ok(CursorState::EndOfFile)
      }
    } else {
      Ok(CursorState::EndOfFile)
    }
  }
}

impl<'a> Lexer<'a> {
  fn scan_next_token(&mut self) -> Result<Option<Token>, fb::Error> {
    // Reading out any leading spaces, tabs, and line comments.
    // After this, the cursor position is the correct start-of-token
    // position for a span.
    // Note that we do not skip any newline characters (including at the end of line comments)
    // to correctly generate indent, dedent, and end-of-line tokens.
    self.skip_any_spaces_and_line_comments()?;

    // terminating if at EOF
    if self.reader.at_eof() {
      return Ok(None);
    }

    // punctuation:
    if let Some(token) = self.scan_punctuation()? {
      return Ok(Some(token));
    }
    
    // keywords and identifiers:
    if let Some(token) = self.scan_word()? {
      return Ok(Some(token));
    }

    // number literals: int or float:
    if let Some(token) = self.scan_number()? {
      return Ok(Some(token));
    }

    // string literals:
    if let Some(token) = self.scan_string_literal()? {
      return Ok(Some(token));
    }

    // TODO: try scanning line-endings (indent, dedent, eol)

    // error: unexpected character
    let msg =
      fb::Message::new(
        format!(
          "Character '{}' came as a total surprise",
          self.reader.peek().unwrap().to_string()
        )
      )
      .with_ref(
        String::from("see"),
        fb::Loc::FilePos(self.reader.source(), self.reader.cursor())
      );
    Err(fb::Error::new().with_message(msg))
  }
}

impl<'a> Lexer<'a> {
  fn skip_any_spaces_and_line_comments(&mut self) -> Result<(), fb::Error> {
    loop {
      // non-newline whitespace
      if self.reader.match_rune(' ')? {
        continue;
      }
      if self.reader.match_rune('\t')? {
        continue;
      }      
      // line comments
      if self.reader.match_rune('#')? {
        self.skip_any_bytes_until_newline()?;
        // After skipping out a line-comment, we always have a newline or EOF. 
        // We should not skip newline because it is used for indent, dedent, 
        // and EOL generation (consider `x = 5 # ...\n`; we need the EOL).
        // Hence safe to break here.
        break;
      }
      // neither whitespace nor line comments left; break.
      break;
    };
    Ok(())
  }
  fn skip_any_bytes_until_newline(&mut self) -> Result<(), fb::Error> {
    while self.reader.match_rune_if(|c| c != '\n')? {};
    Ok(())
  }
}

impl<'a> Lexer<'a> {
  fn scan_punctuation(&mut self) -> Result<Option<Token>, fb::Error> {
    let first_pos = self.reader.cursor();
    macro_rules! token_span {
      () => { self.span(first_pos) };
    }
    if self.reader.match_rune('.')? {
      return Ok(Some(Token::new(token_span!(), TokenInfo::Period)));
    }
    if self.reader.match_rune(',')? {
      return Ok(Some(Token::new(token_span!(), TokenInfo::Comma)));
    }
    if self.reader.match_rune(':')? {
      return Ok(Some(Token::new(token_span!(), TokenInfo::Colon)));
    }
    if self.reader.match_rune('<')? {
      if self.reader.match_rune('<')? {
        return Ok(Some(Token::new(token_span!(), TokenInfo::LeftShift)));
      } else if self.reader.match_rune('=')? {
        return Ok(Some(Token::new(token_span!(), TokenInfo::LessThanOrEquals)));
      } else {
        return Ok(Some(Token::new(token_span!(), TokenInfo::LessThan)));
      }
    }
    if self.reader.match_rune('>')? {
      if self.reader.match_rune('>')? {
        return Ok(Some(Token::new(token_span!(), TokenInfo::RightShift)));
      } else if self.reader.match_rune('=')? {
        return Ok(Some(Token::new(token_span!(), TokenInfo::GreaterThanOrEquals)));
      } else {
        return Ok(Some(Token::new(token_span!(), TokenInfo::GreaterThan)));
      }
    }
    if self.reader.match_rune('=')? {
      if self.reader.match_rune('=')? {
        return Ok(Some(Token::new(token_span!(), TokenInfo::Equals)));
      } else {
        return Ok(Some(Token::new(token_span!(), TokenInfo::Assign)));
      }
    }
    if self.reader.match_rune('!')? {
      if self.reader.match_rune('=')? {
        return Ok(Some(Token::new(token_span!(), TokenInfo::NotEquals)));
      } else {
        return Ok(Some(Token::new(token_span!(), TokenInfo::ExclamationPoint)));
      }
    }
    if self.reader.match_rune('*')? {
      return Ok(Some(Token::new(token_span!(), TokenInfo::Asterisk)));
    }
    if self.reader.match_rune('/')? {
      if self.reader.match_rune('/')? {
        return Ok(Some(Token::new(token_span!(), TokenInfo::Quotient)));
      } else {
        return Ok(Some(Token::new(token_span!(), TokenInfo::Divide)));
      }
    }
    if self.reader.match_rune('%')? {
      return Ok(Some(Token::new(token_span!(), TokenInfo::Modulo)));
    }
    if self.reader.match_rune('+')? {
      return Ok(Some(Token::new(token_span!(), TokenInfo::Plus)));
    }
    if self.reader.match_rune('-')? {
      return Ok(Some(Token::new(token_span!(), TokenInfo::Minus)));
    }
    return Ok(None)
  }
}

impl<'a> Lexer<'a> {
  fn scan_word(&mut self) -> Result<Option<Token>, fb::Error> {
    let first_pos = self.reader.cursor();
    let opt_first_char = self.reader.peek();
    if self.reader.match_rune_if(|b| b.is_ascii_alphabetic() || b == '_')? {
      let first_char = opt_first_char.unwrap();
      let mut chars = Vec::with_capacity(DEFAULT_IDENTIFIER_CAPACITY);
      chars.push(first_char);
      loop {
        let opt_later_char = self.reader.peek();
        if self.reader.match_rune_if(|b| b.is_ascii_alphanumeric() || b == '_')? {
          chars.push(opt_later_char.unwrap())
        } else {
          break;
        }
      }
      Ok(Some(self.new_word_token(first_pos, chars)))
    } else {
      Ok(None)
    }
  }
  fn new_word_token(&mut self, first_pos: fb::Cursor, id_chars: Vec<char>) -> Token {
    let id_is_value = Self::is_value_identifier_chars(&id_chars);
    let id_string = String::from_iter(id_chars);
    let id_intstr = self.intern_manager.intern(id_string);
    Token::new(
      self.span(first_pos), 
      match self.keyword_map.get(&id_intstr) {
        Some(kw_token_info) => 
          kw_token_info.clone(),
        None => 
          if id_is_value {
            TokenInfo::ValueIdentifier(id_intstr)
          } else {
            TokenInfo::TypeIdentifier(id_intstr)
          }
      }
    )
  }
  fn is_value_identifier_chars(chars: &Vec<char>) -> bool {
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
  fn scan_number(&mut self) -> Result<Option<Token>, fb::Error> {
    let first_pos = self.reader.cursor();
    let opt_first_char = self.reader.peek();
    
    // If '0x' or '0X' detected, then should scan a hex integer chunk, no
    // hex floating point numbers.
    // Else should scan a decimal integer chunk;
    // decimal suffix is '[.<decimal-integer-chunk>][(e|E)<decimal-integer-chunk>]',
    // if suffix empty then just an integer, else float.
    
    match opt_first_char {
      Some(first_char) =>
        Ok(Some(self.scan_nonempty_number(first_pos, first_char)?)),
      None =>
        Ok(None)
    }
  }
  fn scan_nonempty_number(&mut self, first_pos: fb::Cursor, first_char: char) -> Result<Token, fb::Error> {
    let is_hex_number = 
      first_char == '0' && 
      self.reader.match_rune_if(|b| b == 'x' || b == 'X')?;
    if is_hex_number {
      Ok(self.scan_nonempty_hex_number(first_pos)?)
    } else {
      Ok(self.scan_nonempty_decimal_number(first_pos, first_char)?)
    }
  }
  fn scan_nonempty_hex_number(&mut self, first_pos: fb::Cursor) -> Result<Token, fb::Error> {
    let hex_int_mantissa = self.scan_hex_int_chunk()?;
    Ok(Token::new(
      self.span(first_pos), 
      TokenInfo::LiteralInteger(hex_int_mantissa, IntegerFormat::Hexadecimal)
    ))
  }
  fn scan_nonempty_decimal_number(&mut self, first_pos: fb::Cursor, first_char: char) -> Result<Token, fb::Error> {
    let mut is_float = false;
    let mantissa = {
      let mut mantissa = self.scan_decimal_int_chunk(Some(first_char))?;
      if self.reader.match_rune('.')? {
        let post_point_int = self.scan_decimal_int_chunk(None)?;
        is_float = true;
        mantissa.reserve_exact(1 + post_point_int.len());
        mantissa.push('.');
        mantissa += post_point_int.as_str();
      };
      mantissa
    };
    let opt_exponent =
      if self.reader.match_rune_if(|b| b == 'e' || b == 'E')? {
        is_float = true;
        Some(self.scan_number_exponent_suffix(&mantissa)?)
      } else {
        None
      };
    let token_info =
      if is_float {
        TokenInfo::LiteralFloat { mantissa: mantissa, exponent: opt_exponent } 
      } else {
        TokenInfo::LiteralInteger(mantissa, IntegerFormat::Decimal)
      };
    Ok(Token::new(self.span(first_pos), token_info))
  }
  fn scan_number_exponent_suffix(&mut self, mantissa: &String) -> Result<String, fb::Error> {
    let start_of_suffix_pos = self.reader.cursor();
    let exponent_has_neg_prefix = self.reader.match_rune('-')?;
    let exponent_int = self.scan_decimal_int_chunk(None)?;
    if exponent_int.is_empty() {
      let message =
        fb::Message::new(
          String::from("Expected valid exponent after 'e/E' exponent in float literal")
        )
        .with_ref(
          format!("See incomplete literal '{}': ", mantissa), 
          fb::Loc::FilePos(self.reader.source(), start_of_suffix_pos)
        );
      return Err(fb::Error::new().with_message(message));
    }
    if exponent_has_neg_prefix {
      let mut neg_exponent_int = String::with_capacity(1+exponent_int.len());
      neg_exponent_int.push('-');
      neg_exponent_int += exponent_int.as_str();
      Ok(neg_exponent_int)
    } else {
      Ok(exponent_int)
    }
  }
  fn scan_hex_int_chunk(&mut self) -> Result<String, fb::Error> {
    let mut hex_int_chunk_chars = Vec::with_capacity(DEFAULT_HEXADECIMAL_INT_CHUNK_CAPACITY);
    loop {
      let opt_int_chunk_char = self.reader.peek();
      if self.reader.match_rune_if(|b| b.is_ascii_hexdigit() || b == '_')? {
        hex_int_chunk_chars.push(opt_int_chunk_char.unwrap());
      } else {
        break;
      }
    };
    Ok(String::from_iter(hex_int_chunk_chars))
  }
  fn scan_decimal_int_chunk(&mut self, opt_first_char: Option<char>) -> Result<String, fb::Error> {
    let mut decimal_int_chunk_chars = Vec::with_capacity(DEFAULT_DECIMAL_INT_CHUNK_CAPACITY);
    if let Some(first_char) = opt_first_char {
      decimal_int_chunk_chars.push(first_char);
    }
    loop {
      let opt_int_chunk_char = self.reader.peek();
      if self.reader.match_rune_if(|b| b.is_ascii_digit() || b == '_')? {
        decimal_int_chunk_chars.push(opt_int_chunk_char.unwrap());
      } else {
        break;
      }
    };
    Ok(String::from_iter(decimal_int_chunk_chars))
  }
}

impl<'a> Lexer<'a> {
  fn scan_string_literal(&mut self) -> Result<Option<Token>, fb::Error> {
    let first_pos = self.reader.cursor();
    if self.reader.match_rune('"')? {
      let mut literal_content_bytes: Vec<char> = Vec::new();
      let literal_terminated =
        loop {
          let glyph_pos = self.reader.cursor();
          let opt_peek_char = self.reader.peek();
          match opt_peek_char {
            Some(peek_char) => {
              if self.reader.match_rune('\\')? {
                let escaped_char: char = self.scan_escape_sequence_suffix(glyph_pos)?;
                literal_content_bytes.push(escaped_char);
              } else if self.reader.match_rune('"')? {
                break true;
              } else {
                literal_content_bytes.push(peek_char);
              }
            }
            None => {
              break false;
            }
          }
        };
      if literal_terminated {
        Ok(Some(
          Token::new(
            self.span(first_pos),
            TokenInfo::LiteralString(String::from_iter(literal_content_bytes))
          )
        ))
      } else {
        Err(fb::Error::new())
      }
    } else {
      Ok(None)
    }
  }
  fn scan_escape_sequence_suffix(&mut self, peek_pos: fb::Cursor) -> Result<char, fb::Error> {
    if self.reader.match_rune('"')? { 
      Ok('"')
    } else if self.reader.match_rune('n')? { 
      Ok('\n')
    }  else if self.reader.match_rune('r')? {
      Ok('\r')
    } else if self.reader.match_rune('t')? {
      Ok('\t')
    } else if self.reader.match_rune('a')? {
      Ok(0x07 as char)
    } else {
      Err(
        fb::Error::new()
        .with_message(
          fb::Message::new(
            format!(
              "Invalid escape sequence: after '\\', expected a valid escape character, not '{}'",
              match self.reader.peek() {
                Some(first_char) => String::from_iter([first_char]),
                None => String::from("EOF")
              }
            )
          )
          .with_ref(
            String::from("see..."), 
            fb::Loc::FilePos(self.reader.source(), peek_pos)
          )
        )
      )
    }
  }
}

impl<'a> Lexer<'a> {
  fn span(&self, first_pos: fb::Cursor) -> fb::Span {
    fb::Span::new(first_pos, self.reader.cursor())
  }
}
