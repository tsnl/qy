#pragma once

#include <stdint.h>
#include <stdbool.h>

typedef struct VM VM;
typedef struct Frame Frame;
typedef struct StringExtract StringExtract;
typedef struct CompoundExtract CompoundExtract;
typedef enum BinaryArithmeticOperator BinaryArithmeticOperator;

typedef uint64_t DefID;
typedef uint64_t TypeID;
typedef uint64_t FuncID;
typedef uint64_t ExprID;
typedef uint64_t TypeID;
typedef uint64_t ValueID;
typedef uint64_t IntStr;

enum BinaryArithmeticOperator {
    BAO_MUL, BAO_DIV, BAO_REM,
    BAO_ADD, BAO_SUB
};
enum BinaryComparisonOperator {
    CMP_LT, CMP_GT,
    CMP_LE, CMP_GE,
    CMP_EQ, CMP_NE
};
enum Allocator {
    ALLOCATOR_STACK,
    ALLOCATOR_HEAP
};
enum AdtKind {
    ADT_STRUCT,
    ADT_ENUM
};
enum ValueKind {
    VAL_UNIT, VAL_STRING,
    VAL_UINT, VAL_SINT, VAL_FLOAT,
    VAL_ARRAY, VAL_SLICE,
    VAL_STRUCT, VAL_UNION
};

// VM creation/destruction:
VM* vm_create();
void vm_destroy(VM* vm);

// string interning:
IntStr vm_intern(VM* vm, char const* name);

// function declaration, defining funcs using expressions:
FuncID vm_declare_fn(DefID def_id);
void vm_define_fn(FuncID func_id, ExprID expr_id);

// rtti: run-time type info: mapped into existence by the 'inference' system.
void vm_map_unit_tid(TypeID unit_tid);
void vm_map_int_tid(TypeID sint_tid, uint8_t width_in_bits, bool is_signed);
void vm_map_float_tid(TypeID float_tid, uint8_t width_in_bits);
void vm_map_string_tid(TypeID string_tid);
void vm_map_tuple_tid(TypeID tuple_tid, uint64_t tuple_count, TypeID* elem_tids);
void vm_map_ptr_tid(TypeID pointee_tid, bool is_mut);
void vm_map_array_tid(TypeID array_tid, TypeID elem_tid, bool is_mut);
void vm_map_slice_tid(TypeID slice_tid, TypeID elem_tid, bool is_mut);
void vm_map_adt_tid(TypeID struct_tid, AdtKind adt_kind, uint64_t count, TypeID* elem_tid_list);

// expressions: lazy-functional-encoding of the language: bound to funcs as definitions.
//  - chains are factored into `let ... in ...` expressions.
//  - discard maps to `let _ = expr in ...` where `_` is discarded.
// NOTE: expressions are strings: written instructions for how to compute a value from other values (IDs)
// NOTE: expressions are 'analysis capable' <=> we can query side-effects-specifier IF expression context-free.
ExprID vm_mk_id_expr(DefID def_id);
ExprID vm_mk_let_in_expr(DefID def_id, ExprID init_expr);
ExprID vm_mk_literal_sint_expr(int64_t s);
ExprID vm_mk_literal_uint_expr(uint64_t u);
ExprID vm_mk_literal_float_expr(double f);
ExprID vm_mk_literal_string_expr(uint64_t length, char const* bytes);
ExprID vm_mk_literal_array_expr(uint64_t length, ExprID const* element_expr_id_array);
ExprID vm_mk_literal_tuple_expr(uint64_t length, ExprID const* element_expr_id_array);
ExprID vm_mk_if_expr(ExprID cond_expr_id, ExprID then_expr_id, ExprID else_expr_id);
ExprID vm_mk_call_expr(ExprID fn_expr_id, ExprID arg_expr_id, bool allow_non_tot);
ExprID vm_mk_bao_expr(BinaryArithmeticOperator bao, ExprID lhs_arg_expr, ExprID rhs_arg_expr);
ExprID vm_mk_cmp_expr(BinaryComparisonOperator bco, ExprID lhs_arg_expr, ExprID rhs_arg_expr);
ExprID vm_mk_alloc_1_expr(Allocator allocator, ExprID stored_value);
ExprID vm_mk_alloc_n_expr(Allocator allocator, ExprID count, ExprID elem_size);
ExprID vm_mk_deref_expr(ExprID ptr_expr);
ExprID vm_mk_sizeof_expr(TypeID type_expr);
ExprID vm_mk_assign_expr(ExprID ptr_expr, ExprID assigned_expr);
ExprID vm_mk_get_tuple_elem_expr(ExprID expr_id, ExprID element_index);
ExprID vm_mk_get_tuple_ptr_elem_ptr_expr(ExprID expr_id, ExprID element_index);
ExprID vm_mk_get_adt_elem_expr(ExprID expr_id, ExprID element_index);
ExprID vm_mk_get_adt_ptr_elem_ptr_expr(ExprID expr_id, ExprID element_index);
ExprID vm_mk_get_list_item_ptr_expr(ExprID array, ExprID index);

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
