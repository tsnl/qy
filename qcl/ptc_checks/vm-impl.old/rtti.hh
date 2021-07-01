#pragma once

#include <cstdint>

namespace qcl {

typedef uint64_t TID;

// todo: acquire type info from the `typer` module.
//  - 'kinds' required to perform virtually any operation
//  - 'elem' properties required to serialize tuples, structs, etc.

// this should be easy to export from Python since sequential integer keys map to
// a struct of properties.

}   // namespace qcl
