"""
This module wraps the `extension/` directory.
"""

import typing as t
from collections import namedtuple
import enum

from libc.stddef cimport size_t
from libc.stdint cimport uint32_t

from qcl import ast

#
#
# Cpp Linking:
#
#

# misc. extern NULL IDs:
cdef extern from "extension/arg-list.hh" namespace "monomorphizer::arg_list":
    extern const ArgListID EMPTY_ARG_LIST
cdef extern from "extension/arg-list.hh" namespace "monomorphizer::arg_list":
    ArgListID empty_arg_list_id()


# defs:
cdef extern from "extension/gdef.hh" namespace "monomorphizer::gdef":
    # init/drop:
    void ensure_defs_init();
    void drop_defs(); 

    # declaration:
    GDefID declare_global_def(DefKind kind, char* mv_bound_name)

    # query definition info:
    bint get_def_is_bv(GDefID def_id);
    DefKind get_def_kind(GDefID def_id);
    const char* get_def_name(GDefID def_id);
    size_t get_def_target(GDefID def_id);
    void set_def_target(GDefID def_id, size_t target);

# modules:
cdef extern from "extension/modules.hh" namespace "monomorphizer::modules":
    # constants:
    const MonoModID NULL_MONO_MOD_ID;
    const PolyModID NULL_POLY_MOD_ID;

    # Monomorphic template construction:
    MonoModID new_monomorphic_module(char* mv_template_name, PolyModID opt_parent_template_id);
    # add_field pushes a field and returns its unique index.
    size_t add_mono_module_field(MonoModID template_id, GDefID field_def_id);

    # Polymorphic template construction:
    PolyModID new_polymorphic_module(char* mv_template_name, size_t bv_def_id_count, GDefID* mv_bv_def_id_array);
    # add_field pushes a field and returns the field's unique index.
    size_t add_poly_module_field(PolyModID template_id, GDefID field_def_id);

    # Module fields are accessed by an index that is determined by the order
    # in which symbols are added.
    # By convention, this should be the order in which source nodes are written
    # in source code.
    GDefID get_poly_mod_field_at(PolyModID poly_mod_id, size_t field_index);
    GDefID get_poly_mod_formal_arg_at(PolyModID poly_mod_id, size_t field_index);
    size_t get_mono_mod_field_count(MonoModID mono_mod_id)
    GDefID get_mono_mod_field_at(MonoModID mono_mod_id, size_t field_index);

    # instantiation:
    # turn a PolyModID into a MonoModID using some template arguments.
    MonoModID instantiate_poly_mod(PolyModID poly_mod_id, ArgListID arg_list_id);

    # system info:
    size_t count_all_mono_modules()
    size_t count_registered_lambdas(MonoModID mono_mod_id)
    ExpID get_registered_lambda_at(MonoModID mono_mod_id, size_t index)

# mast:
cdef extern from "extension/mast.hh" namespace "monomorphizer::mast":
    # Constants:
    extern const NodeID NULL_NODE_ID;

    # Init/drop:
    void ensure_mast_init()
    void drop_mast()

    # Type-specs:
    TypeSpecID get_unit_ts();
    TypeSpecID new_gid_ts(GDefID def_id);
    TypeSpecID new_lid_ts(IntStr int_str_id);
    TypeSpecID new_ptr_ts(TypeSpecID ptd_ts, bint contents_is_mut);
    TypeSpecID new_array_ts(TypeSpecID ptd_ts, ExpID count_exp, bint contents_is_mut);
    TypeSpecID new_slice_ts(TypeSpecID ptd_ts, bint contents_is_mut);
    TypeSpecID new_func_sgn_ts(TypeSpecID arg_ts, TypeSpecID ret_ts, SES ret_ses);
    TypeSpecID new_tuple_ts(size_t elem_ts_count, TypeSpecID* mv_elem_ts_array);
    TypeSpecID new_get_mono_module_field_ts(MonoModID mono_mod_id, size_t ts_field_ix);
    TypeSpecID new_get_poly_module_field_ts(
        PolyModID poly_mod_id,
        size_t ts_field_ix,
        size_t actual_arg_count,
        NodeID* actual_arg_array
    );

    # Expressions:
    ExpID get_unit_exp();
    ExpID new_int_exp(size_t mantissa, IntegerSuffix typing_suffix, bint is_neg);
    ExpID new_float_exp(double value, FloatSuffix typing_suffix);
    ExpID new_string_exp(size_t code_point_count, int* code_point_array);
    ExpID new_gid_exp(GDefID def_id);
    ExpID new_lid_exp(IntStr int_str_id);
    ExpID new_func_call_exp(ExpID called_fn, ExpID arg_exp, bint call_is_non_tot);
    ExpID new_tuple_exp(size_t item_count, ExpID* mv_item_array);
    ExpID new_unary_op_exp(UnaryOp unary_op, ExpID arg_exp);
    ExpID new_binary_op_exp(BinaryOp binary_op, ExpID lt_arg_exp, ExpID rt_arg_exp);
    ExpID new_if_then_else_exp(ExpID cond_exp, ExpID then_exp, ExpID else_exp);
    ExpID new_get_tuple_field_by_index_exp(ExpID tuple_exp_id, size_t index);
    ExpID new_lambda_exp(
            uint32_t arg_name_count,
            IntStr* arg_name_array,
            uint32_t ctx_enclosed_name_count,
            IntStr* ctx_enclosed_name_array,
            ExpID body_exp
    );
    ExpID new_allocate_one_exp(ExpID stored_val_exp_id, AllocationTarget allocation_target, bint allocation_is_mut);
    ExpID new_allocate_many_exp(
        ExpID initializer_stored_val_exp_id,
        ExpID alloc_count_exp,
        AllocationTarget allocation_target,
        bint allocation_is_mut
    );
    ExpID new_chain_exp(size_t prefix_elem_id_count, ElemID* prefix_elem_id_array, ExpID ret_exp_id);
    ExpID new_get_mono_module_field_exp(MonoModID mono_mod_id, size_t exp_field_ix);
    ExpID new_get_poly_module_field_exp(
        PolyModID poly_mod_id, size_t exp_field_ix,
        size_t arg_count, NodeID* arg_array
    )
    ExpID new_cast_exp(
        TypeSpecID ts_id,
        ExpID exp_id
    )

    # Element creation methods:
    ElemID new_bind1v_elem(IntStr bound_def_id, ExpID init_exp_id);
    ElemID new_bind1t_elem(IntStr bound_def_id, TypeSpecID init_ts_id);
    ElemID new_do_elem(ExpID eval_exp_id);

    # Shared:
    NodeKind get_node_kind(NodeID node_id)
    NodeInfo* get_info_ptr(NodeID node_id)
    bint is_node_exp_not_ts(NodeID node_id)
    
