#pragma once

#include <cstddef>
#include <string>

using IntStr = size_t;

namespace q4 {

    IntStr intern(std::string str);
    std::string const& internedString(IntStr is);

}
