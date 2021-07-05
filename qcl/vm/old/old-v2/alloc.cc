#include "alloc.hh"

LinearAllocator alloc_create_linear_allocator(uint64_t capacity_in_bytes) {
    LinearAllocator allocator;
    allocator.memory = static_cast<uint8_t*>(malloc(capacity_in_bytes));
    allocator.capacity = capacity_in_bytes;
    allocator.count = 0;
    return allocator;
}

void alloc_destroy_linear_allocator(LinearAllocator* allocator) {
    free(allocator->memory);
    allocator->memory = nullptr;
    allocator->count = 0;
    allocator->capacity = 0;
}

uint8_t* alloc_allocate_linear_allocator(LinearAllocator* allocator, uint64_t size_in_bytes) {
    uint64_t new_count = allocator->count + size_in_bytes;
    if (new_count > allocator->capacity) {
        return nullptr;
    } else {
        uint64_t old_count = allocator->count;
        allocator->count = new_count;
        return allocator->memory + old_count;
    }
}
