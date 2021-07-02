// expressions are also instructions used to compute results.
// even though this is a lot of AST duplication, it's good enough and produces outstanding
// debug results.

#pragma once

#include <cstdint>

namespace qcl {

    using ExpID = uint64_t;

    ExpID exp_uint_literal(uint64_t value);
    ExpID exp_sint_literal(int64_t value);
    ExpID exp_float_literal(double value);
    ExpID exp_string_literal(uint64_t len, char const* bytes);

}