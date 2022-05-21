#include "string.h"

#include <string.h>
#include <stddef.h>

#include "string-view.h"

#define MIN(x, y) (x < y ? x : y)

String new_string_from_cstr(char const* cstr, int length_hint, AllocCb alloc) {
    int count = length_hint;
    if (count < 0) {
        count = strlen(cstr);
    }
    String s = {
        .count = count,
        .nt_data = alloc(count+1)
    };
    memcpy(s.nt_data, cstr, count+1);
    return s;
}
void dispose_string(String* string, FreeCb free_cb) {
    if (free_cb) {
        free_cb(string->nt_data);
    } 
    string->count = 0;
    string->nt_data = NULL;
}

size_t string_length(String const* string) {
    return string->count;
}
bool string_is_empty(String const* string) {
    return string->count == 0;
}
