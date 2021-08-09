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

}