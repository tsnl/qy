use crate::*;
use crate::fb::{FeedbackManager,Loc};

use crate::intern::IntStrManager;
use crate::pest::Parser;
use crate::pest::iterators::{Pair as GenPair};

#[derive(Parser)]
#[grammar = "frontend/q7b.pest"]
pub struct Q7BaseParser;

type Result<T> = std::result::Result<T, error::Error>;
type Pair<'a> = GenPair<'a, Rule>;

struct AstBuilder<'a> {
    fbm: &'a mut Box<FeedbackManager>,
    im: &'a mut Box<IntStrManager>
}

impl<'a> AstBuilder<'a> {
    pub fn new(fbm: &'a mut Box<FeedbackManager>, im: &'a mut Box<IntStrManager>) -> Self {
        Self { fbm: fbm, im: im }
    }
    pub fn parse_file(&mut self, file: Pair) -> Result<ast::File> {
        // println!("file: {:?}", &file);
        let mut forms = Vec::with_capacity(1024);

        for record in file.into_inner() {
            match &record.as_rule() {
                Rule::form => {
                    let form = self.parse_form(record).unwrap();
                    forms.push(form)
                },
                Rule::EOI => {
                    break;
                },
                _ => { 
                    panic!("Unknown record in top-level of file: {:?}", record)
                }
            }
        }

        Ok(ast::File { lang: vec!{}, forms: forms })
    }
    pub fn parse_qq_form(&mut self, form: Pair) -> Result<ast::Form> {
        // println!("qq-form: {:?}", &form);
        let form = form.into_inner().next().unwrap();
        match form.as_rule() {
            Rule::list => {
                let mut elements = Vec::with_capacity(4);
                for record in form.into_inner()  {
                    elements.push(self.parse_form(record).unwrap())
                }
                Ok(ast::Form::List(elements))
            },
            Rule::atom => {
                let inner = self.parse_atom(form.into_inner().next().unwrap()).unwrap();
                Ok(ast::Form::Atom(inner))
            },
            Rule::quote => {
                let quoted = self.parse_form(form.into_inner().next().unwrap()).unwrap();
                Ok(ast::Form::Quote(Box::new(quoted)))
            },
            Rule::qq_escape => {
                let f = self.parse_form(form.into_inner().next().unwrap())?;
                Ok(ast::Form::QqEscape(Box::new(f)))
            },
            _ => {
                let loc = Loc::new_filewide();
                Err(error::Error::new()
                    .compose(loc, "unexpected Qq form".to_string()))
            }
        }
    }
    pub fn parse_form(&mut self, form: Pair) -> Result<ast::Form> {
        // println!("form: {:?}", &form);
        let form = form.into_inner().next().unwrap();
        match form.as_rule() {
            Rule::list => {
                let mut elements = Vec::with_capacity(4);
                for record in form.into_inner()  {
                    elements.push(self.parse_form(record).unwrap())
                }
                Ok(ast::Form::List(elements))
            },
            Rule::atom => {
                let inner = self.parse_atom(form.into_inner().next().unwrap()).unwrap();
                Ok(ast::Form::Atom(inner))
            },
            Rule::quote => {
                let quoted = self.parse_form(form.into_inner().next().unwrap()).unwrap();
                Ok(ast::Form::Quote(Box::new(quoted)))
            },
            Rule::quasiquote => {
                let quoted = self.parse_qq_form(form.into_inner().next().unwrap()).unwrap();
                Ok(ast::Form::QuasiQuote(Box::new(quoted)))
            },
            _ => {
                let loc = Loc::new_filewide();
                Err(error::Error::new()
                    .compose(loc, format!("unknown form: {:?}", form)))
            }
        }
    }
    pub fn parse_atom(&mut self, form: Pair) -> Result<ast::Atom> {
        // println!("atom: {:?}", &form);
        match form.as_rule() {
            Rule::symbol => {
                let im = self.im.insert(form.as_str().to_string());
                Ok(ast::Atom::Symbol(im))
            },
            Rule::integer => {
                let f_str = form.as_str();
                let mut chars = f_str.chars();
                let is_neg = chars.nth(0) == Some('-');
                let num_chars = if is_neg {f_str[1..].to_string()} else {f_str.to_string()};
                let num = num_chars.parse().unwrap();
                Ok(ast::Atom::Int(num, is_neg))
            },
            Rule::float => {
                let f_str = form.as_str();
                let mut chars = f_str.chars();
                let is_neg = chars.nth(0) == Some('-');
                let num_chars = if is_neg {f_str[1..].to_string()} else {f_str.to_string()};
                let num = num_chars.parse().unwrap();
                Ok(ast::Atom::Float(num))
            },
            Rule::string => {
                // todo: parse string inputs
                Ok(ast::Atom::Str(form.as_str().to_string()))
            },
            Rule::boolean => {
                let s = form.as_str();
                // get nth for n = 1 in '#t' or '#f'
                if let Some(nth) = s.chars().nth(1) {
                    Ok(ast::Atom::Bool(nth == 't'))
                } else {
                    panic!("bad text in str: '{}'", s)
                }
            },
            _ => {
                let s = form.as_str();
                panic!("bad atom: '{}'", s);
            }
        }
    }
}

pub fn parse_file (
    file_path: &String, 
    fbm: &mut Box<FeedbackManager>, 
    im: &mut Box<IntStrManager>
) -> Result<ast::File> {
    println!("{}", &file_path);
    let source = std::fs::read_to_string(file_path).unwrap();
    println!("parse start:");
    let file = Q7BaseParser::parse(Rule::file, source.as_str())
        .expect(format!("failed to parse source file {}", &file_path).as_str())
        .next().unwrap();

    let res = AstBuilder::new(fbm, im).parse_file(file).unwrap();
    
    println!("{}", &res);
    Ok(res)
}
