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
    size_t arg_list_head_compatibility(ArgListID arg_list_id)
    ArgListID arg_list_tail_compatibility(ArgListID arg_list_id)


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
    MonoModID new_monomorphic_module(
        char* mv_template_name, 
        PolyModID opt_parent_template_id, 
        size_t source_node_index
    )
    # add_field pushes a field and returns its unique index.
    size_t add_mono_module_field(MonoModID template_id, GDefID field_def_id);

    # Polymorphic template construction:
    PolyModID new_polymorphic_module(
        char* mv_template_name, 
        size_t bv_def_id_count, 
        GDefID* mv_bv_def_id_array,
        size_t source_node_index
    );
    # add_field pushes a field and returns the field's unique index.
    size_t add_poly_module_field(PolyModID template_id, GDefID field_def_id);

    # Module fields are accessed by an index that is determined by the order
    # in which symbols are added.
    # By convention, this should be the order in which source nodes are written
    # in source code.
    GDefID get_poly_mod_field_at(PolyModID poly_mod_id, size_t field_index)
    GDefID get_poly_mod_formal_arg_at(PolyModID poly_mod_id, size_t field_index)
    size_t get_mono_mod_field_count(MonoModID mono_mod_id)
    GDefID get_mono_mod_field_at(MonoModID mono_mod_id, size_t field_index)
    size_t get_mono_mod_origin_poly_mod(MonoModID mono_mod_id)
    size_t get_mono_mod_source_node_index(MonoModID mono_mod_id)

    # instantiation:
    # turn a PolyModID into a MonoModID using some template arguments.
    MonoModID instantiate_poly_mod(
        PolyModID poly_mod_id, 
        ArgListID arg_list_id
    );

    # system info:
    size_t count_all_mono_modules()
    size_t count_registered_lambdas(MonoModID mono_mod_id)
    ExpID get_registered_lambda_at(MonoModID mono_mod_id, size_t index)
    ArgListID get_instantiation_arg_list_id(MonoModID mono_mod_id)

