use super::*;

#[derive(Debug)]
pub struct Error {
  message_vec: Vec<Message>
}

#[derive(Debug)]
pub struct Message {
  text: String,
  source_refs: Vec<SourceRef>
}

#[derive(Debug)]
struct SourceRef {
  desc: String,
  loc: Loc
}
pub type Result<T> = std::result::Result<T, Error>;

impl Error {
  pub fn new() -> Error {
    Error{message_vec: Vec::new()}
  }
  pub fn with_message(self, message: Message) -> Error {
    let mut message_vec = self.message_vec;
    message_vec.push(message);
    Error{message_vec}
  }
}
impl Message {
  pub fn new(text: String) -> Message {
    Message { text, source_refs: Vec::new() }
  }
  pub fn with_ref(self, desc: String, loc: Loc) -> Message {
    let mut source_refs = self.source_refs;
    source_refs.push(SourceRef{desc, loc});
    Message { text: self.text, source_refs }
  }
}
