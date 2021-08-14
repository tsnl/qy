from libc.stddef cimport size_t
from libcpp.string cimport string as cpp_string

#
#
# Externally linked types:
#
#

#
# Core:
#

cdef extern from "extension/shared-enums.hh" namespace "monomorphizer":
    ctypedef enum SES:
        Tot,
        Dv,
        ST,
        Exn,
        ML

    ctypedef enum UnaryOp:
        LogicalNot,
        DeRef,
        Pos,
        Neg

    ctypedef enum BinaryOp:
        Pow,
        Mul, Div, Rem,
        Add, Sub,
        LessThan, LessThanOrEquals, GreaterThan, GreaterThanOrEquals,
        Equals, NotEquals,
        LogicalAnd,
        LogicalOr

    ctypedef enum AllocationTarget:
        Stack,
        Heap

    ctypedef enum IntegerSuffix:
        U1, U8, U16, U32, U64,
        S8, S16, S32, S64

    ctypedef enum FloatSuffix:
        F32, F64


#
# Arg Lists:
#

cdef extern from "extension/id-arg-list.hh" namespace "monomorphizer::arg_list":
    ctypedef size_t ArgListID

#
# Values:
#

cdef extern from "extension/mval.hh" namespace "monomorphizer::mval":
    ctypedef size_t ValueID

#
# Defs:
#

cdef extern from "extension/id-defs.hh" namespace "monomorphizer":
    ctypedef size_t DefID

cdef extern from "extension/defs.hh" namespace "monomorphizer::defs":
    const DefID NULL_DEF_ID;

    ctypedef enum DefKind:
        BV_EXP,
        BV_TS,
        CONST_EXP,
        CONST_TS,
        CONST_TOT_VAL,
        CONST_TOT_TID


#
# Modules:
#

cdef extern from "extension/modules.hh" namespace "monomorphizer":
    ctypedef size_t MonoModID
    ctypedef size_t PolyModID


#
# Intern:
#

cdef extern from "extension/intern.hh" namespace "monomorphizer::intern":
    ctypedef size_t IntStr

#
# Mast:
#

cdef extern from "extension/id-mast.hh" namespace "monomorphizer::mast":
    ctypedef size_t NodeID
    ctypedef NodeID ExpID
    ctypedef NodeID TypeSpecID
    ctypedef NodeID ElemID


#
# TID
#

cdef extern from "extension/mtype.hh" namespace "monomorphizer::mtype":
    ctypedef size_t TID


#
#
# Interface:
#
#

#
# Shared init:
#

cdef:
    void w_init();
    void w_drop();

#
# TODO: add interface to `modules`
#

#
# TODO: add interface to `eval`
#

#
# MAST: create expressions, type specs, and elems:
#

# expressions:
# - TODO: consider supporting local and global IDs separately
cdef:
    ExpID w_get_unit_exp()
    ExpID w_new_int_exp(size_t mantissa, IntegerSuffix int_suffix, bint is_neg)
    ExpID w_new_float_exp(double value, FloatSuffix float_suffix)
    ExpID w_new_string_exp(size_t code_point_count, int* code_point_array)
    ExpID w_new_lid_exp(IntStr int_str_id)
    ExpID w_new_gid_exp(DefID def_id)
    ExpID w_new_func_call_exp(ExpID called_fn, ExpID arg_exp, bint call_is_non_tot)
    ExpID w_new_unary_op_exp(UnaryOp unary_op, ExpID arg_exp)
    ExpID w_new_binary_op_exp(BinaryOp binary_op, ExpID lt_arg_exp, ExpID rt_arg_exp)
    ExpID w_new_if_then_else_exp(ExpID cond_exp, ExpID then_exp, ExpID else_exp)
    ExpID w_new_get_tuple_field_by_index_exp(ExpID tuple_exp_id, size_t index)
    ExpID w_new_lambda_exp(size_t arg_name_count, DefID * arg_name_array, ExpID body_exp)
    ExpID w_new_allocate_one_exp(ExpID stored_val_exp_id, AllocationTarget allocation_target, bint allocation_is_mut)
    ExpID w_new_allocate_many_exp(
        ExpID initializer_stored_val_exp_id,
        ExpID alloc_count_exp,
        AllocationTarget allocation_target,
        bint allocation_is_mut
    )
    ExpID w_new_chain_exp(size_t prefix_elem_id_count, ElemID * prefix_elem_id_array, ExpID ret_exp_id)
    ExpID w_new_get_mono_module_field_exp(MonoModID mono_mod_id, size_t exp_field_ix)
    ExpID w_new_get_poly_module_field_exp(
        PolyModID poly_mod_id, size_t exp_field_ix,
        size_t arg_count, NodeID* arg_array
    )