# intern:
cdef extern from "extension/intern.hh" namespace "monomorphizer::intern":
    IntStr intern_string(cpp_string s, bint is_tid_not_vid)
    cpp_string get_interned_string(IntStr int_str_id)
    bint is_interned_string_tid_not_vid(IntStr int_str_id)

# printing:
cdef extern from "extension/printing.hh" namespace "monomorphizer::printing":
    void print_poly_mod(PolyModID poly_mod_id)
    void print_mono_mod(MonoModID mono_mod_id)

# mtype:
cdef extern from "extension/mtype.hh" namespace "monomorphizer::mtype":
    void ensure_mtype_init()

    TID get_unit_tid();
    TID get_u1_tid();
    TID get_u8_tid();
    TID get_u16_tid();
    TID get_u32_tid();
    TID get_u64_tid();
    TID get_s8_tid();
    TID get_s16_tid();
    TID get_s32_tid();
    TID get_s64_tid();
    TID get_f32_tid();
    TID get_f64_tid();
    TID get_string_tid();
    TID get_tuple_tid(ArgListID arg_list_id);
    TID get_ptr_tid(TID ptd_tid, bint contents_is_mut);
    TID get_array_tid(TID ptd_tid, VID count_val_id, bint contents_is_mut);
    TID get_slice_tid(TID ptd_tid, bint contents_is_mut);
    TID get_function_tid(TID arg_tid, TID ret_tid, SES ses);

# mval:
cdef extern from "extension/mval.hh" namespace "monomorphizer::mval":
    ValueKind value_kind(VID value_id)
    ValueInfo value_info(VID value_id)
    size_t get_seq_count(size_t seq_info_index)
    bint get_seq_elem1_compatibility(size_t seq_info_index, size_t index, VID* out_vid)
    bint get_seq_elem2_compatibility(VID tuple_val_id, size_t index, VID* out_vid)
    FuncInfo* get_func_info(size_t func_info_index)
    VCellID get_ptr_vcell(VID val_id)
    VCellID get_array_vcell(VID val_id, size_t index)
    VCellID get_slice_vcell(VID val_id, size_t index)
    bint equals(VID v1, VID v2)


#
#
# Interface
#
#

# init/drop:
cdef:
    void w_ensure_init():
        ensure_mast_init()
        ensure_defs_init()
        ensure_mtype_init()

    void w_drop():
        drop_mast()
        drop_defs()

# mast: expressions:
cdef:
    ExpID w_get_unit_exp():
        return get_unit_exp()
    ExpID w_new_int_exp(size_t mantissa, IntegerSuffix int_suffix, bint is_neg):
        return new_int_exp(mantissa, int_suffix, is_neg)
    ExpID w_new_float_exp(double value, FloatSuffix float_suffix):
        return new_float_exp(value, float_suffix)
    ExpID w_new_string_exp(size_t code_point_count, int* code_point_array):
        return new_string_exp(code_point_count, code_point_array)
    ExpID w_new_lid_exp(IntStr int_str_id):
        return new_lid_exp(int_str_id)
    ExpID w_new_gid_exp(GDefID def_id):
        return new_gid_exp(def_id)
    ExpID w_new_func_call_exp(ExpID called_fn, ExpID arg_exp, bint call_is_non_tot):
        return new_func_call_exp(called_fn, arg_exp, call_is_non_tot)
    ExpID w_new_tuple_exp(size_t item_count, ExpID* mv_item_array):
        return new_tuple_exp(item_count, mv_item_array)
    ExpID w_new_unary_op_exp(UnaryOp unary_op, ExpID arg_exp):
        return new_unary_op_exp(unary_op, arg_exp)
    ExpID w_new_binary_op_exp(BinaryOp binary_op, ExpID lt_arg_exp, ExpID rt_arg_exp):
        return new_binary_op_exp(binary_op, lt_arg_exp, rt_arg_exp)
    ExpID w_new_if_then_else_exp(ExpID cond_exp, ExpID then_exp, ExpID else_exp):
        return new_if_then_else_exp(cond_exp, then_exp, else_exp)
    ExpID w_new_get_tuple_field_by_index_exp(ExpID tuple_exp_id, size_t index):
        return new_get_tuple_field_by_index_exp(tuple_exp_id, index)
    ExpID w_new_lambda_exp(
            uint32_t arg_name_count,
            IntStr* arg_name_array,
            uint32_t ctx_enclosed_name_count,
            IntStr* ctx_enclosed_name_array,
            ExpID body_exp
    ):
        return new_lambda_exp(
            arg_name_count, arg_name_array,
            ctx_enclosed_name_count, ctx_enclosed_name_array,
            body_exp
        )
    ExpID w_new_allocate_one_exp(ExpID stored_val_exp_id, AllocationTarget allocation_target, bint allocation_is_mut):
        return new_allocate_one_exp(stored_val_exp_id, allocation_target, allocation_is_mut)
    ExpID w_new_allocate_many_exp(
        ExpID initializer_stored_val_exp_id,
        ExpID alloc_count_exp,
        AllocationTarget allocation_target,
        bint allocation_is_mut
    ):
        return new_allocate_many_exp(
            initializer_stored_val_exp_id,
            alloc_count_exp,
            allocation_target,
            allocation_is_mut
        )
    ExpID w_new_chain_exp(size_t prefix_elem_id_count, ElemID* mv_prefix_elem_id_array, ExpID ret_exp_id):
        return new_chain_exp(prefix_elem_id_count, mv_prefix_elem_id_array, ret_exp_id)
    ExpID w_new_get_mono_module_field_exp(MonoModID mono_mod_id, size_t exp_field_ix):
        return new_get_mono_module_field_exp(mono_mod_id, exp_field_ix)
    ExpID w_new_get_poly_module_field_exp(
        PolyModID poly_mod_id, size_t exp_field_ix,
        size_t arg_count, NodeID* arg_array
    ):
        return new_get_poly_module_field_exp(
            poly_mod_id, exp_field_ix,
            arg_count, arg_array
        )
    ExpID w_new_cast_exp(TypeSpecID ts_id, ExpID exp_id):
        return new_cast_exp(ts_id, exp_id)

