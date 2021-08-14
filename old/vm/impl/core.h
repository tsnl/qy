#pragma once

#include <stdint.h>
#include <stddef.h>

typedef enum BinaryArithmeticOperator BinaryArithmeticOperator;
typedef enum BinaryComparisonOperator BinaryComparisonOperator;
typedef enum AdtKind AdtKind;
typedef enum Allocator Allocator;
typedef enum ValueKind ValueKind;

typedef size_t FuncID;
typedef size_t GDefID;
typedef size_t ExprID;
typedef size_t RtTypeID;

#define NULL_GDEF_ID ((GDefID)0)


enum BinaryArithmeticOperator {
    BAO_POW,
    BAO_MUL, BAO_DIV, BAO_REM,
    BAO_ADD, BAO_SUB
};
enum BinaryComparisonOperator {
    CMP_LT, CMP_GT,
    CMP_LE, CMP_GE,
    CMP_EQ, CMP_NE
};
enum Allocator {
    ALLOCATOR_STACK,
    ALLOCATOR_HEAP
};
enum AdtKind {
    ADT_STRUCT,
    ADT_ENUM
};
enum ValueKind {
    VAL_UNIT, VAL_STRING,
    VAL_UINT, VAL_SINT, VAL_FLOAT,
    VAL_PTR, VAL_ARRAY, VAL_SLICE,
    VAL_TUPLE, VAL_UNION,
    VAL_FN
};
