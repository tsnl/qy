use super::*;

#[derive(Debug)]
pub struct File {
    pub lang: Vec<IntStr>,
    pub forms: Vec<Form>
}
impl fmt::Display for File {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        for (i, form) in self.forms.iter().enumerate() {
            write!(f, "{}", form)?;
            if i < self.forms.len()-1 {
                write!(f, "\n")?;
            }
        };
        Ok(())
    }
}