# mast: type-specs:
cdef:
    TypeSpecID w_get_unit_ts():
        return get_unit_ts()
    TypeSpecID w_new_gid_ts(GDefID def_id):
        return new_gid_ts(def_id)
    TypeSpecID w_new_lid_ts(IntStr int_str_id):
        return new_lid_ts(int_str_id)
    TypeSpecID w_new_ptr_ts(TypeSpecID ptd_ts, bint contents_is_mut):
        return new_ptr_ts(ptd_ts, contents_is_mut)
    TypeSpecID w_new_array_ts(TypeSpecID ptd_ts, ExpID count_exp, bint contents_is_mut):
        return new_array_ts(ptd_ts, count_exp, contents_is_mut)
    TypeSpecID w_new_slice_ts(TypeSpecID ptd_ts, bint contents_is_mut):
        return new_slice_ts(ptd_ts, contents_is_mut)
    TypeSpecID w_new_func_sgn_ts(TypeSpecID arg_ts, TypeSpecID ret_ts, SES ret_ses):
        return new_func_sgn_ts(arg_ts, ret_ts, ret_ses)
    TypeSpecID w_new_tuple_ts(size_t elem_ts_count, TypeSpecID* mv_elem_ts_array):
        return new_tuple_ts(elem_ts_count, mv_elem_ts_array)
    TypeSpecID w_new_get_mono_module_field_ts(MonoModID mono_mod_id, size_t ts_field_ix):
        return new_get_mono_module_field_ts(mono_mod_id, ts_field_ix)
    TypeSpecID w_new_get_poly_module_field_ts(
        PolyModID poly_mod_id,
        size_t ts_field_ix,
        size_t actual_arg_count,
        NodeID* actual_arg_array
    ):
        return new_get_poly_module_field_ts(
            poly_mod_id,
            ts_field_ix,
            actual_arg_count,
            actual_arg_array
        )

# mast: elem:
cdef:
    ElemID w_new_bind1v_elem(GDefID bound_def_id, ExpID init_exp_id):
        return new_bind1v_elem(bound_def_id, init_exp_id)
        
    ElemID w_new_bind1t_elem(GDefID bound_def_id, TypeSpecID init_ts_id):
        return new_bind1t_elem(bound_def_id, init_ts_id)

    ElemID w_new_do_elem(ExpID eval_exp_id):
        return new_do_elem(eval_exp_id)

# mast: common:
cdef:
    NodeKind w_get_node_kind(NodeID node_id):
        return get_node_kind(node_id)
    
    NodeInfo* w_get_info_ptr(NodeID node_id):
        return get_info_ptr(node_id)

    bint w_is_node_exp_not_ts(NodeID node_id):
        return is_node_exp_not_ts(node_id)

# defs: global and unscoped
cdef:
    # constructor:
    GDefID w_declare_global_def(DefKind kind, char* mv_bound_name):
        return declare_global_def(kind, mv_bound_name)

    # functions to query definition info:
    bint w_get_def_is_bv(GDefID def_id):
        return get_def_is_bv(def_id)
    DefKind w_get_def_kind(GDefID def_id):
        return get_def_kind(def_id)
    const char* w_get_def_name(GDefID def_id):
        return get_def_name(def_id)
    size_t w_get_def_target(GDefID def_id):
        return get_def_target(def_id)
    void w_set_def_target(GDefID def_id, size_t target):
        set_def_target(def_id, target)