# mast:
cdef extern from "extension/mast.hh" namespace "monomorphizer::mast":
    # Constants:
    extern const NodeID NULL_NODE_ID;

    # Init/drop:
    void ensure_mast_init()
    void drop_mast()

    # Type-specs:
    TypeSpecID new_unit_ts(size_t source_index);
    TypeSpecID new_gid_ts(GDefID def_id, size_t source_index);
    TypeSpecID new_lid_ts(IntStr int_str_id, size_t source_index);
    TypeSpecID new_ptr_ts(TypeSpecID ptd_ts, bint contents_is_mut, size_t source_index);
    TypeSpecID new_array_ts(TypeSpecID ptd_ts, ExpID count_exp, bint contents_is_mut, size_t source_index);
    TypeSpecID new_slice_ts(TypeSpecID ptd_ts, bint contents_is_mut, size_t source_index);
    TypeSpecID new_func_sgn_ts(TypeSpecID arg_ts, TypeSpecID ret_ts, SES ret_ses, size_t source_index);
    TypeSpecID new_tuple_ts(size_t elem_ts_count, TypeSpecID* mv_elem_ts_array, size_t source_index);
    TypeSpecID new_get_mono_module_field_ts(MonoModID mono_mod_id, size_t ts_field_ix, size_t source_index);
    TypeSpecID new_get_poly_module_field_ts(
        PolyModID poly_mod_id,
        size_t ts_field_ix,
        size_t actual_arg_count,
        NodeID* actual_arg_array, 
        size_t source_index
    );

    # Expressions:
    ExpID new_unit_exp(size_t source_index);
    ExpID new_int_exp(size_t mantissa, IntegerSuffix typing_suffix, bint is_neg, size_t source_index);
    ExpID new_float_exp(double value, FloatSuffix typing_suffix, size_t source_index);
    ExpID new_string_exp(size_t code_point_count, int* code_point_array, size_t source_index);
    ExpID new_gid_exp(GDefID def_id, size_t source_index);
    ExpID new_lid_exp(IntStr int_str_id, size_t source_index);
    ExpID new_func_call_exp(ExpID called_fn, ExpID arg_exp, bint call_is_non_tot, size_t source_index);
    ExpID new_tuple_exp(size_t item_count, ExpID* mv_item_array, size_t source_index);
    ExpID new_unary_op_exp(UnaryOp unary_op, ExpID arg_exp, size_t source_index);
    ExpID new_binary_op_exp(BinaryOp binary_op, ExpID lt_arg_exp, ExpID rt_arg_exp, size_t source_index);
    ExpID new_if_then_else_exp(ExpID cond_exp, ExpID then_exp, ExpID else_exp, size_t source_index);
    ExpID new_get_tuple_field_by_index_exp(ExpID tuple_exp_id, size_t index, size_t source_index);
    ExpID new_lambda_exp(
            uint32_t arg_name_count,
            IntStr* arg_name_array,
            uint32_t ctx_enclosed_name_count,
            IntStr* ctx_enclosed_name_array,
            ExpID body_exp, 
            size_t source_index
    );
    ExpID new_allocate_one_exp(
        ExpID stored_val_exp_id, 
        AllocationTarget allocation_target, 
        bint allocation_is_mut, 
        size_t source_index
    );
    ExpID new_allocate_many_exp(
        ExpID initializer_stored_val_exp_id,
        ExpID alloc_count_exp,
        AllocationTarget allocation_target,
        bint allocation_is_mut,
        size_t source_index
    );
    ExpID new_chain_exp(
        size_t prefix_elem_id_count, 
        ElemID* prefix_elem_id_array, 
        ExpID ret_exp_id, 
        size_t source_index
    );
    ExpID new_get_mono_module_field_exp(
        MonoModID mono_mod_id, 
        size_t exp_field_ix,
        size_t source_index
    );
    ExpID new_get_poly_module_field_exp(
        PolyModID poly_mod_id, size_t exp_field_ix,
        size_t arg_count, 
        NodeID* arg_array,
        size_t source_index
    )
    ExpID new_cast_exp(
        TypeSpecID ts_id,
        ExpID exp_id,
        size_t source_index
    )

    # Element creation methods:
    ElemID new_bind1v_elem(IntStr bound_def_id, ExpID init_exp_id, size_t source_index);
    ElemID new_bind1t_elem(IntStr bound_def_id, TypeSpecID init_ts_id, size_t source_index);
    ElemID new_do_elem(ExpID eval_exp_id, size_t source_index);

    # Shared:
    size_t get_source_node_index(NodeID node_id)
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

    TypeKind kind_of_tid(TID tid);
    size_t get_tuple_count(TID tuple_tid);
    ArgListID get_tuple_arg_list(TID tuple_tid);
    TID get_func_tid_arg_tid(TID func_tid)
    TID get_func_tid_ret_tid(TID func_tid)
    SES get_func_tid_ses(TID func_tid)

# mval:
cdef extern from "extension/mval.hh" namespace "monomorphizer::mval":
    ValueKind value_kind(VID value_id)
    ValueInfo value_info(VID value_id)
    size_t get_seq_count(size_t seq_info_index)
    bint get_seq_elem1_compatibility(size_t seq_info_index, size_t index, VID* out_vid)
    bint get_seq_elem2_compatibility(VID tuple_val_id, size_t index, VID* out_vid)
    FuncInfo* get_func_info(size_t func_info_index)
    VCellID get_ptr_vcell(size_t ptr_info_index)
    size_t count_array_vcells(size_t array_info_index)
    size_t count_slice_vcells(size_t slice_info_index)
    VCellID get_array_vcell(size_t array_info_index, size_t index)
    VCellID get_slice_vcell(size_t slice_info_index, size_t index)
    bint equals(VID v1, VID v2)
    size_t count_str_code_points(size_t str_info_index);
    int get_str_code_point_at(size_t str_info_index, size_t code_point_index);

