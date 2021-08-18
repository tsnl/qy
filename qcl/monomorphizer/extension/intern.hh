#pragma once

#include <string>
#include "id-intern.hh"

namespace monomorphizer::intern {

    extern IntStr NULL_INTSTR_ID;

    IntStr intern_string(std::string s, bool is_tid_not_vid);
    std::string get_interned_string(IntStr i);
    bool is_interned_string_tid_not_vid(IntStr i);

}