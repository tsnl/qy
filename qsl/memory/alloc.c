#include "alloc.h"

#include <stdlib.h>

void* stdlib_malloc_wrapper (u64 size) {
    return malloc(size);
}
void stdlib_free_wrapper(void* ptr) {
    free(ptr);
}
Allocator default_heap_allocator = {
    .alloc_cb = stdlib_malloc_wrapper,
    .free_cb = stdlib_free_wrapper
};