# vcell:
cdef extern from "extension/vcell.hh" namespace "monomorphizer::vcell":
    VID get_vcell_val(VCellID vcell_id)

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
    ExpID w_new_unit_exp(size_t source_index):
        return new_unit_exp(source_index)
    ExpID w_new_int_exp(size_t mantissa, IntegerSuffix int_suffix, bint is_neg, size_t source_index):
        return new_int_exp(mantissa, int_suffix, is_neg, source_index)
    ExpID w_new_float_exp(double value, FloatSuffix float_suffix, size_t source_index):
        return new_float_exp(value, float_suffix, source_index)
    ExpID w_new_string_exp(size_t code_point_count, int* code_point_array, size_t source_index):
        return new_string_exp(code_point_count, code_point_array, source_index)
    ExpID w_new_lid_exp(IntStr int_str_id, size_t source_index):
        return new_lid_exp(int_str_id, source_index)
    ExpID w_new_gid_exp(GDefID def_id, size_t source_index):
        return new_gid_exp(def_id, source_index)
    ExpID w_new_func_call_exp(ExpID called_fn, ExpID arg_exp, bint call_is_non_tot, size_t source_index):
        return new_func_call_exp(called_fn, arg_exp, call_is_non_tot, source_index)
    ExpID w_new_tuple_exp(size_t item_count, ExpID* mv_item_array, size_t source_index):
        return new_tuple_exp(item_count, mv_item_array, source_index)
    ExpID w_new_unary_op_exp(UnaryOp unary_op, ExpID arg_exp, size_t source_index):
        return new_unary_op_exp(unary_op, arg_exp, source_index)
    ExpID w_new_binary_op_exp(BinaryOp binary_op, ExpID lt_arg_exp, ExpID rt_arg_exp, size_t source_index):
        return new_binary_op_exp(binary_op, lt_arg_exp, rt_arg_exp, source_index)
    ExpID w_new_if_then_else_exp(ExpID cond_exp, ExpID then_exp, ExpID else_exp, size_t source_index):
        return new_if_then_else_exp(cond_exp, then_exp, else_exp, source_index)
    ExpID w_new_get_tuple_field_by_index_exp(ExpID tuple_exp_id, size_t index, size_t source_index):
        return new_get_tuple_field_by_index_exp(tuple_exp_id, index, source_index)
    ExpID w_new_lambda_exp(
            uint32_t arg_name_count,
            IntStr* arg_name_array,
            uint32_t ctx_enclosed_name_count,
            IntStr* ctx_enclosed_name_array,
            ExpID body_exp,
            size_t source_index
    ):
        return new_lambda_exp(
            arg_name_count, arg_name_array,
            ctx_enclosed_name_count, ctx_enclosed_name_array,
            body_exp,
            source_index
        )
    ExpID w_new_allocate_one_exp(
        ExpID stored_val_exp_id, 
        AllocationTarget allocation_target, 
        bint allocation_is_mut,
        size_t source_index
    ):
        return new_allocate_one_exp(stored_val_exp_id, allocation_target, allocation_is_mut, source_index)
    ExpID w_new_allocate_many_exp(
        ExpID initializer_stored_val_exp_id,
        ExpID alloc_count_exp,
        AllocationTarget allocation_target,
        bint allocation_is_mut,
        size_t source_index
    ):
        return new_allocate_many_exp(
            initializer_stored_val_exp_id,
            alloc_count_exp,
            allocation_target,
            allocation_is_mut,
            source_index
        )
    ExpID w_new_chain_exp(
        size_t prefix_elem_id_count, 
        ElemID* mv_prefix_elem_id_array, 
        ExpID ret_exp_id,
        size_t source_index
    ):
        return new_chain_exp(prefix_elem_id_count, mv_prefix_elem_id_array, ret_exp_id, source_index)
    ExpID w_new_get_mono_module_field_exp(MonoModID mono_mod_id, size_t exp_field_ix, size_t source_index):
        return new_get_mono_module_field_exp(mono_mod_id, exp_field_ix, source_index)
    ExpID w_new_get_poly_module_field_exp(
        PolyModID poly_mod_id, size_t exp_field_ix,
        size_t arg_count, NodeID* arg_array,
        size_t source_index
    ):
        return new_get_poly_module_field_exp(
            poly_mod_id, exp_field_ix,
            arg_count, arg_array,
            source_index
        )
    ExpID w_new_cast_exp(TypeSpecID ts_id, ExpID exp_id, size_t source_index):
        return new_cast_exp(ts_id, exp_id, source_index)

