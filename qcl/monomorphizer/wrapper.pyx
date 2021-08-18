"""
This module wraps the `extension/` directory.
"""

from libc.stddef cimport size_t
from libc.stdint cimport uint32_t
# from qcl.monomorphizer cimport wrapper 

#
#
# Cpp Linking:
#
#

# arg list:
cdef extern from "extension/arg-list.hh" namespace "monomorphizer::arg_list":
    const ArgListID EMPTY

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
    );

    # Element creation methods:
    ElemID new_bind1v_elem(GDefID bound_def_id, ExpID init_exp_id);
    ElemID new_do_elem(ExpID eval_exp_id);

    # Shared:
    NodeKind get_node_kind(NodeID node_id)

# intern:
cdef extern from "extension/intern.hh" namespace "monomorphizer::intern":
    IntStr intern_string(cpp_string s, bint is_tid_not_vid)
    cpp_string get_interned_string(IntStr int_str_id)
    bint is_interned_string_tid_not_vid(IntStr int_str_id)

# printing:
cdef extern from "extension/printing.hh" namespace "monomorphizer::printing":
    void print_poly_mod(PolyModID poly_mod_id)
    void print_mono_mod(MonoModID mono_mod_id)


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
    ExpID w_new_chain_exp(size_t prefix_elem_id_count, ElemID* prefix_elem_id_array, ExpID ret_exp_id):
        return new_chain_exp(prefix_elem_id_count, prefix_elem_id_array, ret_exp_id)
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
    ElemID w_new_do_elem(ExpID eval_exp_id):
        return new_do_elem(eval_exp_id)

# mast: common:
cdef:
    NodeKind w_get_node_kind(NodeID node_id):
        return get_node_kind(node_id)

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
