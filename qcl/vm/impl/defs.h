// Each `DefID` corresponds to a unique symbol definition, regardless of name or scoping.
// This substitution must be performed ahead of time, by a scoper.

#pragma once

#include <stdint.h>

typedef size_t DefID;
