#pragma once

#include <stdint.h>
#include <stdbool.h>

#include "core.h"
#include "expr.h"

typedef struct VM VM;
typedef struct Frame Frame;
typedef struct StringExtract StringExtract;
typedef struct CompoundExtract CompoundExtract;

typedef uint64_t DefID;
typedef uint64_t TypeID;
typedef uint64_t FuncID;
typedef uint64_t ExprID;
typedef uint64_t TypeID;
typedef uint64_t ValueID;
typedef uint64_t IntStr;

// VM creation/destruction:
VM* vm_create();
void vm_destroy(VM* vm);

// string interning:
IntStr vm_intern(VM* vm, char const* name);

// function declaration, defining funcs using expressions:
FuncID vm_declare_fn(VM* vm, DefID def_id);
void vm_define_fn(VM* vm, FuncID func_id, ExprID expr_id);


// expressions: lazy-functional-encoding of the language: bound to funcs as definitions.
//  - chains are factored into `let ... in ...` expressions.
//  - discard maps to eval_in, just `let _ = expr in ...` where `_` is discarded.
// NOTE: expressions are strings: written instructions for how to compute a value from other values (IDs)
// NOTE: expressions are 'analysis capable' <=> we can query side-effects-specifier IF expression context-free.

// atoms:
ExprID vm_mk_id_expr(VM* vm, DefID def_id);
ExprID vm_mk_unit_expr(VM* vm);
ExprID vm_mk_literal_int_expr(VM* vm, int64_t s, int width_in_bytes, bool is_signed);
ExprID vm_mk_literal_float_expr(VM* vm, double f);
ExprID vm_mk_literal_string_expr(VM* vm, uint64_t length, char const* bytes);
ExprID vm_mk_literal_array_expr(VM* vm, uint64_t length, ExprID const* element_expr_id_array);
ExprID vm_mk_literal_tuple_expr(VM* vm, uint64_t length, ExprID const* element_expr_id_array);
ExprID vm_mk_sizeof_expr(VM* vm, TypeID type_expr);
// complex (1):
ExprID vm_mk_if_expr(VM* vm, ExprID cond_expr_id, ExprID then_expr_id, ExprID else_expr_id);
ExprID vm_mk_call_expr(VM* vm, ExprID fn_expr_id, ExprID arg_expr_id, bool allow_non_tot);
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
// complex (2):
ExprID vm_mk_eval_in_expr(VM* vm, ExprID discarded_expr, ExprID in_expr);
ExprID vm_mk_let_in_expr(VM* vm, DefID def_id, ExprID init_expr, ExprID in_expr);

// evaluation: turns expressions into values.
ValueID vm_evaluate(ExprID expr_id);
ValueKind vm_value_kind(ValueID value_id);
uint64_t vm_extract_uint(ValueID value_id);
int64_t vm_extract_int(ValueID value_id);
double vm_extract_float(ValueID value_id);
StringExtract vm_extract_string(ValueID value_id);
CompoundExtract vm_extract_array(ValueID value_id);
CompoundExtract vm_extract_tuple(ValueID value_id);
CompoundExtract vm_extract_struct(ValueID value_id);
// todo: how to extract unions?
TypeID vm_extract_tid(ValueID value_id);

//
//
// Inline Type Definitions:
//
//

struct StringExtract {
    char const* bytes;
    uint64_t count;
};
struct CompoundExtract {
    ValueID* items;
    uint64_t items_count;
};