# modules:
cdef:
    # Polymorphic template construction:
    PolyModID w_new_polymorphic_module(char* mv_template_name, size_t bv_def_id_count, GDefID* mv_bv_def_id_array):
        return new_polymorphic_module(mv_template_name, bv_def_id_count, mv_bv_def_id_array)
    # add_field pushes a field and returns the field's unique index.
    size_t w_add_poly_module_field(PolyModID template_id, GDefID field_def_id):
        return add_poly_module_field(template_id, field_def_id)

    # Module fields are accessed by an index that is determined by the order
    # in which symbols are added.
    # By convention, this should be the order in which source nodes are written
    # in source code.
    GDefID w_get_poly_mod_field_at(PolyModID poly_mod_id, size_t field_index):
        return get_poly_mod_field_at(poly_mod_id, field_index)
    GDefID w_get_poly_mod_formal_arg_at(PolyModID poly_mod_id, size_t field_index):
        return get_poly_mod_formal_arg_at(poly_mod_id, field_index)
    size_t w_get_mono_mod_field_count(MonoModID mono_mod_id):
        return get_mono_mod_field_count(mono_mod_id)
    GDefID w_get_mono_mod_field_at(MonoModID mono_mod_id, size_t field_index):
        return get_mono_mod_field_at(mono_mod_id, field_index)

    # instantiation:
    # turn a PolyModID into a MonoModID using some template arguments.
    MonoModID w_instantiate_poly_mod(PolyModID poly_mod_id, ArgListID arg_list_id):
        return instantiate_poly_mod(poly_mod_id, arg_list_id)

    # mono module count:
    size_t w_count_all_mono_modules():
        return count_all_mono_modules()

    size_t w_count_registered_lambdas(MonoModID mono_mod_id):
        return count_registered_lambdas(mono_mod_id)
    
    ExpID w_get_registered_lambda_at(MonoModID mono_mod_id, size_t index):
        return get_registered_lambda_at(mono_mod_id, index)


# interning:
cdef:
    IntStr w_intern_string_1(cpp_string s, bint is_id_tid_not_vid):
        return intern_string(s, is_id_tid_not_vid)
    IntStr w_intern_string_2(const char* nt_bytes, bint is_id_tid_not_vid):
        s = cpp_string(nt_bytes)
        return intern_string(s, is_id_tid_not_vid)

# printing:
cdef:
    void w_print_poly_mod(PolyModID poly_mod_id):
        print_poly_mod(poly_mod_id)
    void w_print_mono_mod(MonoModID mono_mod_id):
        print_mono_mod(mono_mod_id)

# arg list:
cdef:
    ArgListID w_empty_arg_list_id():
        return empty_arg_list_id()


# MType:
cdef:
    TID w_get_unit_tid():
        return get_unit_tid()
    TID w_get_u1_tid():
        return get_u1_tid()
    TID w_get_u8_tid():
        return get_u8_tid()
    TID w_get_u16_tid():
        return get_u16_tid()
    TID w_get_u32_tid():
        return get_u32_tid()
    TID w_get_u64_tid():
        return get_u64_tid()
    TID w_get_s8_tid():
        return get_s8_tid()
    TID w_get_s16_tid():
        return get_s16_tid()
    TID w_get_s32_tid():
        return get_s32_tid()
    TID w_get_s64_tid():
        return get_s64_tid()
    TID w_get_f32_tid():
        return get_f32_tid()
    TID w_get_f64_tid():
        return get_f64_tid()
    TID w_get_string_tid():
        return get_string_tid()
    TID w_get_tuple_tid(ArgListID arg_list_id):
        return get_tuple_tid(arg_list_id)
    TID w_get_ptr_tid(TID ptd_tid, bint contents_is_mut):
        return get_ptr_tid(ptd_tid, contents_is_mut)
    TID w_get_array_tid(TID ptd_tid, VID count_val_id, bint contents_is_mut):
        return get_array_tid(ptd_tid, count_val_id, contents_is_mut)
    TID w_get_slice_tid(TID ptd_tid, bint contents_is_mut):
        return get_slice_tid(ptd_tid, contents_is_mut)
    TID w_get_function_tid(TID arg_tid, TID ret_tid, SES ses):
        return get_function_tid(arg_tid, ret_tid, ses)

# MVal:
cdef:
    ValueKind w_value_kind(VID value_id):
        return value_kind(value_id)
    ValueInfo w_value_info(VID value_id):
        return value_info(value_id)
    size_t w_get_seq_count(VID value_id):
        return get_seq_count(value_id)
    bint w_get_seq_elem1(size_t seq_info_index, size_t index, VID* out_vid):
        return get_seq_elem1_compatibility(seq_info_index, index, out_vid)
    bint w_get_seq_elem2(size_t tuple_val_id, size_t index, VID* out_vid):
        return get_seq_elem2_compatibility(tuple_val_id, index, out_vid)
    FuncInfo* w_get_func_info(size_t func_info_index):
        return get_func_info(func_info_index)
    VCellID w_get_ptr_vcell(VID val_id):
        return get_ptr_vcell(val_id)
    VCellID w_get_array_vcell(VID val_id, size_t index):
        return get_array_vcell(val_id, index)
    VCellID w_get_slice_vcell(VID val_id, size_t index):
        return get_slice_vcell(val_id, index)
    bint w_equals(VID v1, VID v2):
        return equals(v1, v2)


#
#
# Python wrappers (for export) (once system is static)
#
#

