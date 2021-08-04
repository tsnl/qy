// TODO: create a `MType` module that...
//  - is pretty much identical to the python `type` module
//  - re-generates IDs for all relevant types
//  - creates new IDs upon substitution as required
// This can be used by 

#pragma once

#include <cstddef>

namespace monomorphizer::mtype {

    using MTypeID = size_t;

}
