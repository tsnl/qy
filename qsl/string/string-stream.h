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
    STRAND_KIND_STRING_REF, 
    STRAND_KIND_STRING_VIEW,
    STRAND_KIND_UNICODE_CHARACTER,
    STRAND_KIND_UINT, 
    STRAND_KIND_SINT,
    STRAND_KIND_F32, 
    STRAND_KIND_F64
} typedef StringStreamStrandKind;
union StringStreamStrandInfo {
    size_t raw[2];  // for size
    String* string_ref; StringView string_view;
    int unicode_character;
    struct { u64 v; i32 base; i32 flags; } uint; 
    struct { i64 v; i32 base; i32 flags; } sint;
    struct { f32 v; i32 base; i32 flags; } float_32; 
    struct { f64 v; i32 base; i32 flags; } float_64; 
};
static_assert(sizeof(StringStreamStrandInfo) == 2*sizeof(size_t), "Invalid StringStreamStrandInfo size");

#pragma pack(push, Words, 8)
struct StringStreamStrand { 
    StringStreamStrandKind kind; 
    StringStreamStrandInfo as; 
};
#pragma pack(pop, Words)
static_assert(sizeof(StringStreamStrand) == 3*sizeof(size_t), "Invalid StringStreamStrand size");

// Strands per chunk (k) must satisfy (3k+2) % 8 == 0 
// Select k=2  then each StringStreamChunk is exactly the size of 1  cache lines (64   bytes, 8   words)
// Select k=42 then each StringStreamChunk is exactly the size of 16 cache lines (1024 bytes, 128 words)
#define STRING_BUILDER_STRANDS_PER_CHUNK (42)

#pragma pack(push, Words, 8)
struct StringStreamChunk {
    StringStreamStrand strands[STRING_BUILDER_STRANDS_PER_CHUNK];
    size_t strands_count;
    StringStreamChunk* next;
};
#pragma pack(pop, Words)
static_assert(sizeof(StringStreamChunk) == 1024, "Invalid StringStreamChunk size");

#define DEFAULT_F32_PRINT_LENGTH 6
#define DEFAULT_F64_PRINT_LENGTH 9

///
// Interface definitions:
//

struct StringStream {
    StringStreamChunk head;                 // first chunk is stored inline
    StringStreamChunk* opt_external_tail;   // if NULL, implies inline 'head' is also tail
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
void string_stream_push_number_sint(StringStream* ss, i64 v, i32 base, i32 flags);
void string_stream_push_number_uint(StringStream* ss, u64 v, i32 base, i32 flags);
void string_stream_push_number_f32(StringStream* ss, f32 v, i32 base, i32 flags);
void string_stream_push_number_f64(StringStream* ss, f64 v, i32 base, i32 flags);
void string_stream_push_string_ref(StringStream* ss, String* str);
void string_stream_push_ascii_character(StringStream* ss, char ascii_code_point);
void string_stream_push_unicode_character(StringStream* ss, int unicode_code_point);

/// Getters:
bool string_stream_is_empty(StringStream* ss);
size_t string_stream_size(StringStream* ss);
