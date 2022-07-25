use crate::{fb::FeedbackManager, intern::IntStrManager};

use super::*;
use std::collections::*;

pub type FileID = usize;

pub struct SourceFileManager {
    sf_vec: Vec<File>,
    sf_map: HashMap<String, src::FileID>
}
pub struct File {
    path: String,
    opt_wb_ast: Option<ast::File>
}

impl SourceFileManager {
    pub fn new () -> SourceFileManager {
        SourceFileManager {
            sf_vec: Vec::with_capacity(tune::EXPECTED_MAX_SOURCE_FILE_COUNT),
            sf_map: HashMap::with_capacity(tune::EXPECTED_MAX_SOURCE_FILE_COUNT),
        }
    }

    // returns (SfID, fresh?)
    pub fn source_file (&mut self, path: String) -> (src::FileID, bool) {
        if !self.sf_map.contains_key(&path) {
            let sf_id = self.sf_map.len();
            self.sf_map.insert(path.clone(), sf_id);
            self.sf_vec.push(File { path: path, opt_wb_ast: None });
            (sf_id, true)
        } else {
            (self.sf_map[&path], false)
        }
    }

    pub fn source_file_filepath (&self, sfid: FileID) -> &str {
        self.sf_vec[sfid].path.as_str()
    }
}

impl SourceFileManager {
    // writeback AST
    pub fn writeback_ast (
        &mut self, 
        sfid: FileID,
        fbm: &mut Box<FeedbackManager>,
        im: &mut Box<IntStrManager>,
        parser_cb: fn (s: &String, fbm: &mut Box<FeedbackManager>, im: &mut Box<IntStrManager>) -> Result<ast::File, error::Error>
    ) {
        let file = &mut self.sf_vec[sfid];
        let parsed_file_res = parser_cb(&file.path, fbm, im);
        match parsed_file_res {
            Ok (ast_file) => {
                file.opt_wb_ast = Some(ast_file);
            },
            Err (e) => {
                // TODO: report this error
                println!("ERROR: something went wrong while parsing {}", &file.path);
                e.print();
            }
        }
    }
}

