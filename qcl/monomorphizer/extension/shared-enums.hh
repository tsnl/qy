#pragma once

namespace monomorphizer {

    //
    // Shared enums:
    //

    enum class SES {
        Tot,
        Dv,
        ST,
        Exn,
        ML
    };

    enum class UnaryOp {
        LogicalNot,
        DeRef,
        Pos,
        Neg
    };

    enum class BinaryOp {
        Pow,
        Mul, Div, Rem,
        Add, Sub,
        LessThan, LessThanOrEquals, GreaterThan, GreaterThanOrEquals,
        Equals, NotEquals,
        LogicalAnd,
        LogicalOr
    };

    enum class AllocationTarget {
        Stack,
        Heap
    };

    enum class IntegerSuffix {
        U1, U8, U16, U32, U64,
        S8, S16, S32, S64
    };

    enum class FloatSuffix {
        F32, F64
    };

}