# mast: type-specs:
cdef:
    TypeSpecID w_new_unit_ts(size_t source_index):
        return new_unit_ts(source_index)
    TypeSpecID w_new_gid_ts(GDefID def_id, size_t source_index):
        return new_gid_ts(def_id, source_index)
    TypeSpecID w_new_lid_ts(IntStr int_str_id, size_t source_index):
        return new_lid_ts(int_str_id, source_index)
    TypeSpecID w_new_ptr_ts(TypeSpecID ptd_ts, bint contents_is_mut, size_t source_index):
        return new_ptr_ts(ptd_ts, contents_is_mut, source_index)
    TypeSpecID w_new_array_ts(TypeSpecID ptd_ts, ExpID count_exp, bint contents_is_mut, size_t source_index):
        return new_array_ts(ptd_ts, count_exp, contents_is_mut, source_index)
    TypeSpecID w_new_slice_ts(TypeSpecID ptd_ts, bint contents_is_mut, size_t source_index):
        return new_slice_ts(ptd_ts, contents_is_mut, source_index)
    TypeSpecID w_new_func_sgn_ts(TypeSpecID arg_ts, TypeSpecID ret_ts, SES ret_ses, size_t source_index):
        return new_func_sgn_ts(arg_ts, ret_ts, ret_ses, source_index)
    TypeSpecID w_new_tuple_ts(size_t elem_ts_count, TypeSpecID* mv_elem_ts_array, size_t source_index):
        return new_tuple_ts(elem_ts_count, mv_elem_ts_array, source_index)
    TypeSpecID w_new_get_mono_module_field_ts(MonoModID mono_mod_id, size_t ts_field_ix, size_t source_index):
        return new_get_mono_module_field_ts(mono_mod_id, ts_field_ix, source_index)
    TypeSpecID w_new_get_poly_module_field_ts(
        PolyModID poly_mod_id,
        size_t ts_field_ix,
        size_t actual_arg_count,
        NodeID* actual_arg_array,
        size_t source_index
    ):
        return new_get_poly_module_field_ts(
            poly_mod_id,
            ts_field_ix,
            actual_arg_count,
            actual_arg_array,
            source_index
        )

# mast: elem:
cdef:
    ElemID w_new_bind1v_elem(GDefID bound_def_id, ExpID init_exp_id, size_t source_index):
        return new_bind1v_elem(bound_def_id, init_exp_id, source_index)
        
    ElemID w_new_bind1t_elem(GDefID bound_def_id, TypeSpecID init_ts_id, size_t source_index):
        return new_bind1t_elem(bound_def_id, init_ts_id, source_index)

    ElemID w_new_do_elem(ExpID eval_exp_id, size_t source_index):
        return new_do_elem(eval_exp_id, source_index)

