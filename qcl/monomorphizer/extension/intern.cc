#include "intern.hh"

#include <map>
#include <vector>
#include <deque>

#include "shared-enums.hh"

namespace monomorphizer::intern {

    extern IntStr NULL_INTSTR_ID = UNIVERSAL_NULL_ID;

    // intern map: string -> IntStr
    static std::map<std::string, IntStr> s_intern_map;

    // lookup tables:
    static std::vector<bool> s_is_tid_not_vid_table;
    static std::deque<std::string> s_string_table;

    IntStr intern_string(std::string s, bool is_tid_not_vid) {
        auto it = s_intern_map.find(s);
        if (it != s_intern_map.end()) {
            return it->second;
        } else {
            auto i = s_string_table.size();

            // updating lookup tables:
            s_string_table.push_back(s);
            s_is_tid_not_vid_table.push_back(is_tid_not_vid);
            s_intern_map.insert({s, i});
            return i;
        }
    }
    std::string get_interned_string(IntStr i) {
        return s_string_table[i];
    }
    bool is_interned_string_tid_not_vid(IntStr i) {
        return s_is_tid_not_vid_table[i];
    }

}