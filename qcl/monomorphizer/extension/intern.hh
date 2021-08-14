#pragma once

#include <string>
#include "id-intern.hh"

namespace monomorphizer::intern {

    IntStr intern_string(std::string s);
    std::string get_interned_string(IntStr i);

}