#pragma once

namespace monomorphizer {

    //
    // Shared enums:
    // FIXME: rename these like enums, not enum classes.
    //

    enum SES: size_t {
        Tot,
        Dv,
        ST,
        Exn,
        ML
    };

    enum UnaryOp: size_t {
        LogicalNot,
        DeRef,
        Pos,
        Neg
    };

    enum BinaryOp: size_t {
        Pow,
        Mul, Div, Rem,
        Add, Sub,
        LessThan, LessThanOrEquals, GreaterThan, GreaterThanOrEquals,
        Equals, NotEquals,
        LogicalAnd,
        LogicalOr
    };

    enum AllocationTarget: size_t {
        Stack,
        Heap
    };

    enum IntegerSuffix: size_t {
        U1, U8, U16, U32, U64,
        S8, S16, S32, S64
    };

    enum FloatSuffix: size_t {
        F32, F64
    };

}