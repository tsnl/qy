#include "string.h"

#include <string.h>
#include <stddef.h>

#define MIN(x, y) (x < y ? x : y)

String new_string_from_cstr(char const* cstr, int length_hint, AllocCb alloc, FreeCb free) {
    int count = length_hint;
    if (count < 0) {
        count = strlen(cstr);
    }
    String s = {
        .count = count,
        .nt_data = alloc(count+1),
        .free_cb = free
    };
    memcpy(s.nt_data, cstr, count+1);
    return s;
}
void dispose_string(String* string) {
    if (string->free_cb) {
        string->free_cb(string->nt_data);
    } 
    string->nt_data = NULL;
    string->free_cb = NULL;
}

StringView new_string_view(String const* string, u64 beg, u64 end) {
    StringView sv = {
        .src = string,
        .beg = beg,
        .end = MIN(end, string->count)
    };
    return sv;
}
