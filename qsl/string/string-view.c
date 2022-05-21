#include "string-view.h"

StringView new_string_view(String const* src, u32 beg, u32 end) {
    return (StringView) {
        .src = src,
        .span = {.beg = beg, .end = end}
    };
}
StringView view_string(String const* src) {
    return new_string_view(src, 0, string_length(src));
}
bool string_view_is_empty(StringView const* sv) {
    return sv->span.beg == sv->span.end;
}
size_t string_view_length(StringView const* sv) {
    return sv->span.end - sv->span.beg;
}