#pragma once

#include "../memory/alloc.h"
#include "string.h"

#define STRING_BUILDER_CHUNK_COUNT (8)

struct StringStreamChunk {
    StringView chunks[STRING_BUILDER_CHUNK_COUNT];
    int count;
};

struct StringStream {
    StringStreamChunk* head;
    StringStreamChunk* tail;
    Allocator allocator;
};

void new_string_stream(void);
void string_stream_flush(void);
void string_stream_push(void);

