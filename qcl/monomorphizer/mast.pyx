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
from collections import namedtuple

from qcl import ast

#
# Nodes are IDed by 64-bit handles
#

ctypedef size_t MastNodeID
ctypedef MastNodeID MastModID
ctypedef MastNodeID MastExpID
ctypedef MastNodeID MastTypeSpecID
ctypedef MastNodeID MastElemID

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
    EXP_GET_TUPLE_FIELD_BY_INDEX,
    EXP_GET_MODULE_FIELD_BY_NAME_WITH_ARGS,
    EXP_LAMBDA,
    EXP_ALLOCATE_ONE,
    EXP_ALLOCATE_MANY,
    EXP_CHAIN

    # chain elements:
    ELEM_BIND1V,
    ELEM_DO


#
# Helpers:
#

cdef struct NameNodeRelation:
    DefID name
    MastNodeID node


PyNameNodeRelation = namedtuple(
    "PyNameNodeRelation",
    [
        "name",     # DefID
        "node"      # MastNodeID
    ]
)


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
    bint contents_is_mut


cdef struct ArrayTypeSpecNodeInfo:
    MastTypeSpecID ptd_ts
    MastExpID count_exp
    bint contents_is_mut


cdef struct SliceTypeSpecNodeInfo:
    MastTypeSpecID ptd_ts
    bint contents_is_mut


cdef struct FuncSgnTypeSpecNodeInfo:
    MastTypeSpecID arg_ts
    MastTypeSpecID ret_ts
    MastSES ret_ses


cdef struct TupleTypeSpecNodeInfo:
    MastTypeSpecID* elem_ts_array
    size_t elem_ts_count


cdef struct CompoundTypeSpecNodeInfo:
    NameNodeRelation* elem_ts_array
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
    int* code_point_array
    size_t code_point_count


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
    bint allocation_is_mut


cdef struct AllocateManyExpNodeInfo:
    MastExpID initializer_stored_val_exp_id
    MastExpID alloc_count_exp
    AllocationTarget allocation_target
    bint allocation_is_mut


cdef struct ChainExpNodeInfo:
    MastElemID* prefix_elem_array
    size_t prefix_elem_count
    MastExpID ret_exp_id


#
# Element Node Info
#

cdef struct Bind1VElem:
    DefID bound_def_id
    MastExpID init_exp_id


cdef struct DoElem:
    MastExpID eval_exp_id


