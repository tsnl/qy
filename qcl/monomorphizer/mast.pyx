# distutils: language = c++

"""
MAST = Monomorphic AST
Monomorphization is just copying the AST many times over for each possible argument value.
All nodes are managed by a `NodeMgr`
"""

from libc.stddef cimport size_t
from libc.stdlib cimport calloc, free
from libcpp.vector cimport vector

import abc
import typing as t

from qcl import ast

#
# Nodes are IDed by 64-bit handles
#

ctypedef size_t MastNodeID
ctypedef MastNodeID MastExpID
ctypedef MastNodeID MastTypeSpecID
ctypedef MastNodeID MastModID

ctypedef size_t DefID


#
# Shared enums:
#

cdef enum MastSES:
    TOT,
    DV,
    ST,
    EXN,
    ML


cdef enum MastUnaryOp:
    LOGICAL_NOT,
    DE_REF,
    POS,
    NEG


cdef enum MastBinaryOp:
    POW,
    MUL,
    DIV,
    REM,
    ADD,
    SUB,
    LT, LE, GT, GE,
    EQ, NE,
    LOGICAL_AND,
    LOGICAL_OR


#
# Node Kind enum:
#

cdef enum NodeKind:
    # modules:
    MOD_SUB_MOD,

    # type-specifiers:
    TS_UNIT,
    TS_ID,
    TS_GET_MODULE_FIELD_BY_NAME_WITH_ARGS,
    TS_PTR,
    TS_ARRAY,
    TS_SLICE,
    TS_FUNC_SGN,
    TS_TUPLE,
    TS_STRUCT,
    TS_UNION,

    # expressions:
    EXP_UNIT,
    EXP_INT,
    EXP_FLOAT,
    EXP_STRING,
    EXP_ID,
    EXP_FUNC_CALL,
    EXP_UNARY_OP,
    EXP_BINARY_OP,
    EXP_IF_THEN_ELSE,
    EXP_GET_TUPLE_FIELD_BY_NAME,
    EXP_GET_TUPLE_FIELD_BY_INDEX,
    EXP_GET_MODULE_FIELD_BY_NAME_WITH_ARGS,
    EXP_LAMBDA,
    EXP_ALLOCATE_ONE,
    EXP_ALLOCATE_MANY,
    EXP_CHAIN


#
# Helpers:
#

cdef struct NameNodeRelation:
    DefID name
    MastNodeID node


cdef enum AllocationTarget:
    STACK,
    HEAP


#
# Mod Node Infos:
#

cdef struct SubModNodeInfo:
    NameNodeRelation* ordered_pairs
    size_t ordered_pair_count


#
# Type Spec Node Infos:
#

cdef struct IdTypeSpecNodeInfo:
    DefID def_id


cdef struct GetModuleFieldByNameWithArgsTypeSpecNodeInfo:
    MastModID sub_mod_id
    DefID field_name
    MastNodeID* actual_args_data
    size_t actual_args_count


cdef struct PtrTypeSpecNodeInfo:
    MastTypeSpecID ptd_ts
    int contents_is_mut


cdef struct ArrayTypeSpecNodeInfo:
    MastTypeSpecID ptd_ts
    MastExpID count_exp
    int contents_is_mut


cdef struct SliceTypeSpecNodeInfo:
    MastTypeSpecID ptd_ts
    int contents_is_mut


cdef struct FuncSgnTypeSpecNodeInfo:
    MastTypeSpecID arg_ts
    MastTypeSpecID ret_ts
    MastSES ret_ses


cdef struct TupleTypeSpecNodeInfo:
    MastTypeSpecID* elem_ts_data
    size_t elem_ts_count


cdef struct CompoundTypeSpecNodeInfo:
    NameNodeRelation* elem_ts_data
    size_t elem_ts_count


#
# Expression Node Infos:
#

cdef struct IntExpNodeInfo:
    size_t mantissa
    int is_neg


cdef struct FloatExpNodeInfo:
    double value


cdef struct StringExpNodeInfo:
    const char* byte_array
    size_t byte_count


