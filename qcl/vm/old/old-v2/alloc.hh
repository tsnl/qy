#pragma once


struct LinearAllocator {
    uint8_t* memory;
    uint64_t capacity;
    uint64_t count;
};

LinearAllocator alloc_create_linear_allocator(uint64_t capacity_in_bytes);
void alloc_destroy_linear_allocate(LinearAllocator* allocator);
uint8_t* alloc_allocate_linear_allocator(LinearAllocator* allocator, uint64_t size_in_bytes);
