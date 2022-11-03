use std::collections::HashMap;
use std::hash::Hash;

use std::fmt::{Debug, Formatter, Result};

#[derive(PartialEq, Eq, Hash, Clone, Copy)]
pub struct IntStr {
  id: usize
}

pub struct Manager {
  string_to_id_map: HashMap<String, IntStr>,
  id_to_string_lut: Vec<String>
}

impl Manager {
  pub fn new() -> Manager {
    Manager {
      string_to_id_map: HashMap::new(),
      id_to_string_lut: Vec::new()
    }
  }
  pub fn intern(&mut self, s: String) -> IntStr {
    if self.string_to_id_map.contains_key(&s) {
      self.string_to_id_map[&s]
    } else {
      let int_str = IntStr { id: self.id_to_string_lut.len() };
      self.string_to_id_map.insert(s.clone(), int_str);
      self.id_to_string_lut.push(s);
      int_str
    }
  }
  pub fn lookup(&self, i: IntStr) -> String {
    self.id_to_string_lut[i.id].clone()
  }
}

impl Debug for IntStr {
  fn fmt(&self, f: &mut Formatter<'_>) -> Result {
      f.write_fmt(format_args!("<IntStr:{}>", self.id))
  }
}