cdef struct IdExpNodeInfo:
    DefID def_id


cdef struct FuncCallExpNodeInfo:
    MastExpID called_fn
    MastExpID* arg_exp_array
    size_t arg_exp_count
    int call_is_non_tot


cdef struct UnaryOpExpNodeInfo:
    MastExpID arg_exp
    MastUnaryOp unary_op


cdef struct BinaryOpExpNodeInfo:
    MastExpID lt_arg_exp
    MastExpID rt_arg_exp
    MastBinaryOp binary_op


cdef struct IfThenElseExpNodeInfo:
    MastExpID cond_exp
    MastExpID then_exp
    MastExpID else_exp


cdef struct GetTupleFieldByNameExpNodeInfo:
    MastExpID* field_array
    size_t field_count


cdef struct GetTupleFieldByIndexExpNodeInfo:
    MastExpID tuple_exp_id
    MastExpID index_exp_id


cdef struct GetModuleFieldByNameWithArgsExpNodeInfo:
    MastExpID module_exp_id
    DefID name_def_id
    MastNodeID* arg_node_array
    size_t arg_node_count


cdef struct LambdaExpNodeInfo:
    DefID* arg_name_array
    size_t arg_name_count
    MastExpID body_exp


cdef struct AllocateOneExpNodeInfo:
    MastExpID stored_val_exp_id
    AllocationTarget allocation_target
    int allocation_is_mut


cdef struct AllocateManyExpNodeInfo:
    MastExpID each_stored_val_exp_id
    MastExpID alloc_count
    AllocationTarget allocation_target
    int allocation_is_mut


cdef struct ChainExpNodeInfo:
    # TODO: encode each element in the table
    MastExpID ret_exp_id


cdef union NodeInfo:
    # modules:
    SubModNodeInfo mod_sub_mod,

    # type-specs:
    IdTypeSpecNodeInfo ts_id,
    GetModuleFieldByNameWithArgsTypeSpecNodeInfo ts_get_module_field_by_name_with_args,
    PtrTypeSpecNodeInfo ts_ptr,
    ArrayTypeSpecNodeInfo ts_array,
    SliceTypeSpecNodeInfo ts_slice,
    FuncSgnTypeSpecNodeInfo ts_func_sgn,
    TupleTypeSpecNodeInfo ts_tuple,
    CompoundTypeSpecNodeInfo ts_compound,

    # expressions:
    IntExpNodeInfo exp_int,
    FloatExpNodeInfo exp_float,
    StringExpNodeInfo exp_str,
    IdExpNodeInfo exp_id,
    FuncCallExpNodeInfo exp_call,
    UnaryOpExpNodeInfo exp_unary,
    BinaryOpExpNodeInfo exp_binary,
    IfThenElseExpNodeInfo exp_if_then_else,
    GetTupleFieldByNameExpNodeInfo exp_get_tuple_field_by_name,
    GetTupleFieldByIndexExpNodeInfo exp_get_tuple_field_by_index,
    GetModuleFieldByNameWithArgsExpNodeInfo exp_get_module_field_by_name_with_args,
    LambdaExpNodeInfo exp_lambda,
    AllocateOneExpNodeInfo exp_allocate_one,
    AllocateManyExpNodeInfo exp_allocate_many,
    ChainExpNodeInfo exp_chain



#
# Managing node properties:
#

cdef class NodeMgr(object):
    cdef NodeKind* kind_table
    cdef NodeInfo* info_table
    cdef size_t node_count
    cdef size_t node_capacity

    def __cinit__(self):
        self.kind_table = NULL
        self.info_table = NULL
        self.node_count = 0
        self.node_capacity = 0

    def __init__(self, capacity=4096):
        self.node_count = 0
        self.node_capacity = capacity
        self.kind_table = <NodeKind*> calloc(sizeof(NodeKind), self.node_capacity)
        self.info_table = <NodeInfo*> calloc(sizeof(NodeInfo), self.node_capacity)

    # TODO: implement methods to push various nodes
    # TODO: use these methods + lazily mapping sub-modules to MAST-icate
