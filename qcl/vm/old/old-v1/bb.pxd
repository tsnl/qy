# distutils: language=c++

from libc.stdint cimport uint32_t
from libcpp.vector cimport vector as vec

from .interp cimport Interp


cdef:
    struct BasicBlock:
        vec[Op] ops


    enum OpCode:
        IMul, IDiv, IRem,
        IAdd, ISub,
        ILThan, IGThan, ILEq, IGEq, IEq, INEq,

        FMul, FDiv, FRem,
        FAdd, FSub,
        FLThan, FGThan, FLEq, FGEq, FEq, FNEq,

        Load, Store,

        Alloca, Malloc,
        Ite,
        Call,
        Return


    struct BinaryOpArgs:
        uint32_t lhs_rix
        uint32_t rhs_rix


    struct LoadArgs:
        uint32_t ptr_rix


    struct StoreArgs:
        uint32_t val_rix
        uint32_t ptr_rix


    struct GenericAllocArgs:
        uint32_t alloc_size_rix


    struct IteArgsData:
        BasicBlock* then_bb
        BasicBlock* else_bb
        uint32_t cond_rix


    struct IteArgs:
        IteArgsData* data


    union OpArgs:
        BinaryOpArgs i_bin_op_args
        BinaryOpArgs f_bin_op_args

        LoadArgs load_args
        StoreArgs store_args

        GenericAllocArgs alloca_args
        GenericAllocArgs malloc_args

        IteArgs ite_args


    struct Op:
        OpCode code
        OpArgs args


cdef:
    BasicBlock* create(Interp* interp)
    void destroy(BasicBlock* bb)

    uint32_t build_imul(BasicBlock* bb, uint32_t lhs_rix, uint32_t rhs_rix)
    uint32_t build_idiv(BasicBlock* bb, uint32_t lhs_rix, uint32_t rhs_rix)
    uint32_t build_irem(BasicBlock* bb, uint32_t lhs_rix, uint32_t rhs_rix)
    uint32_t build_iadd(BasicBlock * bb, uint32_t lhs_rix, uint32_t rhs_rix)
