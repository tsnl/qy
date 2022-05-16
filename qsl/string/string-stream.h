#pragma once

#include <stddef.h>
#include <stdbool.h>
#include <assert.h>

#include "../memory/alloc.h"
#include "../prim/float.h"
#include "string.h"
#include "string-view.h"

static_assert(sizeof(void*) == 8, "Expected 64-bit system");

/// A string stream is an append-only list of string pieces.
/// It can be viewed as a lazily-evaluated 'concat' function whose 
/// arguments are added by successive message invocation.
typedef struct StringStream StringStream;

/// strands are the individual reference elements that make up a chunk.
typedef struct StringStreamStrand StringStreamStrand;
typedef union StringStreamStrandInfo StringStreamStrandInfo;

/// in theory, each strand is an item in a linked list.
/// to avoid allocating for each strand, we 'unroll' multiple adjacent nodes
/// into a single 'chunk'
typedef struct StringStreamChunk StringStreamChunk;

///
// Helper type definitions:
// these types are NOT a required part of the standard.
//

enum StringStreamStrandKind {
    STRING_REF, STRING_VIEW,
    UNICODE_CHARACTER,
    UINT, SINT,
    F32, F64, F128
} typedef StringStreamStrandKind;
union StringStreamStrandInfo {
    size_t raw[2];
    String* string_ref; StringView string_view;
    int unicode_character;
    u64 uint; i64 sint;
    f32 float_32; f64 float_64; f128 float_128;
};
static_assert(sizeof(StringStreamStrandInfo) == 2*sizeof(size_t), "Invalid StringStreamStrandInfo size");

#pragma pack(push, Words, 8)
struct StringStreamStrand { 
    StringStreamStrandKind kind; 
    StringStreamStrandInfo as; 
};
#pragma pack(pop, Words)
static_assert(sizeof(StringStreamStrand) == 3*sizeof(size_t), "Invalid StringStreamStrand size");

#define STRING_BUILDER_STRANDS_PER_CHUNK (2)

#pragma pack(push, Words, 8)
struct StringStreamChunk {
    StringStreamStrand strands[STRING_BUILDER_STRANDS_PER_CHUNK];
    size_t count;
    StringStreamChunk* next;
};
#pragma pack(pop, Words)
static_assert(sizeof(StringStreamChunk) == 8*sizeof(size_t), "Invalid StringStreamChunk size");

///
// Interface definitions:
//

struct StringStream {
    StringStreamChunk* head;
    StringStreamChunk* tail;
    Allocator allocator;
    size_t running_length;
} typedef StringStream;

/// New creates a new string stream.
StringStream new_string_stream(Allocator allocator);

/// Flush restores the stringstream to an 'empty' state and
/// returns a string whose contents match each piece pushed in.
String string_stream_flush(StringStream* ss);

/// Push formats a string piece and adds it to a string stream.
void string_stream_push_string_view(StringStream* ss, StringView sv);
void string_stream_push_number_i8(StringStream* ss, i8 v);
void string_stream_push_number_i16(StringStream* ss, i16 v);
void string_stream_push_number_i32(StringStream* ss, i32 v);
void string_stream_push_number_i64(StringStream* ss, i64 v);
void string_stream_push_number_u8(StringStream* ss, i8 v);
void string_stream_push_number_u16(StringStream* ss, i16 v);
void string_stream_push_number_u32(StringStream* ss, i32 v);
void string_stream_push_number_u64(StringStream* ss, i64 v);
void string_stream_push_number_f32(StringStream* ss, f32 v);
void string_stream_push_number_f64(StringStream* ss, f64 v);
void string_stream_push_number_f128(StringStream* ss, f128 v);
void string_stream_push_string_ref(StringStream* ss, String* str);
void string_stream_push_ascii_character(StringStream* ss, char ascii_code_point);
void string_stream_push_unicode_character(StringStream* ss, int unicode_code_point);

/// Getters:
bool string_stream_is_empty(StringStream* ss);
size_t string_stream_size(StringStream* ss);