# mast: common:
cdef:
    size_t w_get_source_node_index(NodeID node_id):
        return get_source_node_index(node_id)

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
    PolyModID w_new_polymorphic_module(
        char* mv_template_name, 
        size_t bv_def_id_count, 
        GDefID* mv_bv_def_id_array,
        size_t source_node_index
    ):
        return new_polymorphic_module(mv_template_name, bv_def_id_count, mv_bv_def_id_array, source_node_index)
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
    size_t w_get_mono_mod_origin_poly_mod(MonoModID mono_mod_id):
        return get_mono_mod_origin_poly_mod(mono_mod_id)
    size_t w_get_mono_mod_source_node_index(MonoModID mono_mod_id):
        return get_mono_mod_source_node_index(mono_mod_id)

    # instantiation:
    # turn a PolyModID into a MonoModID using some template arguments.
    MonoModID w_instantiate_poly_mod(
        PolyModID poly_mod_id, 
        ArgListID arg_list_id
    ):
        return instantiate_poly_mod(
            poly_mod_id,
            arg_list_id
        )

    # mono module count:
    size_t w_count_all_mono_modules():
        return count_all_mono_modules()

    size_t w_count_registered_lambdas(MonoModID mono_mod_id):
        return count_registered_lambdas(mono_mod_id)
    
    ExpID w_get_registered_lambda_at(MonoModID mono_mod_id, size_t index):
        return get_registered_lambda_at(mono_mod_id, index)

    ArgListID w_get_instantiation_arg_list_id(MonoModID mono_mod_id):
        return get_instantiation_arg_list_id(mono_mod_id)


# interning:
cdef:
    IntStr w_intern_string_1(cpp_string s, bint is_id_tid_not_vid):
        return intern_string(s, is_id_tid_not_vid)
    IntStr w_intern_string_2(const char* nt_bytes, bint is_id_tid_not_vid):
        s = cpp_string(nt_bytes)
        return intern_string(s, is_id_tid_not_vid)
    cpp_string w_get_interned_string(IntStr int_str_id):
        return get_interned_string(int_str_id)
    bint w_is_interned_string_tid_not_vid(IntStr int_str_id):
        return is_interned_string_tid_not_vid(int_str_id)

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
    size_t w_arg_list_head(ArgListID arg_list_id):
        return arg_list_head_compatibility(arg_list_id)
    ArgListID w_arg_list_tail(ArgListID arg_list_id):
        return arg_list_tail_compatibility(arg_list_id)


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
    VCellID w_get_ptr_vcell(size_t ptr_info_index):
        return get_ptr_vcell(ptr_info_index)
    size_t w_count_array_vcells(size_t array_info_index):
        return count_array_vcells(array_info_index)
    size_t w_count_slice_vcells(size_t slice_info_index):
        return count_slice_vcells(slice_info_index)
    VCellID w_get_array_vcell(size_t array_info_index, size_t index):
        return get_array_vcell(array_info_index, index)
    VCellID w_get_slice_vcell(size_t slice_info_index, size_t index):
        return get_slice_vcell(slice_info_index, index)
    bint w_equals(VID v1, VID v2):
        return equals(v1, v2)
    size_t w_count_str_code_points(size_t str_info_index):
        return count_str_code_points(str_info_index)
    int w_get_str_code_point_at(size_t str_info_index, size_t code_point_index):
        return get_str_code_point_at(str_info_index, code_point_index)

# VCell:
cdef:
    VID w_get_vcell_val(VCellID vcell_id):
        return get_vcell_val(vcell_id)


# MType:
cdef:
    TypeKind w_kind_of_tid(TID tid):
        return kind_of_tid(tid)
    size_t w_get_tuple_count(TID tuple_tid):
        return get_tuple_count(tuple_tid)
    ArgListID w_get_tuple_arg_list(TID tuple_tid):
        return get_tuple_arg_list(tuple_tid)
    TID w_get_func_mtid_arg_mtid(TID func_mtid):
        return get_func_tid_arg_tid(func_mtid)
    TID w_get_func_mtid_ret_mtid(TID func_mtid):
        return get_func_tid_ret_tid(func_mtid)
    SES w_get_func_mtid_ses(TID func_mtid):
        return get_func_tid_ses(func_mtid)
