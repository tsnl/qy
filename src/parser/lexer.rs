// TODO: do not generate EOL, indent, dedent between parens, brackets, braces.

use super::*;

use std::mem;
use std::collections::vec_deque::VecDeque;

//
// Interface:
//

impl<'a> Lexer<'a> {
  pub fn new(
    intern_manager: &'a mut intern::Manager,
    source_id: source::SourceID,
    source_text: String,
    tab_width_in_spaces: i32
  ) -> Self {
    let keyword_map = Lexer::new_keyword_map(intern_manager);
    let mut lexer = Self {
      reader: Reader::new(source_id, source_text),
      intern_manager: intern_manager,
      cursor_state: CursorState::StartOfFile,
      token_queue: VecDeque::with_capacity(TOKEN_QUEUE_CAPACITY),
      indent_width_stack: Vec::with_capacity(INDENT_STACK_CAPACITY),
      matching_token_pair_expectation_stack: Vec::with_capacity(PAREN_STACK_CAPACITY),
      keyword_map,
      tab_width_in_spaces
    };
    lexer.indent_width_stack.push(0);
    assert!(lexer.try_advance_impl().unwrap().is_none(), "incorrect initial state while filling peek slot");
    lexer
  }
}

impl<'a> Lexer<'a> {
  pub fn peek(&self) -> Option<&Token> {
    match &self.cursor_state {
      CursorState::InFile(token) => Some(&token),
      _ => None
    }
  }
  pub fn advance(&mut self) -> fb::Result<Token> {
    let opt_old_token: Option<Token> = self.try_advance_impl()?;
    Ok(opt_old_token.unwrap())
  }
  pub fn try_advance(&mut self) -> fb::Result<Option<Token>> {
    self.try_advance_impl()
  }
  pub fn match_token<F: Fn(&Token)->bool>(&mut self, token_predicate: F) -> fb::Result<Option<Token>> {
    match self.peek() {
      Some(peek_token) => {
        if token_predicate(peek_token) {
          Ok(Some(self.advance()?))
        } else {
          Ok(None)
        }
      },
      None => {
        Ok(None)
      }
    }
  }
}

impl<'a> Lexer<'a> {
  pub fn scan_all_remaining_tokens(&mut self) -> fb::Result<Vec<Token>> {
    let mut output = Vec::with_capacity(1 << 20);
    while let Some(token) = self.try_advance()? {
      output.push(token);
    };
    Ok(output)
  }
}

pub fn scan(intern_manager: &mut intern::Manager, filepath: &str) -> Vec<Token> {
  let mut source_manager = source::Manager::new();
  let filepath = String::from(filepath);
  let source_text = std::fs::read_to_string(filepath.as_str()).unwrap();
  let source_id = source_manager.add(filepath);
  let mut lexer = Lexer::new(
    intern_manager,
    source_id,
    source_text,
    4
  );
  lexer.scan_all_remaining_tokens().unwrap()
}

//
// Implementation:
//

pub struct Lexer<'a> {
  reader: Reader,
  intern_manager: &'a mut intern::Manager,
  cursor_state: CursorState,
  token_queue: VecDeque<Token>,
  indent_width_stack: Vec<i32>,
  matching_token_pair_expectation_stack: Vec<(fb::Span, char)>,
  keyword_map: HashMap<intern::IntStr, TokenInfo>,
  tab_width_in_spaces: i32
}

pub enum CursorState {
  StartOfFile,
  EndOfFile,
  InFile(Token)
}

const IDENTIFIER_CAPACITY: usize = 10;
const HEXADECIMAL_INT_CHUNK_CAPACITY: usize = 10;
const DECIMAL_INT_CHUNK_CAPACITY: usize = 10;
const INDENT_STACK_CAPACITY: usize = 12;
const PAREN_STACK_CAPACITY: usize = 8;
const TOKEN_QUEUE_CAPACITY: usize = INDENT_STACK_CAPACITY;

