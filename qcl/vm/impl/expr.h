#pragma once

#include <stdbool.h>

#include "core.h"
#include "table.h"
#include "rtti.h"
#include "consts.h"

typedef union ExprData ExprData;
typedef enum ExprKind ExprKind;
typedef struct Expr Expr;

#define NULL_EXPR_ID ((ExprID)0)

TABLE(Expr)* expr_tab_init();
void expr_tab_destroy(TABLE(Expr)* table);

ExprID expr_tab_new_id(TABLE(Expr)* table, DefID def_id);
ExprID expr_tab_new_simplest(TABLE(Expr)* table, ExprKind kind);
ExprID expr_tab_new_int_literal(TABLE(Expr)* table, uint64_t value, size_t width_in_bytes, bool is_signed);
ExprID expr_tab_new_float_literal(TABLE(Expr)* table, double value, size_t width_in_bytes);
ExprID expr_tab_new_string_literal(TABLE(Expr)* table, char const* bytes, size_t bytes_count);
ExprID expr_tab_new_collection(TABLE(Expr)* table, ExprKind kind, ExprID const* items, size_t item_count);
ExprID expr_tab_new_sizeof(TABLE(Expr)* table, RtTypeID tid);
ExprID expr_tab_new_ite(TABLE(Expr)* table, ExprID cond_expr_id, ExprID then_expr_id, ExprID else_expr_id);
ExprID expr_tab_new_call(
    TABLE(Expr)* table, ExprID func_expr_id, ExprID arg_expr_id, 
    size_t val_template_count, ExprID* val_args,
    size_t type_template_count, RtTypeID* type_args
);
ExprID expr_tab_new_bao(TABLE(Expr)* table, ExprKind kind, ExprID lhs_arg_expr_id, ExprID rhs_arg_expr_id);
ExprID expr_tab_new_cmp(TABLE(Expr)* table, ExprKind kind, ExprID lhs_arg_expr_id, ExprID rhs_arg_expr_id);
ExprID expr_tab_new_alloc_1(TABLE(Expr)* table, Allocator allocator, ExprID stored_value);
ExprID expr_tab_new_alloc_n(TABLE(Expr)* table, Allocator allocator, ExprID count, ExprID elem_size);
ExprID expr_tab_new_deref(TABLE(Expr)* table, ExprID pointer_expr_id);
ExprID expr_tab_new_assign(TABLE(Expr)* table, ExprID dst_ptr_expr_id, ExprID src_expr_id);
ExprID expr_tab_new_gep(TABLE(Expr)* table, ExprID container_expr_id, ExprID index_expr_id);
ExprID expr_tab_new_let_in(TABLE(Expr)* table, DefID def_id, ExprID init_expr_id, ExprID in_expr_id);
ExprID expr_tab_new_discard_in(TABLE(Expr)* table, ExprID init_expr_id, ExprID in_expr_id);

Expr* expr(TABLE(Expr)* table, ExprID expr_id);

//
//
// Inline type definitions:
//
//

typedef struct ActualTemplateArgs ActualTemplateArgs;
struct ActualTemplateArgs {
    size_t val_count;
    Const* val_args;
    size_t type_count;
    RtTypeID* type_args;
};

enum ExprKind {
    EXPR_UNIT, EXPR_STRING,
    EXPR_UINT, EXPR_SINT, EXPR_FLOAT,
    EXPR_ARRAY, EXPR_TUPLE,
    EXPR_IF,
    EXPR_CALL,
    EXPR_BAO_POW,
    EXPR_BAO_MUL, EXPR_BAO_DIV, EXPR_BAO_REM,
    EXPR_BAO_ADD, EXPR_BAO_SUB,
    EXPR_CMP_LT, EXPR_CMP_GT,
    EXPR_CMP_LE, EXPR_CMP_GE,
    EXPR_CMP_EQ, EXPR_CMP_NE,
    EXPR_ALLOC_1,
    EXPR_ALLOC_N,
    EXPR_DEREF,
    EXPR_SIZEOF,
    EXPR_ASSIGN,
    EXPR_GEP,
    EXPR_LET_IN, EXPR_DISCARD_IN
};

union ExprData {
    struct {
        DefID def_id;
    } id;
    
    struct {
        uint64_t value;
        size_t width_in_bytes;
    } u_int;

    struct {
        int64_t value;
        size_t width_in_bytes;
    } s_int;

    struct {
        double value;
        size_t width_in_bytes;
    } float_;

    struct {
        char const* ptr;
        size_t      len;
    } str_literal;

    struct {
        ExprID const* items;
        size_t  count;
    } collection;   // array, tuple

    struct {
        RtTypeID tid;
    } sizeof_;

    struct {
        ExprID cond_expr_id;
        ExprID then_expr_id;
        ExprID else_expr_id;
    } ite;

    struct {
        ExprID fn_expr_id;
        ExprID arg_expr_id;
        ActualTemplateArgs* opt_template_args;
    } call;

    struct {
        ExprID lhs_arg_expr_id;
        ExprID rhs_arg_expr_id;
    } bao;

    struct {
        ExprID lhs_arg_expr_id;
        ExprID rhs_arg_expr_id;
    } cmp;

    struct {
        ExprID stored_value_expr_id;
        Allocator allocator;
    } alloc_1;

    struct {
        ExprID count_expr_id;
        ExprID elem_size_expr_id;
        Allocator allocator;
    } alloc_n;

    struct {
        ExprID ptr_expr_id;
    } deref;

    struct {
        ExprID dst_expr_id;
        ExprID src_expr_id;
    } assign;

    struct {
        ExprID tuple_expr_id;
        ExprID index_expr_id;
    } get_elem_ptr;

    struct {
        ExprID discarded_expr_id;
        ExprID in_expr_id;
    } discard;

    struct {
        DefID def_id;
        ExprID init_expr_id;
        ExprID in_expr_id;
    } let_in;
};

struct Expr {
    ExprKind kind;
    ExprData data;
};

//
// TODO: allow `call` to accept template arguments, which are cached by the `func` module.
//
