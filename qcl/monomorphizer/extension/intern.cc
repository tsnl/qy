#include "intern.hh"

#include <deque>
#include <map>

namespace monomorphizer::intern {

    static std::map<std::string, IntStr> s_intern_map;
    static std::deque<std::string> s_string_table;

    IntStr intern_string(std::string s) {
        auto it = s_intern_map.find(s);
        if (it != s_intern_map.end()) {
            return it->second;
        } else {
            auto i = s_string_table.size();
            s_string_table.push_back(s);
            s_intern_map.insert({s, i});
            return i;
        }
    }
    std::string get_interned_string(IntStr i) {
        return s_string_table[i];
    }

}