use super::*;

pub struct Compiler {
    pub fbm: Box<fb::FeedbackManager>,
    pub sfm: Box<src::SourceFileManager>,
    pub im: Box<intern::IntStrManager>
}

impl Compiler {
    pub fn new () -> Compiler {
        Compiler { 
            fbm: Box::new(fb::FeedbackManager::new()), 
            sfm: Box::new(src::SourceFileManager::new()),
            im: Box::new(intern::IntStrManager::new())
        }
    }
}
impl Compiler {
    pub fn compile (&mut self, entry_point_filepath: String) {
        let (sfid, is_fresh) = self.sfm.source_file(entry_point_filepath);
        if !is_fresh {
            return;
        }
        // need to compile this file
        self.sfm.writeback_ast(sfid, &mut self.fbm, &mut self.im, frontend::parse_file);
    }
}
