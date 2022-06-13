#include "string-stream.h"
#include <assert.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include "string-view.h"

///
// Implementation:
//

// ilog(v,b) finds the smallest exponent 'a' such that 'b^a >= v'
inline static size_t ilog(size_t v, size_t b) {
    assert(b != 0);
    size_t a = 0;
    for (size_t x = 1; x < v; x *= b) {
        a++;
    }
    return a;
}

StringStreamChunk new_string_stream_chunk() {
    return (StringStreamChunk) {
        .strands_count = 0,
        .next = NULL
    };
}
StringStreamChunk* string_stream_tail(StringStream* ss) {
    return ss->opt_external_tail ? ss->opt_external_tail : &ss->head;
}
StringStreamChunk* string_stream_append_chunk(StringStream* ss, StringStreamChunk chunk) {
    StringStreamChunk* new_chunk = ss->allocator.alloc_cb(sizeof(StringStreamChunk));
    *new_chunk = chunk;
    return new_chunk;
}
void string_stream_push_basic_strand(StringStream* ss, StringStreamStrand strand, size_t strand_length) {
    ss->running_length += strand_length;
    StringStreamChunk* tail = string_stream_tail(ss);
    if (tail->strands_count == STRING_BUILDER_STRANDS_PER_CHUNK) {
        // push new chunk, append there
        tail->next = ss->opt_external_tail = string_stream_append_chunk(ss, new_string_stream_chunk());
        ss->opt_external_tail->strands[0] = strand;
        ss->opt_external_tail->strands_count = 1;
    } else {
        // place exists in this chunk for a new strand
        size_t strand_index = tail->strands_count++;
        tail->strands[strand_index] = strand;
    }
}
inline static size_t unicode_code_point_length_in_utf8(int code_point) {
    // see: https://en.wikipedia.org/wiki/UTF-8
    if (code_point < (1U << (8-1))) {
        return 1;
    }
    if (code_point < (1U << (16-5))) {
        return 2;
    }
    if (code_point < (1U << (24-7))) {
        return 3;
    }
    if (code_point < (1U << (32-9))) {
        return 4;
    }
    assert(0 && "Invalid Unicode code point");
    return 0;   // not reachable
}

size_t int_strand_length(size_t number_len, bool has_base_prefix, bool is_signed) {
    size_t length = number_len;
    if (has_base_prefix) {
        length += 2;
    }
    if (is_signed) {
        length += 1;
    }
    return length;
}
size_t float_strand_length(size_t number_len, bool has_base_prefix) {
    size_t length = number_len;
    if (has_base_prefix) {
        length += 2;
    }
    bool is_signed = true;
    if (is_signed) {
        length += 1;
    }
    return length;
}

static size_t write_strand(char* buffer, size_t w_ix, StringStreamStrand strand);
static size_t write_strand__string_ref(char* buffer, size_t w_ix, StringStreamStrand strand);
static size_t write_strand__string_view(char* buffer, size_t w_ix, StringStreamStrand strand);
static size_t write_strand__uint(char* buffer, size_t w_ix, StringStreamStrand strand);
static size_t write_strand__sint(char* buffer, size_t w_ix, StringStreamStrand strand);
static size_t write_strand__f32(char* buffer, size_t w_ix, StringStreamStrand strand);
static size_t write_strand__f64(char* buffer, size_t w_ix, StringStreamStrand strand);
static size_t write_strand__unicode_char_utf8(char* buffer, size_t w_ix, StringStreamStrand strand);
static char digit_char(size_t digit);

