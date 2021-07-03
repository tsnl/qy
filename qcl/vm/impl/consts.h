// Constants are terse, serialized data in our universe of operation.
// They are used...
//  - ...as intermediaries of evaluation: evaluating expressions yields constants
//  - ...as a medium of output to other compiler modules
// Constants are always represented by a 64-bit/8-byte union.
//  - for unit, `Const` stores a 0-bit constant.
//  - for all number types, we use bit-casting to store numbers in the word
//  - for all other types, the 64-bit unsigned int is a pointer
//      - function pointers are special `FuncID`s
//      - arrays, structs, and unions are just a single pointer with memory
// This module expects RTTI checks to guarantee correctness.
//  - hence, all ops are fundamentally un-typed.
// NOTE: destruction only required for non-trivial types.

#pragma once

#include <stdint.h>

#include "core.h"

typedef union Const Const;
typedef struct CollectionConstInfo CollectionConstInfo;

//
//
// Inline type definitions:
//
//

union Const {
    uint8_t u8;
    uint16_t u16;
    uint32_t u32;
    uint64_t u64;

    int8_t s8;
    int16_t i16;
    int32_t i32;
    int64_t i64;

    float f32;
    double f64;

    FuncID fn_ptr;
    char const* str_data;
    uint8_t* data_ptr;
};
