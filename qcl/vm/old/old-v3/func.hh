#pragma once

#include <cstdint>

#include "rtti.hh"

namespace qcl {

using FuncID = uint64_t;

struct FuncDecl {
    // todo: store a body of data without any definitions
  private:
    TID m_fn_tid;
};

struct FuncDefn {
    // todo: store a list of operations/instructions in a sequential form
    //  - default constructor: create an empty definition (no allocs please)
    //  - assign/move operator: overwrite [only empty/invalid defn] with new ones.
};

}   // namespace qcl
