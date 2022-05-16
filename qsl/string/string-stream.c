#include "string-stream.h"

StringStream new_string_stream(Allocator allocator) {
    return (StringStream) {
        .head = NULL,
        .tail = NULL,
        .allocator = allocator
    };
}
String string_stream_flush(StringStream* ss) {
    // TODO: build a string.
}

void string_stream_push_string_view(StringStream* ss, StringView sv) {
    
}
void string_stream_push_number_i8(StringStream* ss, i8 v) {
    
}
void string_stream_push_number_i16(StringStream* ss, i16 v) {

}
void string_stream_push_number_i32(StringStream* ss, i32 v) {

}
void string_stream_push_number_i64(StringStream* ss, i64 v) {

}
void string_stream_push_number_u8(StringStream* ss, i8 v) {

}
void string_stream_push_number_u16(StringStream* ss, i16 v) {

}
void string_stream_push_number_u32(StringStream* ss, i32 v) {

}
void string_stream_push_number_u64(StringStream* ss, i64 v) {

}
void string_stream_push_number_f32(StringStream* ss, f32 v) {

}
void string_stream_push_number_f64(StringStream* ss, f64 v) {

}
void string_stream_push_number_f128(StringStream* ss, f128 v) {

}
void string_stream_push_string_ref(StringStream* ss, String* str) {

}
void string_stream_push_ascii_character(StringStream* ss, char ascii_code_point) {
    
}
void string_stream_push_unicode_character(StringStream* ss, int unicode_code_point) {

}

bool string_stream_is_empty(StringStream* ss) {

}
size_t string_stream_size(StringStream* ss) {

}
