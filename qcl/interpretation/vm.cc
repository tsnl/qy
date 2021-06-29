#include "vm.hh"

#include <cstdlib>

#include <vector>

//
// LinearAllocator implementation
//

struct LinearAllocator {
    uint8_t* memory;
    uint64_t capacity;
    uint64_t count;
};

LinearAllocator create_linear_allocator(uint64_t capacity_in_bytes) {
    LinearAllocator allocator;
    allocator.memory = static_cast<uint8_t*>(malloc(capacity_in_bytes));
    allocator.capacity = capacity_in_bytes;
    allocator.count = 0;
    return allocator;
}

void destroy_linear_allocator(LinearAllocator* allocator) {
    free(allocator->memory);
    allocator->memory = nullptr;
    allocator->count = 0;
    allocator->capacity = 0;
}

uint8_t* try_allocate(LinearAllocator* allocator, uint64_t size_in_bytes) {
    uint64_t new_count = allocator->count + size_in_bytes;
    if (new_count > allocator->capacity) {
        return nullptr;
    } else {
        uint64_t old_count = allocator->count;
        allocator->count = new_count;
        return allocator->memory + old_count;
    }
}

void free(LinearAllocator* allocator, uint8_t* ptr) {
    // do nothing: we clean up all memory at once.
}

//
// Function & Basic Block implementations
//

struct BasicBlock {
    // todo: implement me
};

struct Function {
    // todo: implement me
};

//
// Frame implementations
//

struct Frame {
    // todo: implement me
};

//
// VM implementation
//

struct VM {
    Register registers[VM_REGISTER_COUNT];
    std::vector<Function> functions;
    std::vector<Frame> frame_stack;
    LinearAllocator stack;
    LinearAllocator heap;
};

