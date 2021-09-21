#pragma once

#include <cstddef>

namespace monomorphizer {

    //
    // Shared enums:
    // FIXME: rename these like enums, not enum classes.
    //

    enum SES: size_t {
        SES_TOT,
        SES_DV,
        SES_ST,
        SES_EXN,
        SES_ML
    };

    enum UnaryOp: size_t {
        UNARY_LOGICAL_NOT,
        UNARY_DE_REF,
        UNARY_POS,
        UNARY_NEG
    };

    enum BinaryOp: size_t {
        BINARY_POW,
        BINARY_MUL, BINARY_DIV, BINARY_REM,
        BINARY_ADD, BINARY_SUB,
        BINARY_LT, BINARY_LE, BINARY_GT, BINARY_GE,
        BINARY_EQ, BINARY_NE,
        BINARY_LOGICAL_AND,
        BINARY_LOGICAL_OR
    };

    enum AllocationTarget: size_t {
        ALLOCATION_TARGET_STACK,
        ALLOCATION_TARGET_HEAP
    };

    enum IntegerSuffix: size_t {
        IS_U1, IS_U8, IS_U16, IS_U32, IS_U64,
        IS_S8, IS_S16, IS_S32, IS_S64
    };

    enum FloatSuffix: size_t {
        FS_F32, FS_F64
    };

    extern size_t const UNIVERSAL_NULL_ID;

}