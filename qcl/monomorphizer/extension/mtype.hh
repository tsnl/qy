#pragma once

#include <cstddef>

#include "id-mtype.hh"

namespace monomorphizer::mtype {

    // TODO: create a `MType` module that...
    //  - is pretty much identical to the python `type` module
    //  - re-generates IDs for all relevant types
    //  - creates new IDs upon substitution as required

    // NOTE: can consider a nominal type equality check rather than structural
    //   (i.e. same ID <=> same TID like in Python)
    //   since uniqueness is 'cached' with ArgList
    //   cf. val_equals

}
