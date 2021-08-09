// This module provides a representation of a monomorphic AST
// This representation can then be queried (for subsequent operations), and 
// later, evaluated.
// NOTE: the DefIDs used here are distinct from the DefIDs generated previously.
// - TODO: delete the old version since it is no longer required

#pragma once

#include <cstddef>
#include <cstdlib>

#include "id-mast.hh"
#include "id-defs.hh"
#include "id-modules.hh"
#include "shared-enums.hh"

namespace monomorphizer::mast {

    //
    // Node Kind enum:
    //

    enum class NodeKind {
        // type-specifiers:
        TS_UNIT,
        TS_ID,
        TS_PTR,
        TS_ARRAY,
        TS_SLICE,
        TS_FUNC_SGN,
        TS_TUPLE,
        TS_GET_POLY_MODULE_FIELD,
        TS_GET_MONO_MODULE_FIELD,

        // expressions:
        EXP_UNIT,
        EXP_INT,
        EXP_FLOAT,
        EXP_STRING,
        EXP_ID,
        EXP_FUNC_CALL,
        EXP_UNARY_OP,
        EXP_BINARY_OP,
        EXP_IF_THEN_ELSE,
        EXP_GET_TUPLE_FIELD,
        EXP_GET_POLY_MODULE_FIELD,
        EXP_GET_MONO_MODULE_FIELD,
        EXP_LAMBDA,
        EXP_ALLOCATE_ONE,
        EXP_ALLOCATE_MANY,
        EXP_CHAIN,

        // chain elements:
        ELEM_BIND1V,
        ELEM_DO,
    };

    //
    // Type Spec Node Infos:
    //

    struct IdTypeSpecNodeInfo {
        DefID def_id;
    };

    struct PtrTypeSpecNodeInfo {
        mast::TypeSpecID ptd_ts;
        bool contents_is_mut;
    };

    struct ArrayTypeSpecNodeInfo {
        mast::TypeSpecID ptd_ts;
        mast::ExpID count_exp;
        bool contents_is_mut;
    };

    struct SliceTypeSpecNodeInfo {
        mast::TypeSpecID ptd_ts;
        bool contents_is_mut;
    };

    struct FuncSgnTypeSpecNodeInfo {
        mast::TypeSpecID arg_ts;
        mast::TypeSpecID ret_ts;
        SES ret_ses;
    };

    struct TupleTypeSpecNodeInfo {
        mast::TypeSpecID* elem_ts_array;
        size_t elem_ts_count;
    };

    struct GetPolyModuleFieldTypeSpecNodeInfo {
        size_t actual_arg_count;
        mast::NodeID* actual_arg_array;
        PolyModID template_id;
        size_t ts_field_index;
    };

    struct GetMonoModuleFieldTypeSpecNodeInfo {
        MonoModID template_id;
        size_t ts_field_index;
    };

    //
    // Expression Node Infos:
    //

    struct IntExpNodeInfo {
        size_t mantissa;
        int is_neg;
    };

    struct FloatExpNodeInfo {
        double value;
    };

    struct StringExpNodeInfo {
        int* code_point_array;
        size_t code_point_count;
    };

    struct IdExpNodeInfo {
        DefID def_id;
    };

    struct FuncCallExpNodeInfo {
        mast::ExpID called_fn;
        mast::ExpID arg_exp_id;
        int call_is_non_tot;
    };

    struct UnaryOpExpNodeInfo {
        mast::ExpID arg_exp;
        UnaryOp unary_op;
    };

    struct BinaryOpExpNodeInfo {
        mast::ExpID lt_arg_exp;
        mast::ExpID rt_arg_exp;
        BinaryOp binary_op;
    };

    struct IfThenElseExpNodeInfo {
        mast::ExpID cond_exp;
        mast::ExpID then_exp;
        mast::ExpID else_exp;
    };

    struct GetTupleFieldExpNodeInfo {
        mast::ExpID tuple_exp_id;
        size_t index;
    };

    struct LambdaExpNodeInfo {
        DefID* arg_name_array;
        size_t arg_name_count;
        mast::ExpID body_exp;
    };

    struct AllocateOneExpNodeInfo {
        mast::ExpID stored_val_exp_id;
        AllocationTarget allocation_target;
        bool allocation_is_mut;
    };

    struct AllocateManyExpNodeInfo {
        mast::ExpID initializer_stored_val_exp_id;
        mast::ExpID alloc_count_exp;
        AllocationTarget allocation_target;
        bool allocation_is_mut;
    };

    struct ChainExpNodeInfo {
        mast::ElemID* prefix_elem_array;
        size_t prefix_elem_count;
        mast::ExpID ret_exp_id;
    };

    struct GetPolyModuleFieldExpNodeInfo {
        size_t arg_count;
        mast::NodeID* arg_array;
        PolyModID template_id;
        size_t field_index;
    };

    struct GetMonoModuleFieldExpNodeInfo {
        MonoModID template_id;
        size_t field_index;
    };

    //
    // Element Node Info
    //

    struct Bind1VElemNodeInfo {
        DefID bound_def_id;
        mast::ExpID init_exp_id;
    };

    struct DoElemNodeInfo {
        mast::ExpID eval_exp_id;
    };

    //
    // Since some expressions take no arguments, we cache a constant instead.
    //

    struct SingletonNodeCache {
        mast::TypeSpecID ts_unit;
        mast::ExpID exp_unit;
    };

    //
    //
    // Union of all NodeInfo:
    //
    //