static size_t write_strand(char* buffer, size_t w_ix, StringStreamStrand strand) {
    switch (strand.kind) {
        case STRAND_KIND_STRING_REF: return write_strand__string_ref(buffer, w_ix, strand);
        case STRAND_KIND_STRING_VIEW: return write_strand__string_view(buffer, w_ix, strand);
        case STRAND_KIND_UINT: return write_strand__uint(buffer, w_ix, strand);
        case STRAND_KIND_SINT: return write_strand__sint(buffer, w_ix, strand);
        case STRAND_KIND_F32: return write_strand__f32(buffer, w_ix, strand);
        case STRAND_KIND_F64: return write_strand__f64(buffer, w_ix, strand);
        case STRAND_KIND_UNICODE_CHARACTER: return write_strand__unicode_char_utf8(buffer, w_ix, strand);
        default: {
            assert(0 && "Unknown strand.");
            return 0;
        }
    }
}
static size_t write_strand__string_ref(char* buffer, size_t w_ix, StringStreamStrand strand) {
    String* string_ref = strand.as.string_ref;
    strncpy(buffer+w_ix, string_ref->nt_data, string_ref->count);
    return string_ref->count;
}
static size_t write_strand__string_view(char* buffer, size_t w_ix, StringStreamStrand strand) {
    StringView string_view = strand.as.string_view;
    size_t length = string_view_length(&string_view);
    strncpy(buffer+w_ix, string_view.src->nt_data + string_view.span.beg, length);
    return length;
}
static size_t write_strand__uint(char* buffer, size_t w_ix, StringStreamStrand strand) {
    size_t length = sprintf(buffer+w_ix, "%llu", strand.as.sint.v);
    assert(length == int_strand_length(ilog(strand.as.sint.v, strand.as.sint.base), strand.as.uint.base != 10, true));
    return length;
}
static size_t write_strand__sint(char* buffer, size_t w_ix, StringStreamStrand strand) {
    size_t length = sprintf(buffer+w_ix, "%+lld", strand.as.sint.v);
    assert(length == int_strand_length(ilog(strand.as.sint.v, strand.as.sint.base), strand.as.uint.base != 10, true));
    return length;
}
static size_t write_strand__f32(char* buffer, size_t w_ix, StringStreamStrand strand) {
    size_t length = sprintf(buffer+w_ix, "%+06.2f", strand.as.float_32.v);
    assert(length == float_strand_length(DEFAULT_F32_PRINT_LENGTH, strand.as.float_32.base != 10));
    return length;
}
static size_t write_strand__f64(char* buffer, size_t w_ix, StringStreamStrand strand) {
    size_t length = sprintf(buffer+w_ix, "%+09.4f", strand.as.float_64.v);
    assert(length == float_strand_length(DEFAULT_F64_PRINT_LENGTH, strand.as.float_64.base != 10));
    return length;
}
static size_t write_strand__unicode_char_utf8(char* buffer, size_t w_ix, StringStreamStrand strand) {
    // see: https://en.wikipedia.org/wiki/UTF-8
    int code_point = strand.as.unicode_character;
    if (code_point >= 0x10000) {
        // 4-byte sequence
        buffer[w_ix + 0] = 0xf0 | ((code_point >> 0) & 0x08);   // bits 0  through 2  (3 bits), header 11110 => 0xf0 header mask
        buffer[w_ix + 1] = 0x80 | ((code_point >> 3) & 0x3f);   // bits 3  through 8  (6 bits), header 10 => 0x80 header mask
        buffer[w_ix + 2] = 0x80 | ((code_point >> 9) & 0x3f);   // bits 9  through 14 (6 bits), header 10 => 0x80 header mask
        buffer[w_ix + 3] = 0x80 | ((code_point >> 15) & 0x3f);  // bits 15 through 20 (6 bits), header 10 => 0x80 header mask
        return 4;
    }
    if (code_point >= 0x800) {
        buffer[w_ix + 0] = 0xe0 | ((code_point >> 0) & 0x0f);   // bits 0  through 3  (4 bits), header 1110 => 0xe0 header mask
        buffer[w_ix + 1] = 0x80 | ((code_point >> 4) & 0x3f);   // bits 4  through 9  (6 bits), header 10 => 0x80 header mask
        buffer[w_ix + 2] = 0x80 | ((code_point >> 10) & 0x3f);  // bits 10 through 15 (6 bits), header 10 => 0x80 header mask
        return 3;
    }
    if (code_point >= 0x80) {
        buffer[w_ix + 0] = 0xc0 | ((code_point >> 0) & 0x1f);  // bits 0 through 4  (5 bits), header 110 => 0xc0 header mask
        buffer[w_ix + 1] = 0x80 | ((code_point >> 5) & 0x3f);  // bits 5 through 10 (6 bits), header 10  => 0x80 header mask
        return 2;
    }
    if (code_point >= 0 || true) {
        // just ascii
        buffer[w_ix] = code_point & 0x7f;
        return 1;
    }
}
static char digit_char(size_t digit) {
    if (digit < 10) {
        return '0' + digit;
    } else {
        assert(digit < 16);
        return 'a' + digit;
    }
}

///
// Interface
//

