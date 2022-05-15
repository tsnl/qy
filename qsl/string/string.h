#pragma once

#include "../prim/integer.h"
#include "../memory/alloc.h"

/// This is the default 'Qy' string type.
/// Every Qy string...
/// - immutable
/// - UTF-8 encoded
/// - contains the length AND is NULL-terminated for compatibility with C code
///   - NOTE: the string may contain an early, explicit null-terminating character.
struct String {
    u64 count;
    char* nt_data;
    FreeCb free_cb;
} typedef String;

String new_string_from_cstr(char const* cstr, int length_hint, AllocCb alloc, FreeCb free);
void dispose_string(String* string);

/// This is the default 'Qy' string view type.
/// A string view must be created in most cases to use a string.
/// Since strings are immutable, they naturally only provide read-only access.
/// They do not need to be disposed
struct StringView {
    String const* src;
    u64 beg;
    u64 end;
} typedef StringView;

StringView new_string_view(String const* src, u64 beg, u64 end);
