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

namespace monomorphizer::mast {

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
        TS_STRUCT,
        TS_UNION,
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
        EXP_GET_TUPLE_FIELD_BY_INDEX,
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
    // Helpers:
    //

    struct NameNodeRelation {
        DefID name;
        NodeID node;
    };

    //
    // Type Spec Node Infos:
    //

    struct IdTypeSpecNodeInfo {
        DefID def_id;
    };

    struct PtrTypeSpecNodeInfo {
        TypeSpecID ptd_ts;
        bool contents_is_mut;
    };

    struct ArrayTypeSpecNodeInfo {
        TypeSpecID ptd_ts;
        ExpID count_exp;
        bool contents_is_mut;
    };

    struct SliceTypeSpecNodeInfo {
        TypeSpecID ptd_ts;
        bool contents_is_mut;
    };

    struct FuncSgnTypeSpecNodeInfo {
        TypeSpecID arg_ts;
        TypeSpecID ret_ts;
        SES ret_ses;
    };

    struct TupleTypeSpecNodeInfo {
        TypeSpecID* elem_ts_array;
        size_t elem_ts_count;
    };

    struct CompoundTypeSpecNodeInfo {
        NameNodeRelation* elem_ts_array;
        size_t elem_ts_count;
    };

    struct GetPolyModuleFieldTypeSpecNodeInfo {
        size_t args_count;
        NodeID* args_array;
        PolyModID template_id;
        DefID polymorphic_def_id;
    };

    struct GetMonoModuleFieldTypeSpecNodeInfo {
        MonoModID template_id;
        DefID def_id;
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
        ExpID called_fn;
        ExpID* arg_exp_array;
        size_t arg_exp_count;
        int call_is_non_tot;
    };

    struct UnaryOpExpNodeInfo {
        ExpID arg_exp;
        UnaryOp unary_op;
    };

    struct BinaryOpExpNodeInfo {
        ExpID lt_arg_exp;
        ExpID rt_arg_exp;
        BinaryOp binary_op;
    };

    struct IfThenElseExpNodeInfo {
        ExpID cond_exp;
        ExpID then_exp;
        ExpID else_exp;
    };

    struct GetTupleFieldByIndexExpNodeInfo {
        ExpID tuple_exp_id;
        ExpID index_exp_id;
    };

    struct LambdaExpNodeInfo {
        DefID* arg_name_array;
        size_t arg_name_count;
        ExpID body_exp;
    };

    struct AllocateOneExpNodeInfo {
        ExpID stored_val_exp_id;
        AllocationTarget allocation_target;
        bool allocation_is_mut;
    };

    struct AllocateManyExpNodeInfo {
        ExpID initializer_stored_val_exp_id;
        ExpID alloc_count_exp;
        AllocationTarget allocation_target;
        bool allocation_is_mut;
    };

    struct ChainExpNodeInfo {
        ElemID* prefix_elem_array;
        size_t prefix_elem_count;
        ExpID ret_exp_id;
    };

    struct GetPolyModuleFieldExpNodeInfo {
        size_t arg_count;
        NodeID* arg_array;
        PolyModID template_id;
        DefID def_id;
    };

    struct GetMonoModuleFieldExpNodeInfo {
        MonoModID template_id;
        DefID def_id;
    };

    //
    // Element Node Info
    //

    struct Bind1VElemNodeInfo {
        DefID bound_def_id;
        ExpID init_exp_id;
    };

    struct DoElemNodeInfo {
        ExpID eval_exp_id;
    };

    //
    // Since some expressions take no arguments, we cache a constant instead.
    //

    struct SingletonNodeCache {
        TypeSpecID ts_unit;
        ExpID exp_unit;
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
        CompoundTypeSpecNodeInfo ts_compound;
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
        GetTupleFieldByIndexExpNodeInfo exp_get_tuple_field_by_index;
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
    TypeSpecID get_unit_ts();
    TypeSpecID new_id_ts(DefID def_id);
    TypeSpecID new_ptr_ts(
        TypeSpecID ptd_ts,
        bool contents_is_mut
    );
    TypeSpecID new_array_ts(
        TypeSpecID ptd_ts,
        ExpID count_exp,
        bool contents_is_mut
    );
    TypeSpecID new_slice_ts(
        TypeSpecID ptd_ts,
        bool contents_is_mut
    );
    TypeSpecID new_func_sgn_ts(
        TypeSpecID arg_ts,
        TypeSpecID ret_ts,
        SES ret_ses
    );
    TypeSpecID new_tuple_ts(
        size_t elem_ts_count,
        TypeSpecID* elem_ts_list
    );
    TypeSpecID new_struct_ts(
        size_t elem_ts_count,
        NameNodeRelation* elem_ts_array
    );
    TypeSpecID new_union_ts(
        size_t elem_ts_count,
        NameNodeRelation* elem_ts_array
    );
    // todo: add constructors for Get{Mono|Poly}ModuleFieldTypeSpec

    // Expressions:
    ExpID get_unit_exp();
    ExpID new_int_exp(
        size_t mantissa,
        bool is_neg
    );
    ExpID new_float_exp(
        double value
    );
    ExpID new_string_exp(
        size_t code_point_count,
        int* code_point_array
    );
    ExpID new_id_exp(
        DefID def_id
    );
    ExpID new_func_call_exp(
        ExpID called_fn,
        size_t arg_exp_id_count,
        ExpID* arg_exp_id_array,
        bool call_is_non_tot
    );
    ExpID new_unary_op_exp(
        UnaryOp unary_op,
        ExpID arg_exp
    );
    ExpID new_binary_op_exp(
        BinaryOp binary_op,
        ExpID lt_arg_exp,
        ExpID rt_arg_exp
    );
    ExpID new_if_then_else_exp(
        ExpID cond_exp,
        ExpID then_exp,
        ExpID else_exp
    );
    ExpID new_get_tuple_field_by_index_exp(
        ExpID tuple_exp_id,
        ExpID index_exp_id
    );
    ExpID new_lambda_exp(
        size_t arg_name_count,
        DefID* arg_name_array,
        ExpID body_exp
    );
    ExpID new_allocate_one_exp(
        ExpID stored_val_exp_id,
        AllocationTarget allocation_target,
        bool allocation_is_mut
    );
    ExpID new_allocate_many_exp(
        ExpID initializer_stored_val_exp_id,
        ExpID alloc_count_exp,
        AllocationTarget allocation_target,
        bool allocation_is_mut
    );
    ExpID new_chain_exp(
        size_t prefix_elem_id_count,
        ElemID* prefix_elem_id_array,
        ExpID ret_exp_id
    );
    // todo: add constructors for Get{Mono|Poly}ModuleFieldExp

    // Element creation methods:
    ElemID new_bind1v_elem(
        DefID bound_def_id,
        ExpID init_exp_id
    );
    ElemID new_do_elem(
        ExpID eval_exp_id
    );

    //
    // Data Accessors:
    //

    NodeInfo* get_info_ptr(NodeID node_id);

}
