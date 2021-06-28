#pragma once

#include <cstdint>

#define VM_REGISTER_COUNT (16)

typedef struct VM VM;
typedef struct Function Function;
typedef struct BasicBlock BasicBlock;
typedef union Register Register;

//
// Interface:
//

VM* vm_create();
void vm_destroy(VM* vm);

Function* vm_add_func(VM* vm);
// todo: allow BasicBlock creation and building


//
// Inline type definitions:
//

union Register {
    int8_t i8;
    int16_t i16;
    int32_t i32;
    int64_t i64;

    uint8_t u8;
    uint16_t u16;
    uint32_t u32;
    uint64_t u64;

    float f32;
    double f64;

    uint8_t* ptr;
};