impl<'a> Lexer<'a> {
  fn try_advance_impl(&mut self) -> fb::Result<Option<Token>> {
    let next_state =
      match &self.cursor_state {
        CursorState::EndOfFile => CursorState::EndOfFile,
        CursorState::StartOfFile => self.get_next_state()?,
        CursorState::InFile(_) => self.get_next_state()?
      };
    let replaced_old_token =
      match mem::replace(&mut self.cursor_state, next_state) {
        CursorState::StartOfFile | CursorState::EndOfFile => None,
        CursorState::InFile(old_token) => Some(old_token)
      };
    Ok(replaced_old_token)
  }
  fn get_next_state(&mut self) -> fb::Result<CursorState> {
    // Try depleting from the token queue:
    if let Some(next_token) = self.dequeue_token() {
      return Ok(CursorState::InFile(next_token));
    };
    // Try refilling the token queue; if successful, return from queue.
    // Note that the queue may or may not be empty after this pop.
    if self.replenish_token_queue()? {
      let next_token = self.dequeue_token().unwrap();
      return Ok(CursorState::InFile(next_token));
    };
    // Token queue empty AND cannot refill, hence must be at EOF
    debug_assert!(self.reader.at_eof());
    return Ok(CursorState::EndOfFile);
  }
}

impl<'a> Lexer<'a> {
  fn replenish_token_queue(&mut self) -> fb::Result<bool> {
    // Reading out any leading spaces, tabs, and line comments.
    // After this, the cursor position is the correct start-of-token
    // position for a span.
    // Note that we do not skip any newline characters (including at the end of line comments)
    // to correctly generate indent, dedent, and end-of-line tokens UNLESS between parens,
    // brackets, or braces.
    self.skip_any_spaces_and_line_comments()?;

    // if at EOF...
    if self.reader.at_eof() {
      // if indent stack is not empty, can still generate 'dedent' tokens, else verify that
      // EOF is expected, e.g. no unterminated pair tokens (...), [...], {...}
      if self.indent_width_stack.len() == 1 {
        self.check_on_eof()?;
        return Ok(false);
      } else {
        let eof_pos = self.reader.cursor();
        let eof_span = self.span(eof_pos);
        self.enqueue_token(Token::new(eof_span, TokenInfo::EndOfLine));
        while self.indent_width_stack.len() > 1 {
          self.enqueue_token(Token::new(eof_span, TokenInfo::Dedent));
          self.indent_width_stack.pop();
        }
        debug_assert!(self.indent_width_stack.len() == 1);
        debug_assert!(*self.indent_width_stack.last().unwrap() == 0);
        return Ok(true);
      }
    }

    // parentheses, brackets, braces:
    if let Some(token) = self.try_scan_paren_bracket_brace()? {
      self.enqueue_token(token);
      return Ok(true);
    }

    // other punctuation:
    if let Some(token) = self.scan_punctuation()? {
      self.enqueue_token(token);
      return Ok(true);
    }

    // keywords and identifiers:
    if let Some(token) = self.scan_word()? {
      self.enqueue_token(token);
      return Ok(true);
    }

    // number literals: int or float:
    if let Some(token) = self.scan_number()? {
      self.enqueue_token(token);
      return Ok(true);
    }

    // string literals:
    if let Some(token) = self.scan_string_literal()? {
      self.enqueue_token(token);
      return Ok(true);
    }

    // try scanning line-endings (indent, dedent, eol)
    // - need to allow multiple tokens to be pushed to a queue
    //   - e.g. multiple dedents (arbitrary limit)
    //   - e.g. EOL, indent and EOL, dedent
    // - when obtaining tokens, must first try to de-queue before scanning more from reader
    // - consider using Rust's 'yield' statements (highly unstable though)
    if let Some(()) = self.scan_multiple_line_ending_tokens()? {
      return Ok(true);
    }

    // error: unexpected character, but not EOF
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
  fn skip_any_spaces_and_line_comments(&mut self) -> fb::Result<()> {
    loop {
      // non-newline whitespace
      if self.reader.match_char(' ')? || self.reader.match_char('\t')? {
        continue;
      }
      // line comments
      if self.reader.match_char('#')? {
        self.skip_any_bytes_until_newline()?;
        // After skipping out a line-comment, we always have a newline or EOF.
        // We should not skip newline because it is used for indent, dedent,
        // and EOL generation (consider `x = 5 # ...\n`; we need the EOL).
        // Hence safe to break here.
        break;
      }
      // skipping newlines if paren/bracket/brace stack is empty
      if !self.matching_token_pair_expectation_stack.is_empty() {
        if self.reader.match_char('\n')? {
          continue;
        }
      }
      // nothing left to skip; break.
      break;
    };
    Ok(())
  }
  fn skip_any_bytes_until_newline(&mut self) -> fb::Result<()> {
    while self.reader.match_char_if(|c| c != '\n')? {};
    Ok(())
  }
}

impl<'a> Lexer<'a> {
  fn scan_punctuation(&mut self) -> fb::Result<Option<Token>> {
    let first_pos = self.reader.cursor();
    macro_rules! token_span {
      () => { self.span(first_pos) };
    }
    if self.reader.match_char('.')? {
      return Ok(Some(Token::new(token_span!(), TokenInfo::Period)));
    }
    if self.reader.match_char(',')? {
      return Ok(Some(Token::new(token_span!(), TokenInfo::Comma)));
    }
    if self.reader.match_char(':')? {
      if self.reader.match_char('=')? {
        return Ok(Some(Token::new(token_span!(), TokenInfo::Update)));
      } else {
        return Ok(Some(Token::new(token_span!(), TokenInfo::Colon)));
      }
    }
    if self.reader.match_char('<')? {
      if self.reader.match_char('<')? {
        return Ok(Some(Token::new(token_span!(), TokenInfo::LeftShift)));
      } else if self.reader.match_char('=')? {
        return Ok(Some(Token::new(token_span!(), TokenInfo::LessThanOrEquals)));
      } else {
        return Ok(Some(Token::new(token_span!(), TokenInfo::LessThan)));
      }
    }
    if self.reader.match_char('>')? {
      if self.reader.match_char('>')? {
        return Ok(Some(Token::new(token_span!(), TokenInfo::RightShift)));
      } else if self.reader.match_char('=')? {
        return Ok(Some(Token::new(token_span!(), TokenInfo::GreaterThanOrEquals)));
      } else {
        return Ok(Some(Token::new(token_span!(), TokenInfo::GreaterThan)));
      }
    }
    if self.reader.match_char('=')? {
      if self.reader.match_char('=')? {
        return Ok(Some(Token::new(token_span!(), TokenInfo::Equals)));
      } else {
        return Ok(Some(Token::new(token_span!(), TokenInfo::Assign)));
      }
    }
    if self.reader.match_char('!')? {
      if self.reader.match_char('=')? {
        return Ok(Some(Token::new(token_span!(), TokenInfo::NotEquals)));
      } else {
        return Ok(Some(Token::new(token_span!(), TokenInfo::ExclamationPoint)));
      }
    }
    if self.reader.match_char('*')? {
      return Ok(Some(Token::new(token_span!(), TokenInfo::Asterisk)));
    }
    if self.reader.match_char('/')? {
      if self.reader.match_char('/')? {
        return Ok(Some(Token::new(token_span!(), TokenInfo::Quotient)));
      } else {
        return Ok(Some(Token::new(token_span!(), TokenInfo::Divide)));
      }
    }
    if self.reader.match_char('%')? {
      return Ok(Some(Token::new(token_span!(), TokenInfo::Modulo)));
    }
    if self.reader.match_char('+')? {
      return Ok(Some(Token::new(token_span!(), TokenInfo::Plus)));
    }
    if self.reader.match_char('-')? {
      return Ok(Some(Token::new(token_span!(), TokenInfo::Minus)));
    }
    if self.reader.match_char('&')? {
      if self.reader.match_char('&')? {
        return Ok(Some(Token::new(token_span!(), TokenInfo::LogicalAnd)));
      } else {
        return Ok(Some(Token::new(token_span!(), TokenInfo::BitwiseAnd)));
      };
    };
    if self.reader.match_char('|')? {
      if self.reader.match_char('|')? {
        return Ok(Some(Token::new(token_span!(), TokenInfo::LogicalOr)));
      } else {
        return Ok(Some(Token::new(token_span!(), TokenInfo::BitwiseOr)));
      };
    };
    if self.reader.match_char('^')? {
      return Ok(Some(Token::new(token_span!(), TokenInfo::BitwiseXOr)));
    }
    return Ok(None)
  }
}

impl<'a> Lexer<'a> {
  fn try_scan_paren_bracket_brace(&mut self) -> fb::Result<Option<Token>> {
    // opening characters:
    if let Some(token) = self.try_scan_opening_char('(', TokenInfo::LeftParenthesis, ')')? {
      return Ok(Some(token));
    };
    if let Some(token) = self.try_scan_opening_char('[', TokenInfo::LeftSquareBracket, ']')? {
      return Ok(Some(token));
    };
    if let Some(token) = self.try_scan_opening_char('{', TokenInfo::LeftCurlyBrace, '}')? {
      return Ok(Some(token));
    };
    // closing characters:
    if let Some(token) = self.try_scan_closing_char(')', TokenInfo::RightParenthesis, '(')? {
      return Ok(Some(token));
    };
    if let Some(token) = self.try_scan_closing_char(']', TokenInfo::RightSquareBracket, '[')? {
      return Ok(Some(token));
    };
    if let Some(token) = self.try_scan_closing_char('}', TokenInfo::RightCurlyBrace, '{')? {
      return Ok(Some(token));
    };
    return Ok(None);
  }
  fn try_scan_opening_char(&mut self, opening_char: char, opening_token_info: TokenInfo, closing_char: char) -> fb::Result<Option<Token>> {
    let first_pos = self.reader.cursor();
    if self.reader.match_char(opening_char)? {
      self.matching_token_pair_expectation_stack.push((self.span(first_pos), closing_char));
      return Ok(Some(Token::new(self.span(first_pos), opening_token_info)))
    } else {
      Ok(None)
    }
  }
  fn try_scan_closing_char(&mut self, closing_char: char, closing_token_info: TokenInfo, opening_char: char) -> fb::Result<Option<Token>> {
    let first_pos = self.reader.cursor();
    if self.reader.match_char(closing_char)? {
      match self.matching_token_pair_expectation_stack.pop() {
        Some((opening_paren_span, expected_char)) => {
          if closing_char == expected_char {
            Ok(Some(Token::new(self.span(first_pos), closing_token_info)))
          } else {
            Err(fb::Error::new().with_message(
              fb::Message::new(
                format!("Before '{}', expected '{}'", closing_char, expected_char)
              ).with_ref(
                String::from("opened here"), 
                fb::Loc::FileSpan(self.reader.source(), opening_paren_span)
              ).with_ref(
                String::from("see"), 
                fb::Loc::FileSpan(self.reader.source(), self.span(first_pos))
              )
            ))
          }
        },
        None => {
          // report an error indicating that extraneous ')' was found before an opening
          Err(fb::Error::new().with_message(
            fb::Message::new(
              format!("Before '{}', expected complementary '{}'", closing_char, opening_char)
            ).with_ref(
              String::from("see"),
              fb::Loc::FileSpan(self.reader.source(), self.span(first_pos))
            )
          ))
        }
      }
    } else {
      Ok(None)
    }
  }
}

impl<'a> Lexer<'a> {
  fn scan_word(&mut self) -> fb::Result<Option<Token>> {
    let first_pos = self.reader.cursor();
    let opt_first_char = self.reader.peek();
    if self.reader.match_char_if(|b| b.is_ascii_alphabetic() || b == '_')? {
      let first_char = opt_first_char.unwrap();
      let mut chars = Vec::with_capacity(IDENTIFIER_CAPACITY);
      chars.push(first_char);
      loop {
        let opt_later_char = self.reader.peek();
        if self.reader.match_char_if(|b| b.is_ascii_alphanumeric() || b == '_')? {
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
  fn scan_number(&mut self) -> fb::Result<Option<Token>> {
    let first_pos = self.reader.cursor();
    let opt_first_char = self.reader.peek();

    // If '0x' or '0X' detected, then should scan a hex integer chunk, no
    // hex floating point numbers.
    // Else should scan a decimal integer chunk;
    // decimal suffix is '[.<decimal-integer-chunk>][(e|E)<decimal-integer-chunk>]',
    // if suffix empty then just an integer, else float.

    if self.reader.match_char_if(|c| c.is_ascii_digit())? {
      Ok(Some(self.scan_nonempty_number(first_pos, opt_first_char.unwrap())?))
    } else {
      Ok(None)
    }
  }
  fn scan_nonempty_number(&mut self, first_pos: fb::Cursor, first_char: char) -> fb::Result<Token> {
    let is_hex_number =
      first_char == '0' &&
      self.reader.match_char_if(|b| b == 'x' || b == 'X')?;
    if is_hex_number {
      Ok(self.scan_nonempty_hex_number(first_pos)?)
    } else {
      Ok(self.scan_nonempty_decimal_number(first_pos, first_char)?)
    }
  }
  fn scan_nonempty_hex_number(&mut self, first_pos: fb::Cursor) -> fb::Result<Token> {
    let hex_int_mantissa = self.scan_hex_int_chunk()?;
    Ok(Token::new(
      self.span(first_pos),
      TokenInfo::LiteralInteger(hex_int_mantissa, IntegerFormat::Hexadecimal)
    ))
  }
  fn scan_nonempty_decimal_number(&mut self, first_pos: fb::Cursor, first_char: char) -> fb::Result<Token> {
    let mut is_float = false;
    let mantissa = {
      let mut mantissa = self.scan_decimal_int_chunk(Some(first_char))?;
      if self.reader.match_char('.')? {
        let post_point_int = self.scan_decimal_int_chunk(None)?;
        is_float = true;
        mantissa.reserve_exact(1 + post_point_int.len());
        mantissa.push('.');
        mantissa += post_point_int.as_str();
      };
      mantissa
    };
    let opt_exponent =
      if self.reader.match_char_if(|b| b == 'e' || b == 'E')? {
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
  fn scan_number_exponent_suffix(&mut self, mantissa: &String) -> fb::Result<String> {
    let start_of_suffix_pos = self.reader.cursor();
    let exponent_has_neg_prefix = self.reader.match_char('-')?;
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
  fn scan_hex_int_chunk(&mut self) -> fb::Result<String> {
    let mut hex_int_chunk_chars = Vec::with_capacity(HEXADECIMAL_INT_CHUNK_CAPACITY);
    loop {
      let opt_int_chunk_char = self.reader.peek();
      if self.reader.match_char_if(|b| b.is_ascii_hexdigit() || b == '_')? {
        hex_int_chunk_chars.push(opt_int_chunk_char.unwrap());
      } else {
        break;
      }
    };
    Ok(String::from_iter(hex_int_chunk_chars))
  }
  fn scan_decimal_int_chunk(&mut self, opt_first_char: Option<char>) -> fb::Result<String> {
    let mut decimal_int_chunk_chars = Vec::with_capacity(DECIMAL_INT_CHUNK_CAPACITY);
    if let Some(first_char) = opt_first_char {
      decimal_int_chunk_chars.push(first_char);
    }
    loop {
      let opt_int_chunk_char = self.reader.peek();
      if self.reader.match_char_if(|b| b.is_ascii_digit() || b == '_')? {
        decimal_int_chunk_chars.push(opt_int_chunk_char.unwrap());
      } else {
        break;
      }
    };
    Ok(String::from_iter(decimal_int_chunk_chars))
  }
}

impl<'a> Lexer<'a> {
  fn scan_string_literal(&mut self) -> fb::Result<Option<Token>> {
    let first_pos = self.reader.cursor();
    if self.reader.match_char('"')? {
      let mut literal_content_bytes: Vec<char> = Vec::new();
      let literal_terminated =
        loop {
          let glyph_pos = self.reader.cursor();
          let opt_peek_char = self.reader.peek();
          match opt_peek_char {
            Some(peek_char) => {
              if self.reader.match_char('\\')? {
                let escaped_char: char = self.scan_escape_sequence_suffix(glyph_pos)?;
                literal_content_bytes.push(escaped_char);
              } else if self.reader.match_char('"')? {
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
  fn scan_escape_sequence_suffix(&mut self, peek_pos: fb::Cursor) -> fb::Result<char> {
    if self.reader.match_char('"')? {
      Ok('"')
    } else if self.reader.match_char('n')? {
      Ok('\n')
    }  else if self.reader.match_char('r')? {
      Ok('\r')
    } else if self.reader.match_char('t')? {
      Ok('\t')
    } else if self.reader.match_char('a')? {
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
  fn scan_multiple_line_ending_tokens(&mut self) -> fb::Result<Option<()>> {
    let pre_eol_pos = self.reader.cursor();

    if self.reader.match_char('\n')? {
      let post_eol_pos = self.reader.cursor();

      // if there are any open parentheses, brackets, or braces, then we do not generate
      // any EOL, indent, or dedent tokens.
      if !self.matching_token_pair_expectation_stack.is_empty() {
        return Ok(None)
      };

      // counting the number of spaces immediately after this newline: this gives us
      // the indent width
      let this_indent_width = self.scan_indent_whitespace()?;

      // comparing the obtained count against the last value on the indent width stack,
      // generating tokens appropriately
      let last_indent_width = *self.indent_width_stack.last().unwrap();

      // always generating an EOL token before any indent, dedent
      let eol_token = Token::new(
        fb::Span::new(pre_eol_pos, post_eol_pos),
        TokenInfo::EndOfLine
      );
      self.enqueue_token(eol_token);

      // generating indent/dedent:
      if this_indent_width < last_indent_width {
        while this_indent_width < *self.indent_width_stack.last().unwrap() {
          self.indent_width_stack.pop();
          let dedent_token = Token::new(
            self.span(pre_eol_pos),
            TokenInfo::Dedent
          );
          self.enqueue_token(dedent_token);
        }
        let expected_indent_width = *self.indent_width_stack.last().unwrap();
        if this_indent_width != expected_indent_width {
          let error =
            fb::Error::new()
            .with_message(
              fb::Message::new(
                format!(
                  "Invalid indent: got block at depth {} spaces, but expected depth {} spaces",
                  this_indent_width, expected_indent_width
                )
              )
              .with_ref(
                String::from("indentation whitespace here"),
                fb::Loc::FileSpan(
                  self.reader.source(),
                  self.span(post_eol_pos)
                )
              )
            );

          return Err(error);
        }
      } else if this_indent_width > last_indent_width {
        self.indent_width_stack.push(this_indent_width);
        let indent_token = Token::new(self.span(post_eol_pos), TokenInfo::Indent);
        self.enqueue_token(indent_token);
      }
      // return Ok(Some(())) to indicate tokens were successfully eaten
      Ok(Some(()))
    } else {
      // return Ok(None) to indicate EOF without any errors
      Ok(None)
    }
  }
  fn scan_indent_whitespace(&mut self) -> fb::Result<i32> {
    let mut indent_width = 0;
    loop {
      match self.reader.peek() {
        Some(peek_char) => {
          if peek_char == ' ' {
            self.reader.skip()?;
            indent_width += 1;
          } else if peek_char == '\t' {
            self.reader.skip()?;
            indent_width += self.tab_width_in_spaces;
          } else {
            break;
          }
        },
        None => {
          break;
        }
      }
    };
    Ok(indent_width)
  }
}

impl<'a> Lexer<'a> {
  fn check_on_eof(&mut self) -> fb::Result<()> {
    if self.matching_token_pair_expectation_stack.is_empty() {
      // at EOF, all ok
      Ok(())
    } else {
      let mut error = fb::Error::new();
      while let Some((opening_span, closing_char)) = self.matching_token_pair_expectation_stack.pop() {
        error = error.with_message(
          fb::Message::new(
            format!("Before EOF, expected '{}' to match opening token", closing_char)
          ).with_ref(
            String::from("opening token here..."),
            fb::Loc::FileSpan(self.reader.source(), opening_span)
          )
        );
      };
      Err(error)
    }
  } 
}

//
// Common utility:
//

impl<'a> Lexer<'a> {
  fn new_keyword_map(intern_manager: &'a mut intern::Manager) -> HashMap<intern::IntStr, TokenInfo> {
    let mut kw_map = HashMap::with_capacity(6);
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
  fn span(&self, first_pos: fb::Cursor) -> fb::Span {
    fb::Span::new(first_pos, self.reader.cursor())
  }
}

impl<'a> Lexer<'a> {
  fn enqueue_token(&mut self, token: Token) {
    self.token_queue.push_back(token);
  }
  fn dequeue_token(&mut self) -> Option<Token> {
    self.token_queue.pop_front()
  }
}
