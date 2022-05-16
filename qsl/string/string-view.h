#pragma once

#include <stdbool.h>
#include "../prim/integer.h"
#include "string.h"

/// This is the default 'Qy' string view type.
/// A string view must be created in most cases to use a string.
/// Since strings are immutable, they naturally only provide read-only access.
/// They do not need to be disposed.
/// WARNING: 'end' in span refers to 'past-the-end' marker just like in C++, not the
/// index of the last element.
/// This allows us to encode empty views using `beg==end`
struct StringView {
    String const* src;
    struct { u32 beg; u32 end; } span;
} typedef StringView;

/// Construct/destroy:
StringView new_string_view(String const* src, u64 beg, u64 end);
StringView to_string_view(String const* src);

/// Const accessors:
bool string_view_is_empty(StringView const* sv);
size_t string_view_length(StringView const* sv);

/// Sizing guarantees:
static_assert(sizeof(void*), "Expected to only be running on 64-bit systems.");
static_assert(sizeof(StringView) == 2*sizeof(size_t), "Expected 'StringView' to be 16B in size.");