StringStream new_string_stream(Allocator allocator) {
    StringStream ss = {
        .head = new_string_stream_chunk(),
        .opt_external_tail = NULL,
        .allocator = allocator
    };
    return ss;
}
String string_stream_flush(StringStream* ss) {
    char* buffer = ss->allocator.alloc_cb(1 + ss->running_length);
    {
        size_t w_ix = 0;
        for (StringStreamChunk* chunk = &ss->head; chunk;) {
            for (size_t i = 0; i < chunk->strands_count; i++) {
                w_ix += write_strand(buffer, w_ix, chunk->strands[i]);
            }
            
            // iterating to next chunk, freeing current chunk
            StringStreamChunk* next_chunk = chunk->next;
            StringStreamChunk* curr_chunk = chunk;
            if (curr_chunk != &ss->head) {
                ss->allocator.free_cb(curr_chunk);
            }
            chunk = next_chunk;
        }
        assert(w_ix == ss->running_length);
        buffer[w_ix] = '\0';
    }

    return (String) {
        .count = ss->running_length,
        .nt_data = buffer
    };
}

void string_stream_push_string_view(StringStream* ss, StringView sv) {
    StringStreamStrand strand = {
        .kind = STRAND_KIND_STRING_VIEW,
        .as = {.string_view = sv}
    };
    string_stream_push_basic_strand(ss, strand, string_view_length(&sv));
}
void string_stream_push_number_i64(StringStream* ss, i64 v, i32 base, i32 flags) {
    assert(base == 2 || base == 10 || base == 16 && "Invalid base for 'string_stream_push_number_i64'");
    StringStreamStrand strand = {
        .kind = STRAND_KIND_SINT,
        .as = {.sint = {.v=v, .base=base, .flags=flags}}
    };
    string_stream_push_basic_strand(ss, strand, int_strand_length(ilog(v, base), base != 10, true));
}
void string_stream_push_number_u64(StringStream* ss, u64 v, i32 base, i32 flags) {
    assert(base == 2 || base == 10 || base == 16 && "Invalid base for 'string_stream_push_number_u64'");
    StringStreamStrand strand = {
        .kind = STRAND_KIND_UINT,
        .as = {.uint = {.v=v, .base=base, .flags=flags}}
    };
    string_stream_push_basic_strand(ss, strand, int_strand_length(ilog(v, base), base != 10, false));
}
void string_stream_push_number_f32(StringStream* ss, f32 v, i32 base, i32 flags) {
    assert(base == 10 && "Invalid base for 'string_stream_push_number_f32'");
    StringStreamStrand strand = {
        .kind = STRAND_KIND_F32,
        .as = {.float_32 = {.v=v, .base=base, .flags=flags}}
    };
    string_stream_push_basic_strand(ss, strand, float_strand_length(DEFAULT_F32_PRINT_LENGTH, base != 10));
}
void string_stream_push_number_f64(StringStream* ss, f64 v, i32 base, i32 flags) {
    assert(base == 10 && "Invalid base for 'string_stream_push_number_f64'");
    StringStreamStrand strand = {
        .kind = STRAND_KIND_F64,
        .as = {.float_64 = {.v=v, .base=base, .flags=flags}}
    };
    string_stream_push_basic_strand(ss, strand, float_strand_length(DEFAULT_F64_PRINT_LENGTH, base != 10));
}
void string_stream_push_string_ref(StringStream* ss, String* str) {
    StringStreamStrand strand = {
        .kind = STRAND_KIND_STRING_REF,
        .as = {.string_ref = str}
    };
    string_stream_push_basic_strand(ss, strand, str->count);
}
void string_stream_push_ascii_character(StringStream* ss, char ascii_code_point) {
    StringStreamStrand strand = {
        .kind = STRAND_KIND_UNICODE_CHARACTER,
        .as = {.unicode_character = ascii_code_point}
    };
    string_stream_push_basic_strand(ss, strand, 1);
}
void string_stream_push_unicode_character(StringStream* ss, int unicode_code_point) {
    StringStreamStrand strand = {
        .kind = STRAND_KIND_UNICODE_CHARACTER,
        .as = {.unicode_character = unicode_code_point}
    };
    string_stream_push_basic_strand(ss, strand, unicode_code_point_length_in_utf8(unicode_code_point));
}

bool string_stream_is_empty(StringStream* ss) {
    return ss->running_length == 0;
}
size_t string_stream_size(StringStream* ss) {
    return ss->running_length;
}