# type-specs:
# - TODO: consider supporting local and global IDs separately
cdef:
    TypeSpecID w_get_unit_ts()
    TypeSpecID w_new_gid_ts(DefID def_id)
    TypeSpecID w_new_lid_ts(IntStr int_str_id)
    TypeSpecID w_new_ptr_ts(TypeSpecID ptd_ts, bint contents_is_mut)
    TypeSpecID w_new_array_ts(TypeSpecID ptd_ts, ExpID count_exp, bint contents_is_mut)
    TypeSpecID w_new_slice_ts(TypeSpecID ptd_ts, bint contents_is_mut)
    TypeSpecID w_new_func_sgn_ts(TypeSpecID arg_ts, TypeSpecID ret_ts, SES ret_ses)
    TypeSpecID w_new_tuple_ts(size_t elem_ts_count, TypeSpecID* mv_elem_ts_array)
    TypeSpecID w_new_get_mono_module_field_ts(MonoModID mono_mod_id, size_t ts_field_ix)
    TypeSpecID w_new_get_poly_module_field_ts(
        PolyModID poly_mod_id,
        size_t ts_field_ix,
        size_t actual_arg_count,
        NodeID* actual_arg_array
    )

# elements:
cdef:
    ElemID w_new_bind1v_elem(DefID bound_def_id, ExpID init_exp_id)
    ElemID w_new_do_elem(ExpID eval_exp_id)

#
# Defs:
#

# constant definitions:
cdef:
    # declaring definitions for PolyModID fields:
    DefID w_declare_t_const_mast_node(char* mv_def_name)
    DefID w_declare_v_const_mast_node(char* mv_def_name)
    
    # defining definitions in PolyModID fields:
    void w_define_declared_t_const(DefID declared_def_id, TypeSpecID ts_id)
    void w_define_declared_v_const(DefID declared_def_id, ExpID exp_id)
    
    # bound var definitions:
    # monomorphization is just replacing references to these in polymorphic 
    # modules with total const definitions, returning a monomorphic copy.
    DefID w_define_bound_var_ts(char* mv_formal_var_name);
    DefID w_define_bound_var_exp(char* mv_formal_var_name);

    # query definition info:
    bint w_get_def_is_bv(DefID def_id);
    DefKind w_get_def_kind(DefID def_id);
    const char* w_get_def_name(DefID def_id);
    void w_store_id_at_def_id(DefID def_id, size_t id_);
    size_t w_load_id_from_def_id(DefID def_id);

#
# Modules:
#

cdef:
    # Polymorphic template construction:
    # - add_field pushes a field and returns the field's unique index.
    PolyModID w_new_polymorphic_module(char* mv_template_name, size_t bv_def_id_count, DefID* mv_bv_def_id_array);
    size_t w_add_poly_module_field(PolyModID template_id, DefID field_def_id);

    # Module fields are accessed by an index that is determined by the order
    # in which symbols are added.
    # By convention, this should be the order in which source nodes are written
    # in source code.
    size_t w_get_mono_mod_field_count(MonoModID mono_mod_id)
    DefID w_get_mono_mod_field_at(MonoModID mono_mod_id, size_t field_index)

    # instantiation:
    # turn a PolyModID into a MonoModID using some template arguments.
    MonoModID w_instantiate_poly_mod(PolyModID poly_mod_id, ArgListID arg_list_id);

#
# Interning:
#

cdef:
    IntStr w_intern_string_1(cpp_string s)
    IntStr w_intern_string_2(const char* nt_bytes)


#
# printing:
#

cdef:
    void w_print_poly_mod(PolyModID poly_mod_id)
    void w_print_mono_mod(MonoModID mono_mod_id)