# `mast` wrappers for Python:
# NOTE: shared enums are substituted for their Python variants from `ast.node` or string-coded tuples
class PyMAST:
    NodeID = int
    ExpID = NodeID
    TypeSpecID = NodeID
    ElemID = NodeID
    class PyNodeKind(enum.Enum):
        TS_Unit = TS_UNIT
        TS_GId = TS_GID
        TS_LId = TS_LID
        TS_Ptr = TS_PTR
        TS_Array = TS_ARRAY
        TS_Slice = TS_SLICE
        TS_FuncSgn = TS_FUNC_SGN
        TS_Tuple = TS_TUPLE
        TS_GetPolyModuleField = TS_GET_POLY_MODULE_FIELD
        TS_GetMonoModuleField = TS_GET_MONO_MODULE_FIELD
        EXP_Unit = EXP_UNIT
        EXP_Int = EXP_INT
        EXP_Float = EXP_FLOAT
        EXP_String = EXP_STRING
        EXP_LId = EXP_LID
        EXP_GId = EXP_GID
        EXP_Tuple = EXP_TUPLE
        EXP_FuncCall = EXP_FUNC_CALL
        EXP_UnaryOp = EXP_UNARY_OP
        EXP_BinaryOp = EXP_BINARY_OP
        EXP_IfThenElse = EXP_IF_THEN_ELSE
        EXP_GetTupleField = EXP_GET_TUPLE_FIELD
        EXP_Lambda = EXP_LAMBDA
        EXP_AllocOne = EXP_ALLOCATE_ONE
        EXP_AllocMany = EXP_ALLOCATE_MANY
        EXP_Chain = EXP_CHAIN
        EXP_GetPolyModuleField = EXP_GET_POLY_MODULE_FIELD
        EXP_GetMonoModuleField = EXP_GET_MONO_MODULE_FIELD
        EXP_Cast = EXP_CAST
        ELEM_Bind1V = ELEM_BIND1V
        ELEM_Bind1T = ELEM_BIND1T
        ELEM_Do = ELEM_DO
    PyGlobalIdTypeSpecNodeInfo = namedtuple(
        "GlobalIdTypeSpecNodeInfo",
        ["def_id"]
    )
    PyLocalIdTypeSpecNodeInfo = namedtuple(
        "LocalIdTypeSpecNodeInfo",
        ["int_str_id"]
    )
    PyPtrTypeSpecNodeInfo = namedtuple(
        "PtrTypeSpecNodeInfo",
        ["ptd_ts", "contents_is_mut"]
    )
    PyArrayTypeSpecNodeInfo = namedtuple(
        "ArrayTypeSpecNodeInfo",
        ["ptd_ts", "count_exp", "contents_is_mut"]
    )
    PySliceTypeSpecNodeInfo = namedtuple(
        "SliceTypeSpecNodeInfo",
        ["ptd_ts", "contents_is_mut"]
    )
    PyFuncSgnTypeSpecNodeInfo = namedtuple(
        "FuncSgnTypeSpecNodeInfo",
        ["arg_ts", "ret_ts", "ret_ses"]
    )
    PyTupleTypeSpecNodeInfo = namedtuple(
        "TupleTypeSpecNodeInfo",
        ["elem_ts_id_list"]
    )
    PyGetPolyModuleFieldTypeSpecNodeInfo = namedtuple(
        "GetPolyModuleFieldTypeSpecNodeInfo",
        ["actual_arg_id_list", "template_id", "ts_field_index"]
    )
    PyGetMonoModuleFieldTypeSpecNodeInfo = namedtuple(
        "GetMonoModuleFieldTypeSpecNodeInfo",
        ["template_id", "ts_field_index"]
    )
    PyIntExpNodeInfo = namedtuple(
        "IntExpNodeInfo",
        ["mantissa", "suffix", "is_neg"]
    )
    PyFloatExpNodeInfo = namedtuple(
        "FloatExpNodeInfo",
        ["value", "suffix"]
    )
    PyStringExpNodeInfo = namedtuple(
        "StringExpNodeInfo",
        ["code_point_list"]
    )
    PyGlobalIdExpNodeInfo = namedtuple(
        "GlobalIdExpNodeInfo",
        ["def_id"]
    )
    PyLocalIdExpNodeInfo = namedtuple(
        "LocalIdExpNodeInfo",
        ["int_str_id"]
    )
    PyTupleExpNodeInfo = namedtuple(
        "TupleExpNodeInfo",
        ["item_list"]
    )
    PyFuncCallExpNodeInfo = namedtuple(
        "FuncCallExpNodeInfo",
        ["called_fn", "arg_exp_id", "call_is_non_tot"]
    )
    PyUnaryOpExpNodeInfo = namedtuple(
        "UnaryOpExpNodeInfo",
        ["arg_exp", "unary_op"]
    )
    PyBinaryOpExpNodeInfo = namedtuple(
        "BinaryOpExpNodeInfo",
        ["lt_arg_exp", "rt_arg_exp", "binary_op"]
    )
    PyIfThenElseExp = namedtuple(
        "IfThenElseExp",
        ["cond_exp", "then_exp", "else_exp"]
    )
    PyGetTupleFieldExpNodeInfo = namedtuple(
        "GetTupleFieldExpNodeInfo",
        ["tuple_exp_id", "index"]
    )
    PyLambdaExpNodeInfo = namedtuple(
        "LambdaExpNodeInfo",
        ["arg_name_list", "ctx_enclosed_name_list", "body_exp"]
    )
    PyAllocateOneExpNodeInfo = namedtuple(
        "AllocateOneExpNodeInfo",
        ["stored_val_exp_id", "allocation_target", "allocation_is_mut"]
    )
    PyAllocateManyExpNodeInfo = namedtuple(
        "AllocateManyExpNodeInfo",
        ["initializer_stored_val_exp_id", "alloc_count_exp", "allocation_target"]
    )
    PyChainExpNodeInfo = namedtuple(
        "ChainExpNodeInfo",
        ["prefix_elem_list", "ret_exp_id"]
    )
    PyGetPolyModuleFieldExpNodeInfo = namedtuple(
        "GetPolyModuleFieldExpNodeInfo",
        ["arg_list", "temmplate_id", "field_index"]
    )
    PyGetMonoModuleFieldExpNodeInfo = namedtuple(
        "GetMonoModuleFieldExpNodeInfo",
        ["template_id", "field_index"]
    )
    PyCastExpNodeInfo = namedtuple(
        "CastExpNodeInfo",
        ["ts_id", "exp_id"]
    )
    PyBind1VElemNodeInfo = namedtuple(
        "Bind1VElemNodeInfo",
        ["bound_id", "init_exp_id"]
    )
    PyBind1TElemNodeInfo = namedtuple(
        "Bind1TElemNodeInfo",
        ["bound_id", "init_ts_id"]
    )
    PyDoElemNodeInfo = namedtuple(
        "DoElemNodeInfo",
        ["eval_exp_id"]
    )

    get_unit_ts = py_mast_get_unit_ts
    get_unit_exp = py_mast_get_unit_exp
    get_node_kind = py_mast_get_node_kind
    get_info = py_mast_get_info