#
#
# Union
#
#

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
    GetTupleFieldByIndexExpNodeInfo exp_get_tuple_field_by_index,
    GetModuleFieldByNameWithArgsExpNodeInfo exp_get_module_field_by_name_with_args,
    LambdaExpNodeInfo exp_lambda,
    AllocateOneExpNodeInfo exp_allocate_one,
    AllocateManyExpNodeInfo exp_allocate_many,
    ChainExpNodeInfo exp_chain,

    # elements:
    Bind1VElem elem_bind1v,
    DoElem elem_do



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

    #
    # Node property accessors:
    #

    cdef public NodeInfo* get_info_ptr(self, MastNodeID node_id):
        node_index = <size_t>node_id
        return &self.info_table[node_index]

    #
    # Shared helpers:
    #

    cdef MastNodeID help_alloc_node(self, NodeKind kind):
        new_node_index = self.node_count
        self.node_count += 1
        assert self.node_count <= self.node_capacity

        self.kind_table[new_node_index] = kind

        new_node_id = <MastNodeID>new_node_index
        return new_node_id

    cdef MastTypeSpecID help_new_compound_ts(
            self,
            object elem_ts_list: t.List[PyNameNodeRelation],
            NodeKind node_kind
    ):
        new_node_id = self.help_alloc_node(node_kind)
        info_ptr = <CompoundTypeSpecNodeInfo*> (
            &self.get_info_ptr(new_node_id).ts_compound
        )

        elem_ts_count = len(elem_ts_list)

        info_ptr.elem_ts_count = elem_ts_count
        info_ptr.elem_ts_array = <NameNodeRelation*> calloc(elem_ts_count, sizeof(NameNodeRelation))
        for index, (name, node) in enumerate(elem_ts_list):
            rel_ptr = <NameNodeRelation*> &info_ptr.elem_ts_array[index]
            rel_ptr.name = <DefID> name
            rel_ptr.node = <MastTypeSpecID> node

        return new_node_id

    #
    # Modules:
    #

    cdef public MastNodeID new_sub_mod(
            self,
            object name_node_relation_list: t.List[PyNameNodeRelation]
    ):
        new_node_id = self.help_alloc_node(NodeKind.MOD_SUB_MOD)
        info_ptr = &self.get_info_ptr(new_node_id).mod_sub_mod

        pair_count = len(name_node_relation_list)
        info_ptr.ordered_pair_count = pair_count
        info_ptr.ordered_pairs =  <NameNodeRelation*> calloc(pair_count, sizeof(NameNodeRelation))
        for index, (name, node) in enumerate(name_node_relation_list):
            rel_ptr = <NameNodeRelation*> &info_ptr.ordered_pairs[index]
            rel_ptr.name = <DefID> int(name)
            rel_ptr.node = <MastNodeID> int(node)

        return new_node_id

    #
    # Type-specifiers:
    #

    cdef public MastTypeSpecID new_unit_ts(self):
        new_node_id = self.help_alloc_node(NodeKind.TS_UNIT)
        return new_node_id

    cdef public MastTypeSpecID new_id_ts(self, DefID def_id):
        new_node_id = self.help_alloc_node(NodeKind.TS_ID)
        info_ptr = self.get_info_ptr(new_node_id)

        info_ptr.ts_id.def_id = def_id

        return new_node_id

    cdef public MastTypeSpecID new_get_module_field_by_name_with_args_ts(
            self,
            MastModID mod_id,
            DefID field_name,
            object actual_args_list: t.List["MastNodeID"]
    ):
        new_node_id = self.help_alloc_node(NodeKind.TS_ID)
        info_ptr = <GetModuleFieldByNameWithArgsTypeSpecNodeInfo*> (
            &self.get_info_ptr(new_node_id).ts_get_module_field_by_name_with_args
        )

        actual_arg_count = len(actual_args_list)

        info_ptr.sub_mod_id = mod_id
        info_ptr.field_name = field_name
        info_ptr.actual_args_count = actual_arg_count
        info_ptr.actual_args_data = <MastNodeID*> calloc(actual_arg_count, sizeof(MastNodeID))
        for index, arg_node_id in enumerate(actual_args_list):
            info_ptr.actual_args_data[index] = arg_node_id

        return new_node_id

    cdef public MastTypeSpecID new_ptr_ts(
            self,
            MastTypeSpecID ptd_ts,
            bint contents_is_mut
    ):
        new_node_id = self.help_alloc_node(NodeKind.TS_PTR)
        info_ptr = <PtrTypeSpecNodeInfo*> (
            &self.get_info_ptr(new_node_id).ts_ptr
        )

        info_ptr.ptd_ts = ptd_ts
        info_ptr.contents_is_mut = contents_is_mut

        return new_node_id

    cdef public MastTypeSpecID new_array_ts(
            self,
            MastTypeSpecID ptd_ts,
            MastExpID count_exp,
            bint contents_is_mut
    ):
        new_node_id = self.help_alloc_node(NodeKind.TS_ARRAY)
        info_ptr = <ArrayTypeSpecNodeInfo*> (
            &self.get_info_ptr(new_node_id).ts_array
        )

        info_ptr.ptd_ts = ptd_ts
        info_ptr.count_exp = count_exp
        info_ptr.contents_is_mut = contents_is_mut

        return new_node_id

    cdef MastTypeSpecID new_slice_ts(
            self,
            MastTypeSpecID ptd_ts,
            bint contents_is_mut
    ):
        new_node_id = self.help_alloc_node(NodeKind.TS_SLICE)
        info_ptr = <SliceTypeSpecNodeInfo*> (
            &self.get_info_ptr(new_node_id).ts_slice
        )

        info_ptr.ptd_ts = ptd_ts
        info_ptr.contents_is_mut = contents_is_mut

        return new_node_id

    cdef MastTypeSpecID new_func_sgn_ts(
            self,
            MastTypeSpecID arg_ts,
            MastTypeSpecID ret_ts,
            MastSES ret_ses
    ):
        new_node_id = self.help_alloc_node(NodeKind.TS_FUNC_SGN)
        info_ptr = <FuncSgnTypeSpecNodeInfo*> (
            &self.get_info_ptr(new_node_id).ts_func_sgn
        )

        info_ptr.arg_ts = arg_ts
        info_ptr.ret_ts = ret_ts
        info_ptr.ret_ses = ret_ses

        return new_node_id

    cdef MastTypeSpecID new_tuple_ts(
            self,
            object elem_ts_list: t.List["MastTypeSpecID"]
    ):
        new_node_id = self.help_alloc_node(NodeKind.TS_TUPLE)
        info_ptr = <TupleTypeSpecNodeInfo*> (
            &self.get_info_ptr(new_node_id).ts_tuple
        )

        elem_ts_count = len(elem_ts_list)

        info_ptr.elem_ts_count = elem_ts_count
        info_ptr.elem_ts_array = <MastTypeSpecID*> calloc(elem_ts_count, sizeof(MastTypeSpecID))
        for index, elem_ts_id in enumerate(elem_ts_list):
            info_ptr.elem_ts_array[index] = elem_ts_id

        return new_node_id

    cdef MastTypeSpecID new_struct_ts(
            self,
            object elem_ts_list: t.List[PyNameNodeRelation]
    ):
        return self.help_new_compound_ts(
            elem_ts_list,
            NodeKind.TS_STRUCT
        )

    cdef MastTypeSpecID new_union_ts(
            self,
            object elem_ts_list: t.List[PyNameNodeRelation]
    ):
        return self.help_new_compound_ts(
            elem_ts_list,
            NodeKind.TS_UNION
        )

    #
    # Expressions:
    #

    cdef MastExpID new_unit_exp(self):
        new_node_id = self.help_alloc_node(NodeKind.EXP_UNIT)
        return new_node_id

    cdef MastExpID new_int_exp(
            self,
            size_t mantissa,
            int is_neg
    ):
        new_node_id = self.help_alloc_node(NodeKind.EXP_INT)
        info_ptr = <IntExpNodeInfo*> (
            &self.get_info_ptr(new_node_id).exp_int
        )

        info_ptr.mantissa = mantissa
        info_ptr.is_neg = is_neg

        return new_node_id

    cdef MastExpID new_float_exp(
            self,
            double value
    ):
        new_node_id = self.help_alloc_node(NodeKind.EXP_FLOAT)
        info_ptr = <FloatExpNodeInfo*> (
            &self.get_info_ptr(new_node_id).exp_float
        )

        info_ptr.value = value

        return new_node_id

    cdef MastExpID new_string_exp(
            self,
            object code_point_list: t.List[int]
    ):
        new_node_id = self.help_alloc_node(NodeKind.EXP_STRING)
        info_ptr = <StringExpNodeInfo*> (
            &self.get_info_ptr(new_node_id).exp_str
        )

        code_point_count = len(code_point_list)

        info_ptr.code_point_count = code_point_count
        info_ptr.code_point_array = <int*> calloc(code_point_count, sizeof(int))
        for index, code_point in enumerate(code_point_list):
            info_ptr.code_point_array[index] = code_point

        return new_node_id

    cdef MastExpID new_id_exp(
            self,
            DefID def_id
    ):
        new_node_id = self.help_alloc_node(NodeKind.EXP_ID)
        info_ptr = <IdExpNodeInfo*> (
            &self.get_info_ptr(new_node_id).exp_id
        )

        info_ptr.def_id = def_id

        return new_node_id

    cdef MastExpID new_func_call_exp(
            self,
            MastExpID called_fn,
            object arg_exp_ids: t.List["MastExpID"],
            bint call_is_non_tot
    ):
        new_node_id = self.help_alloc_node(NodeKind.EXP_FUNC_CALL)
        info_ptr = <FuncCallExpNodeInfo*> (
            &self.get_info_ptr(new_node_id).exp_call
        )

        arg_count = len(arg_exp_ids)

        info_ptr.called_fn = called_fn
        info_ptr.arg_exp_count = arg_count
        info_ptr.arg_exp_array = <MastExpID*> calloc(arg_count, sizeof(MastExpID))
        for index, arg_exp_id in enumerate(arg_exp_ids):
            info_ptr.arg_exp_array[index] = arg_exp_id

        return new_node_id

    cdef MastExpID new_unary_op_exp(
            self,
            MastUnaryOp unary_op,
            MastExpID arg_exp
    ):
        new_node_id = self.help_alloc_node(NodeKind.EXP_UNARY_OP)
        info_ptr = <UnaryOpExpNodeInfo*> (
            &self.get_info_ptr(new_node_id).exp_unary
        )

        info_ptr.arg_exp = arg_exp
        info_ptr.unary_op = unary_op

        return new_node_id

    cdef MastExpID new_binary_op_exp(
            self,
            MastBinaryOp binary_op,
            MastExpID lt_arg_exp,
            MastExpID rt_arg_exp
    ):
        new_node_id = self.help_alloc_node(NodeKind.EXP_BINARY_OP)
        info_ptr = <BinaryOpExpNodeInfo*> (
            &self.get_info_ptr(new_node_id).exp_binary
        )

        info_ptr.lt_arg_exp = lt_arg_exp
        info_ptr.rt_arg_exp = rt_arg_exp
        info_ptr.binary_op = binary_op

        return new_node_id

    cdef MastExpID new_if_then_else_exp(
            self,
            MastExpID cond_exp,
            MastExpID then_exp,
            MastExpID else_exp
    ):
        new_node_id = self.help_alloc_node(NodeKind.EXP_IF_THEN_ELSE)
        info_ptr = <IfThenElseExpNodeInfo*> (
            &self.get_info_ptr(new_node_id).exp_if_then_else
        )

        info_ptr.cond_exp = cond_exp
        info_ptr.then_exp = then_exp
        info_ptr.else_exp = else_exp

        return new_node_id

    cdef MastExpID new_get_tuple_field_by_index_exp(
            self,
            MastExpID tuple_exp_id,
            MastExpID index_exp_id
    ):
        new_node_id = self.help_alloc_node(NodeKind.EXP_GET_TUPLE_FIELD_BY_INDEX)
        info_ptr = <GetTupleFieldByIndexExpNodeInfo*> (
            &self.get_info_ptr(new_node_id).exp_get_tuple_field_by_index
        )

        info_ptr.tuple_exp_id = tuple_exp_id
        info_ptr.index_exp_id = index_exp_id

        return new_node_id

    cdef MastExpID new_get_module_field_by_name_with_args_exp(
            self,
            MastExpID module_exp_id,
            DefID name_def_id,
            object arg_node_list: t.List["MastNodeID"]
    ):
        new_node_id = self.help_alloc_node(NodeKind.EXP_GET_MODULE_FIELD_BY_NAME_WITH_ARGS)
        info_ptr = <GetModuleFieldByNameWithArgsExpNodeInfo*> (
            &self.get_info_ptr(new_node_id).exp_get_module_field_by_name_with_args
        )

        arg_count = len(arg_node_list)

        info_ptr.module_exp_id = module_exp_id
        info_ptr.name_def_id = name_def_id
        info_ptr.arg_node_count = arg_count
        info_ptr.arg_node_array = <MastNodeID*> calloc(arg_count, sizeof(MastNodeID))
        for index, arg_node in enumerate(arg_node_list):
            info_ptr.arg_node_array[index] = arg_node_list[index]

        return new_node_id

    cdef MastExpID new_lambda_exp(
            self,
            object arg_name_list: t.List["DefID"],
            body_exp: MastExpID
    ):
        new_node_id = self.help_alloc_node(NodeKind.EXP_LAMBDA)
        info_ptr = <LambdaExpNodeInfo*> (
            &self.get_info_ptr(new_node_id).exp_lambda
        )

        arg_count = len(arg_name_list)

        info_ptr.arg_name_count = arg_count
        info_ptr.arg_name_array = <DefID*> calloc(arg_count, sizeof(DefID))
        for index, arg_name in enumerate(arg_name_list):
            info_ptr.arg_name_array[index] = arg_name
        info_ptr.body_exp = body_exp

        return new_node_id

    cdef MastExpID new_allocate_one_exp(
            self,
            MastExpID stored_val_exp_id,
            AllocationTarget allocation_target,
            bint allocation_is_mut
    ):
        new_node_id = self.help_alloc_node(NodeKind.EXP_ALLOCATE_ONE)
        info_ptr = <AllocateOneExpNodeInfo*> (
            &self.get_info_ptr(new_node_id).exp_allocate_one
        )

        info_ptr.stored_val_exp_id = stored_val_exp_id
        info_ptr.allocation_target = allocation_target
        info_ptr.allocation_is_mut = allocation_is_mut

        return new_node_id

    cdef MastExpID new_allocate_many_exp(
            self,
            MastExpID initializer_stored_val_exp_id,
            MastExpID alloc_count_exp,
            AllocationTarget allocation_target,
            bint allocation_is_mut
    ):
        new_node_id = self.help_alloc_node(NodeKind.EXP_ALLOCATE_MANY)
        info_ptr = <AllocateManyExpNodeInfo*> (
            &self.get_info_ptr(new_node_id).exp_allocate_many
        )

        info_ptr.initializer_stored_val_exp_id = initializer_stored_val_exp_id
        info_ptr.alloc_count_exp = alloc_count_exp
        info_ptr.allocation_target = allocation_target
        info_ptr.allocation_is_mut = allocation_is_mut

        return new_node_id

    cdef MastExpID new_chain_exp(
            self,
            object prefix_elem_id_list: t.List["MastElemID"],
            MastExpID ret_exp_id
    ):
        new_node_id = self.help_alloc_node(NodeKind.EXP_CHAIN)
        info_ptr = <ChainExpNodeInfo*> (
            &self.get_info_ptr(new_node_id).exp_chain
        )

        prefix_elem_count = len(prefix_elem_id_list)

        info_ptr.prefix_elem_count = prefix_elem_count
        info_ptr.prefix_elem_array = <MastElemID*> calloc(prefix_elem_count, sizeof(MastElemID))
        for index, elem_id in enumerate(prefix_elem_id_list):
            info_ptr.prefix_elem_array[index] = elem_id
        info_ptr.ret_exp_id = ret_exp_id

        return new_node_id

    #
    # Elements:
    #

    cdef MastElemID new_bind1v_elem(
            self,
            DefID bound_def_id,
            MastExpID init_exp_id
    ):
        new_node_id = self.help_alloc_node(NodeKind.ELEM_BIND1V)
        info_ptr = <Bind1VElem*> (
            &self.get_info_ptr(new_node_id).elem_bind1v
        )

        info_ptr.bound_def_id = bound_def_id
        info_ptr.init_exp_id = init_exp_id

        return new_node_id

    cdef MastElemID new_do_elem(
            self,
            MastExpID eval_exp_id
    ):
        new_node_id = self.help_alloc_node(NodeKind.ELEM_DO)
        info_ptr = <DoElem*> (
            &self.get_info_ptr(new_node_id).elem_do
        )

        info_ptr.eval_exp_id = eval_exp_id

        return new_node_id