    union NodeInfo {
        // type-specs:
        IdTypeSpecNodeInfo ts_id;
        PtrTypeSpecNodeInfo ts_ptr;
        ArrayTypeSpecNodeInfo ts_array;
        SliceTypeSpecNodeInfo ts_slice;
        FuncSgnTypeSpecNodeInfo ts_func_sgn;
        TupleTypeSpecNodeInfo ts_tuple;
        GetMonoModuleFieldTypeSpecNodeInfo ts_get_mono_module_field;
        GetPolyModuleFieldTypeSpecNodeInfo ts_get_poly_module_field;

        // expressions:
        IntExpNodeInfo exp_int;
        FloatExpNodeInfo exp_float;
        StringExpNodeInfo exp_str;
        IdExpNodeInfo exp_id;
        FuncCallExpNodeInfo exp_call;
        UnaryOpExpNodeInfo exp_unary;
        BinaryOpExpNodeInfo exp_binary;
        IfThenElseExpNodeInfo exp_if_then_else;
        GetTupleFieldExpNodeInfo exp_get_tuple_field;
        LambdaExpNodeInfo exp_lambda;
        AllocateOneExpNodeInfo exp_allocate_one;
        AllocateManyExpNodeInfo exp_allocate_many;
        ChainExpNodeInfo exp_chain;
        GetMonoModuleFieldExpNodeInfo exp_get_mono_module_field;
        GetPolyModuleFieldExpNodeInfo exp_get_poly_module_field;

        // elements:
        Bind1VElemNodeInfo elem_bind1v;
        DoElemNodeInfo elem_do;
    };

    //
    // Managing nodes:
    //

    void ensure_init();
    void drop();

    //
    // Node Constructors
    //

    // Type-specifiers:
    mast::TypeSpecID get_unit_ts();
    mast::TypeSpecID new_id_ts(DefID def_id);
    mast::TypeSpecID new_ptr_ts(
        mast::TypeSpecID ptd_ts,
        bool contents_is_mut
    );
    mast::TypeSpecID new_array_ts(
        mast::TypeSpecID ptd_ts,
        mast::ExpID count_exp,
        bool contents_is_mut
    );
    mast::TypeSpecID new_slice_ts(
        mast::TypeSpecID ptd_ts,
        bool contents_is_mut
    );
    mast::TypeSpecID new_func_sgn_ts(
        mast::TypeSpecID arg_ts,
        mast::TypeSpecID ret_ts,
        SES ret_ses
    );
    mast::TypeSpecID new_tuple_ts(
        size_t elem_ts_count,
        mast::TypeSpecID* mv_elem_ts_array
    );
    mast::TypeSpecID new_get_mono_module_field_ts(
        MonoModID mono_mod_id,
        size_t ts_field_ix
    );
    mast::TypeSpecID new_get_poly_module_field_ts(
        PolyModID poly_mod_id,
        size_t ts_field_ix,
        size_t actual_arg_count,
        mast::NodeID* actual_arg_array
    );
    
    // Expressions:
    mast::ExpID get_unit_exp();
    mast::ExpID new_int_exp(
        size_t mantissa,
        bool is_neg
    );
    mast::ExpID new_float_exp(
        double value
    );
    mast::ExpID new_string_exp(
        size_t code_point_count,
        int* code_point_array
    );
    mast::ExpID new_id_exp(
        DefID def_id
    );
    mast::ExpID new_func_call_exp(
        mast::ExpID called_fn,
        mast::ExpID arg_exp,
        bool call_is_non_tot
    );
    mast::ExpID new_unary_op_exp(
        UnaryOp unary_op,
        mast::ExpID arg_exp
    );
    mast::ExpID new_binary_op_exp(
        BinaryOp binary_op,
        mast::ExpID lt_arg_exp,
        mast::ExpID rt_arg_exp
    );
    mast::ExpID new_if_then_else_exp(
        mast::ExpID cond_exp,
        mast::ExpID then_exp,
        mast::ExpID else_exp
    );
    mast::ExpID new_get_tuple_field_by_index_exp(
        mast::ExpID tuple_exp_id,
        size_t index
    );
    mast::ExpID new_lambda_exp(
        size_t arg_name_count,
        DefID* arg_name_array,
        mast::ExpID body_exp
    );
    mast::ExpID new_allocate_one_exp(
        mast::ExpID stored_val_exp_id,
        AllocationTarget allocation_target,
        bool allocation_is_mut
    );
    mast::ExpID new_allocate_many_exp(
        mast::ExpID initializer_stored_val_exp_id,
        mast::ExpID alloc_count_exp,
        AllocationTarget allocation_target,
        bool allocation_is_mut
    );
    mast::ExpID new_chain_exp(
        size_t prefix_elem_id_count,
        mast::ElemID* prefix_elem_id_array,
        mast::ExpID ret_exp_id
    );
    mast::ExpID new_get_mono_module_field_exp(
        MonoModID mono_mod_id,
        size_t exp_field_ix
    );
    mast::ExpID new_get_poly_module_field_exp(
        PolyModID poly_mod_id,
        size_t exp_field_ix
    );
    
    // Element creation methods:
    mast::ElemID new_bind1v_elem(
        DefID bound_def_id,
        mast::ExpID init_exp_id
    );
    mast::ElemID new_do_elem(
        mast::ExpID eval_exp_id
    );

    //
    // Data Accessors:
    //

    NodeKind get_node_kind(mast::NodeID node_id);
    NodeInfo* get_info_ptr(mast::NodeID node_id);

}