cpdef object py_mast_get_unit_ts():
    # TODO: cache this
    return w_get_unit_ts()

cpdef object py_mast_get_unit_exp():
    # TODO: cache this
    return w_get_unit_exp()

cpdef object py_mast_get_node_kind(node_id: "PyMAST.NodeID"):
    # TODO: cache this
    return {
        TS_UNIT: PyMAST.PyNodeKind.TS_Unit,
        TS_GID: PyMAST.PyNodeKind.TS_GId,
        TS_LID: PyMAST.PyNodeKind.TS_LId,
        TS_PTR: PyMAST.PyNodeKind.TS_Ptr,
        TS_ARRAY: PyMAST.PyNodeKind.TS_Array,
        TS_SLICE: PyMAST.PyNodeKind.TS_Slice,
        TS_FUNC_SGN: PyMAST.PyNodeKind.TS_FuncSgn,
        TS_GET_POLY_MODULE_FIELD: PyMAST.PyNodeKind.TS_GetPolyModuleField,
        TS_GET_MONO_MODULE_FIELD: PyMAST.PyNodeKind.TS_GetMonoModuleField,
        EXP_UNIT: PyMAST.PyNodeKind.EXP_Unit,
        EXP_INT: PyMAST.PyNodeKind.EXP_Int,
        EXP_FLOAT: PyMAST.PyNodeKind.EXP_Float,
        EXP_STRING: PyMAST.PyNodeKind.EXP_String,
        EXP_LID: PyMAST.PyNodeKind.EXP_LId,
        EXP_GID: PyMAST.PyNodeKind.EXP_GId,
        EXP_TUPLE: PyMAST.PyNodeKind.EXP_Tuple,
        EXP_FUNC_CALL: PyMAST.PyNodeKind.EXP_FuncCall,
        EXP_UNARY_OP: PyMAST.PyNodeKind.EXP_UnaryOp,
        EXP_BINARY_OP: PyMAST.PyNodeKind.EXP_BinaryOp,
        EXP_IF_THEN_ELSE: PyMAST.PyNodeKind.EXP_IfThenElse,
        EXP_GET_TUPLE_FIELD: PyMAST.PyNodeKind.EXP_GetTupleField,
        EXP_LAMBDA: PyMAST.PyNodeKind.EXP_Lambda,
        EXP_ALLOCATE_ONE: PyMAST.PyNodeKind.EXP_AllocOne,
        EXP_ALLOCATE_MANY: PyMAST.PyNodeKind.EXP_AllocMany,
        EXP_CHAIN: PyMAST.PyNodeKind.EXP_Chain,
        EXP_GET_POLY_MODULE_FIELD: PyMAST.PyNodeKind.EXP_GetPolyModuleField,
        EXP_GET_MONO_MODULE_FIELD: PyMAST.PyNodeKind.EXP_GetMonoModuleField,
        EXP_CAST: PyMAST.PyNodeKind.EXP_Cast,
        ELEM_BIND1V: PyMAST.PyNodeKind.ELEM_Bind1V,
        ELEM_BIND1T: PyMAST.PyNodeKind.ELEM_Bind1T,
        ELEM_DO: PyMAST.PyNodeKind.ELEM_Do
    }[w_get_node_kind(node_id)]

