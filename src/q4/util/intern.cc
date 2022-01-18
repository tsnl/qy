#include "q4/util/intern.hh"

#include <map>
#include <deque>

namespace q4 {
    static std::map<std::string, IntStr> s_intern_map;
    static std::deque<std::string> s_interned_string_table;

    IntStr intern(std::string str) {
        auto new_is_id = s_intern_map.size();
        auto insert_res = s_intern_map.insert({str, new_is_id});
        if (insert_res.second) {
            s_interned_string_table.push_back(std::move(str));
            return new_is_id;
        } else {
            auto existing_it = insert_res.first;
            return existing_it->second;
        }
    }
    std::string const& internedString(IntStr is) {
        return s_interned_string_table[is];
    }
}