use super::*;

#[derive(Clone, Copy)]
pub struct SourceID(usize);

pub struct SourceManager {
  source_table: Vec<Source>,
  filepath_sid_map: HashMap<String, SourceID>
}

impl SourceManager {
  pub fn new() -> SourceManager {
    SourceManager {
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
    let filepath_path_buf = std::fs::canonicalize(filepath).unwrap();
    let filepath = filepath_path_buf.as_path().to_str().unwrap().to_owned();
    match self.filepath_sid_map.get(&filepath) {
      Some(sid) => { *sid },
      None => { self.add_fresh(filepath) }
    }
  }
  pub fn get(&self, sid: SourceID) -> &Source {
    &self.source_table[sid.0]
  }
}