cpdef object py_mast_get_info(node_id: "PyMAST.NodeID"):
    # TODO: cache the result of this
    node_kind = get_node_kind(node_id)
    if node_kind in (PyMAST.PyNodeKind.TS_Unit, PyMAST.PyNodeKind.EXP_Unit):
        return ()
    node_info_ptr = w_get_info_ptr(node_id)
    if node_kind == PyMAST.PyNodeKind.TS_GId:
        return PyMAST.PyGlobalIdTypeSpecNodeInfo(
            def_id=node_info_ptr.ts_gid.def_id
        )
    if node_kind == PyMAST.PyNodeKind.TS_LId:
        return PyMAST.PyLocalIdTypeSpecNodeInfo(
            int_str_id=node_info_ptr.ts_lid.int_str_id
        )
    if node_kind == PyMAST.PyNodeKind.TS_Ptr:
        return PyMAST.PyPtrTypeSpecNodeInfo(
            ptd_ts=node_info_ptr.ts_ptr.ptd_ts, 
            contents_is_mut=node_info_ptr.ts_ptr.contents_is_mut
        )
    if node_kind == PyMAST.PyNodeKind.TS_Array:
        return PyMAST.PyArrayTypeSpecNodeInfo(
            ptd_ts=node_info_ptr.ts_array.ptd_ts,
            count_exp=node_info_ptr.ts_array.count_exp,
            contents_is_mut=node_info_ptr.ts_array.contents_is_mut
        )
    if node_kind == PyMAST.PyNodeKind.TS_Slice:
        return PyMAST.PySliceTypeSpecNodeInfo(
            ptd_ts=node_info_ptr.ts_array.ptd_ts,
            contents_is_mut=node_info_ptr.ts_array.contents_is_mut
        )
    if node_kind == PyMAST.PyNodeKind.TS_FuncSgn:
        return PyMAST.PyFuncSgnTypeSpecNodeInfo(
            arg_ts=node_info_ptr.ts_func_sgn.arg_ts,
            ret_ts=node_info_ptr.ts_func_sgn.ret_ts,
            ret_ses={
                SES_ML: type.side_effects.SES.ML,
                SES_ST: type.side_effects.SES.ST,
                SES_EXN: type.side_effects.SES.Exn,
                SES_DV: type.side_effects.SES.Dv,
                SES_TOT: type.side_effects.SES.Tot
            }[node_info_ptr.ts_func_sgn.ret_ses]
        )
    if node_kind == PyMAST.PyNodeKind.TS_Tuple:
        item_id_array = node_info_ptr.ts_tuple.elem_ts_array
        item_id_count = node_info_ptr.ts_tuple.elem_ts_count
        return PyMAST.PyTupleTypeSpecNodeInfo(
            elem_ts_id_list=[
                item_id_array[i]
                for i in range(item_id_count)
            ]
        )
    if node_kind == PyMAST.PyNodeKind.TS_GetPolyModuleField:
        actual_arg_id_array = node_info_ptr.ts_get_poly_module_field.actual_arg_array
        actual_arg_id_count = node_info_ptr.ts_get_poly_module_field.actual_arg_count
        return PyMAST.PyGetPolyModuleFieldTypeSpecNodeInfo(
            actual_arg_id_list=[
                actual_arg_id_array[i]
                for i in range(actual_arg_id_count)
            ],
            template_id=node_info_ptr.ts_get_poly_module_field.template_id,
            ts_field_index=node_info_ptr.ts_get_poly_module_field.ts_field_index
        )
    if node_kind == PyMAST.PyNodeKind.TS_GetMonoModuleField:
        return PyMAST.PyGetMonoModuleFieldTypeSpecNodeInfo(
            template_id=node_info_ptr.ts_get_mono_module_field.template_id,
            ts_field_index=node_info_ptr.ts_get_mono_module_field.ts_field_index
        )
    if node_kind == PyMAST.PyNodeKind.EXP_Int:
        return PyMAST.PyIntExpNodeInfo(
            mantissa=node_info_ptr.exp_int.mantissa,
            suffix={
                IS_U1: ("u", 1),
                IS_U8: ("u", 8),
                IS_U16: ("u", 16),
                IS_U32: ("u", 32),
                IS_U64: ("u", 64),
                IS_S8: ("s", 8),
                IS_S16: ("s", 16),
                IS_S32: ("s", 32),
                IS_S64: ("s", 64),
            }[node_info_ptr.exp_int.suffix],
            is_neg=node_info_ptr.exp_int.is_neg
        )
    if node_kind == PyMAST.PyNodeKind.EXP_Float:
        return PyMAST.PyFloatExpNodeInfo(
            value=node_info_ptr.exp_float.value,
            suffix={
                FS_F32: ("f", 32),
                FS_F64: ("f", 64)
            }[node_info_ptr.exp_float.suffix]
        )
    if node_kind == PyMAST.PyNodeKind.EXP_String:
        code_point_array = node_info_ptr.exp_str.code_point_array
        code_point_count = node_info_ptr.exp_str.code_point_count
        return PyMAST.PyStringExpNodeInfo(
            code_point_list=[
                int(code_point_array[i])
                for i in range(code_point_count)
            ]
        )
    if node_kind == PyMAST.PyNodeKind.EXP_GId:
        return PyMAST.PyGlobalIdExpNodeInfo(
            def_id=node_info_ptr.exp_gid.def_id
        )
    if node_kind == PyMAST.PyNodeKind.EXP_LId:
        return PyMAST.PyLocalIdExpNodeInfo(
            int_str_id=node_info_ptr.exp_lid.int_str_id
        )
    if node_kind == PyMAST.PyNodeKind.EXP_Tuple:
        item_array = node_info_ptr.exp_tuple.item_array
        item_count = node_info_ptr.exp_tuple.item_count
        return PyMAST.PyTupleExpNodeInfo(
            item_list=[
                item_array[i]
                for i in range(item_count)
            ]
        )
    if node_kind == PyMAST.PyNodeKind.EXP_UnaryOp:
        return PyMAST.PyUnaryOpExpNodeInfo(
            arg_exp=node_info_ptr.exp_unary.arg_exp,
            unary_op={
                UNARY_DE_REF: ast.node.UnaryOp.DeRef,
                UNARY_LOGICAL_NOT: ast.node.UnaryOp.LogicalNot,
                UNARY_POS: ast.node.UnaryOp.Pos,
                UNARY_NEG: ast.node.UnaryOp.Neg
            }[node_info_ptr.exp_unary.unary_op]
        )
    if node_kind == PyMAST.PyNodeKind.EXP_BinaryOp:
        return PyMAST.PyBinaryOpExpNodeInfo(
            lt_arg_exp=node_info_ptr.exp_binary.lt_arg_exp,
            rt_arg_exp=node_info_ptr.exp_binary.rt_arg_exp,
            binary_op={
                BINARY_MUL: ast.node.BinaryOp.Mul,
                BINARY_DIV: ast.node.BinaryOp.Div,
                BINARY_REM: ast.node.BinaryOp.Rem,
                BINARY_ADD: ast.node.BinaryOp.Add,
                BINARY_SUB: ast.node.BinaryOp.Sub,
                BINARY_LT: ast.node.BinaryOp.LT,
                BINARY_GT: ast.node.BinaryOp.GT,
                BINARY_LE: ast.node.BinaryOp.LE,
                BINARY_GE: ast.node.BinaryOp.GE,
                BINARY_EQ: ast.node.BinaryOp.Eq,
                BINARY_NE: ast.node.BinaryOp.NE,
                BINARY_LOGICAL_AND: ast.node.BinaryOp.LogicalAnd,
                BINARY_LOGICAL_OR: ast.node.BinaryOp.LogicalOr
            }[node_info_ptr.exp_binary.binary_op]
        )
    if node_kind == PyMAST.PyNodeKind.EXP_IfThenElse:
        return PyMAST.PyIfThenElseExpNodeInfo(
            cond_exp=node_info_ptr.exp_if_then_else.cond_exp,
            then_exp=node_info_ptr.exp_if_then_else.then_exp,
            else_exp=node_info_ptr.exp_if_then_else.else_exp
        )
    if node_kind == PyMAST.PyNodeKind.EXP_GetTupleField:
        return PyMAST.PyGetTupleFieldExpNodeInfo(
            tuple_exp_id=node_info_ptr.exp_get_tuple_field.tuple_exp_id,
            index=node_info_ptr.exp_get_tuple_field.index
        )
    if node_kind == PyMAST.PyNodeKind.EXP_Lambda:
        arg_name_count = node_info_ptr.exp_lambda.arg_name_count
        ctx_enclosed_name_count = node_info_ptr.exp_lambda.ctx_enclosed_name_count
        arg_name_array = node_info_ptr.exp_lambda.arg_name_array
        ctx_enclosed_name_array = node_info_ptr.exp_lambda.ctx_enclosed_name_array
        body_exp_id = node_info_ptr.exp_lambda.body_exp

        return PyMAST.PyLambdaExpNodeInfo(
            arg_name_list=[
                arg_name_array[i]
                for i in range(arg_name_count)
            ],
            ctx_enclosed_name_list=[
                ctx_enclosed_name_array[i]
                for i in range(arg_name_count)
            ],
            body_exp=body_exp_id
        )
    if node_kind == PyMAST.PyNodeKind.EXP_AllocOne:
        return PyMAST.PyAllocateOneExpNodeInfo(
            stored_val_exp_id=node_info_ptr.exp_allocate_one.stored_val_exp_id,
            allocation_target={
                ALLOCATION_TARGET_HEAP: ast.node.Allocator.Heap,
                ALLOCATION_TARGET_STACK: ast.node.Allocator.Stack
            }[node_info_ptr.exp_allocate_one.allocation_target],
            allocation_is_mut=node_info_ptr.exp_allocate_one.allocation_is_mut
        )
    if node_kind == PyMAST.PyNodeKind.EXP_AllocMany:
        return PyMAST.PyAllocateManyExpNodeInfo(
            initializer_stored_val_exp_id=node_info_ptr.exp_allocate_many.initializer_stored_val_exp_id,
            alloc_count_exp=node_info_ptr.exp_allocate_many.alloc_count_exp,
            allocation_target={
                ALLOCATION_TARGET_HEAP: ast.node.Allocator.Heap,
                ALLOCATION_TARGET_STACK: ast.node.Allocator.Stack
            }[node_info_ptr.exp_allocate_many.allocation_target],
            allocation_is_mut=node_info_ptr.exp_allocate_many.allocation_is_mut
        )
    if node_kind == PyMAST.PyNodeKind.EXP_Chain:
        prefix_elem_array = node_info_ptr.exp_chain.prefix_elem_array
        prefix_elem_count = node_info_ptr.exp_chain.prefix_elem_count
        return PyMAST.PyChainExpNodeInfo(
            prefix_elem_list=[
                prefix_elem_array[i]
                for i in range(prefix_elem_count)
            ],
            ret_exp_id=node_info_ptr.exp_chain.ret_exp_id
        )
    if node_kind == PyMAST.PyNodeKind.EXP_GetPolyModuleField:
        arg_count = node_info_ptr.exp_get_poly_module_field.arg_count
        arg_array = node_info_ptr.exp_get_poly_module_field.arg_array
        return PyMAST.PyGetPolyModuleFieldExpNodeInfo(
            arg_list=[
                arg_array[i]
                for i in range(arg_count)
            ],
            template_id=node_info_ptr.exp_get_poly_module_field.template_id,
            field_index=node_info_ptr.exp_get_poly_module_field.field_index
        )
    if node_kind == PyMAST.PyNodeKind.EXP_GetMonoModuleField:
        return PyMAST.PyGetMonoModuleFieldExpNodeInfo(
            template_id=node_info_ptr.exp_get_mono_module_field.template_id,
            field_index=node_info_ptr.exp_get_mono_module_field.field_index
        )
    if node_kind == PyMAST.PyNodeKind.EXP_Cast:
        return PyMAST.PyCastExpNodeInfo(
            ts_id=node_info_ptr.exp_cast.ts_id,
            exp_id=node_info_ptr.exp_cast.exp_id
        )
    if node_kind == PyMAST.PyNodeKind.ELEM_Bind1V:
        return PyMAST.PyBind1VElemNodeInfo(
            bound_id=node_info_ptr.elem_bind1v.bound_id,
            init_exp_id=node_info_ptr.elem_bind1v.init_exp_id
        )
    if node_kind == PyMAST.PyNodeKind.ELEM_Bind1T:
        return PyMAST.PyBind1TElemNodeInfo(
            bound_id=node_info_ptr.elem_bind1t.bound_id,
            init_ts_id=node_info_ptr.elem_bind1t.init_ts_id
        )
    if node_kind == PyMAST.PyNodeKind.ELEM_Do:
        return PyMAST.PyDoElemNodeInfo(
            eval_exp_id=node_info_ptr.elem_do.eval_exp_id
        )
    raise NotImplementedError(f"`mast_get_info` for node_kind {node_kind}")


# TODO: write Python wrapper for `mval`