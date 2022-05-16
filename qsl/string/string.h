#pragma once

#include <stddef.h>
#include <stdbool.h>
#include "../prim/integer.h"
#include "../memory/alloc.h"

/// This is the default 'Qy' string type.
/// Every Qy string...
/// - immutable
/// - UTF-8 encoded
/// - contains the length AND is NULL-terminated for compatibility with C code
///   - NOTE: the string may contain an early, explicit null-terminating character.
struct String {
    char* nt_data;
    u32 count;
} typedef String;

/// Create/destroy:
String new_string_from_cstr(char const* cstr, int length_hint, AllocCb alloc);
void dispose_string(String* string, FreeCb free_cb);

/// Const accessors:
size_t string_length(String const* string);
bool string_is_empty(String const* string);

/// Sizing guarantees:
static_assert(sizeof(void*), "Expected to only be running on 64-bit systems.");
static_assert(sizeof(String) == 2*sizeof(size_t), "Expected 'String' to be 16B in size.");
