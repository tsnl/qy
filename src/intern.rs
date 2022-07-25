use super::*;
use std::collections::*;

pub type IntStr = usize;

pub struct IntStrManager {
    map: HashMap<String, IntStr>,
    tab: Vec<String>
}

impl IntStrManager {
    pub fn new () -> IntStrManager {
        IntStrManager {
            map: HashMap::with_capacity(tune::EXPECTED_MAX_SYMBOL_COUNT),
            tab: Vec::with_capacity(tune::EXPECTED_MAX_SYMBOL_COUNT)
        }
    }
    pub fn insert (&mut self, k: String) -> IntStr {
        if self.map.contains_key(&k) {
            self.map[&k]
        } else {
            let i = self.tab.len();
            self.map.insert(k.clone(), i);
            self.tab.push(k);
            i
        }
    }
    pub fn lookup (&self, i: IntStr) -> String {
        self.tab[i].clone()
    }
}
