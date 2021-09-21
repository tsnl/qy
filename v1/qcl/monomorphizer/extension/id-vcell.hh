// V-Cell = Value Cell
// Each VCell stores an mval::VID that may mutate over time.
// Each VCell is used to model the contents of pointers.
// E.g. allocated memory is modeled as a cell that is referenced by a pointer.
// E.g. allocated slices are modeled using a vector of V-Cells

#pragma once

#include <cstddef>

namespace monomorphizer::vcell {
    using VCellID = size_t;
}
