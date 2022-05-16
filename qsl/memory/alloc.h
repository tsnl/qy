#pragma once

#include "../prim/integer.h"

typedef void*(*AllocCb)(u64 size);
typedef void(*FreeCb)(void* ptr);
    
struct {
    AllocCb alloc_cb;
    FreeCb free_cb;
} typedef Allocator;
