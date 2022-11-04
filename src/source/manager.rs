use super::*;

use std::fmt::{Debug, Formatter, Result};

#[derive(Clone, Copy)]
pub struct SourceID(usize);

pub struct Manager {
  source_table: Vec<Source>,
  filepath_sid_map: HashMap<String, SourceID>
}

impl Manager {
  pub fn new() -> Manager {
    Manager {
      source_table: Vec::new(),
      filepath_sid_map: HashMap::new()
    }
  }
  fn add_fresh(&mut self, filepath: String) -> SourceID {
    let fresh_sid = SourceID(self.source_table.len());
    let new_source = Source::new(filepath.clone());
    self.source_table.push(new_source);
    self.filepath_sid_map.insert(filepath, fresh_sid);
    fresh_sid
  }
  pub fn add(&mut self, filepath: String) -> SourceID {
    let filepath = 
      if !filepath.starts_with("$DEBUG") {
        std::fs::canonicalize(filepath).unwrap().as_path().to_str().unwrap().to_owned()
      } else {
        filepath
      };
    match self.filepath_sid_map.get(&filepath) {
      Some(sid) => { *sid },
      None => { self.add_fresh(filepath) }
    }
  }
  pub fn get(&self, sid: SourceID) -> &Source {
    &self.source_table[sid.0]
  }
}

impl Debug for SourceID {
  fn fmt(&self, f: &mut Formatter) -> Result {
    f.write_fmt(format_args!("{}", &self.0))
  }
}
