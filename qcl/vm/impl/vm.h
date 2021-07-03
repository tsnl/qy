#pragma once

#include <stdint.h>
#include <stdbool.h>

#include "core.h"
#include "expr.h"
#include "consts.h"

typedef struct VM VM;

typedef uint64_t ExprID;
typedef uint64_t RtTypeID;
typedef uint64_t ValueID;
typedef uint64_t IntStr;

// VM creation/destruction:
VM* vm_create();
void vm_destroy(VM* vm);

// registering DefIDs:
//  - todo: get `raw_def_id` as id(definitions.BaseRec) from Python
DefID vm_map_def_id(char const* def_name, size_t raw_def_id);

// function declaration, defining funcs using expressions:
FuncID vm_declare_fn(VM* vm, DefID opt_def_id);
void vm_define_fn(VM* vm, FuncID func_id, ExprID expr_id);

// expressions: lazy-functional-encoding of the language: bound to funcs as definitions.
//  - chains are factored into `let ... in ...` expressions.
//  - discard maps to eval_in, just `let _ = expr in ...` where `_` is discarded.
// NOTE: expressions are strings: written instructions for how to compute a value from other values (IDs)
// NOTE: expressions are 'analysis capable' <=> we can query side-effects-specifier IF expression context-free.

// atoms:
ExprID vm_mk_id_expr(VM* vm, DefID def_id);
ExprID vm_mk_unit_expr(VM* vm);
ExprID vm_mk_literal_int_expr(VM* vm, uint64_t raw_val, size_t width_in_bytes, bool is_signed);
ExprID vm_mk_literal_float_expr(VM* vm, double f, size_t width_in_bytes);
ExprID vm_mk_literal_string_expr(VM* vm, uint64_t bytes_count, char const* bytes);
ExprID vm_mk_literal_array_expr(VM* vm, uint64_t length, ExprID const* element_expr_id_array);
ExprID vm_mk_literal_tuple_expr(VM* vm, uint64_t length, ExprID const* element_expr_id_array);
ExprID vm_mk_sizeof_expr(VM* vm, RtTypeID type_expr);
// complex:
ExprID vm_mk_if_expr(VM* vm, ExprID cond_expr_id, ExprID then_expr_id, ExprID else_expr_id);
ExprID vm_mk_call1_expr(VM* vm, ExprID fn_expr_id, ExprID arg_expr_id, bool allow_non_tot);
ExprID vm_mk_bao_expr(VM* vm, BinaryArithmeticOperator bao, ExprID lhs_arg_expr, ExprID rhs_arg_expr);
ExprID vm_mk_cmp_expr(VM* vm, BinaryComparisonOperator bco, ExprID lhs_arg_expr, ExprID rhs_arg_expr);
ExprID vm_mk_alloc_1_expr(VM* vm, Allocator allocator, ExprID stored_value);
ExprID vm_mk_alloc_n_expr(VM* vm, Allocator allocator, ExprID count, ExprID elem_size);
ExprID vm_mk_deref_expr(VM* vm, ExprID ptr_expr);
ExprID vm_mk_assign_expr(VM* vm, ExprID ptr_expr, ExprID assigned_expr);
ExprID vm_mk_get_tuple_elem_expr(VM* vm, ExprID expr_id, ExprID element_index);
ExprID vm_mk_get_tuple_ptr_elem_ptr_expr(VM* vm, ExprID expr_id, ExprID element_index);
ExprID vm_mk_get_adt_elem_expr(VM* vm, ExprID expr_id, ExprID element_index);
ExprID vm_mk_get_adt_ptr_elem_ptr_expr(VM* vm, ExprID expr_id, ExprID element_index);
ExprID vm_mk_get_list_item_ptr_expr(VM* vm, ExprID array, ExprID index);
ExprID vm_mk_eval_in_expr(VM* vm, ExprID discarded_expr, ExprID in_expr);
ExprID vm_mk_let_in_expr(VM* vm, DefID def_id, ExprID init_expr, ExprID in_expr);

// evaluation: turns expressions into values or equivalent property
Const vm_evaluate_value(ExprID expr_id);
RtTypeID vm_evaluate_rttid(ExprID expr_id);
