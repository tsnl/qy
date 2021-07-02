#pragma once

#include <stdbool.h>

#include "core.h"
#include "table.h"
#include "rtti.h"
#include "defs.h"

typedef union ExprData ExprData;
typedef enum ExprKind ExprKind;
typedef struct Expr Expr;
typedef size_t ExprID;

Table* expr_tab_init();
void expr_tab_destroy(Table* table);

Expr* expr_tab_get_expr(Table* table, ExprID id);

ExprID expr_tab_new_id(Table* table, DefID def_id);
ExprID expr_tab_new_simplest(Table* table, ExprKind kind);
ExprID expr_tab_new_int_literal(Table* table, uint64_t value, int width_in_bytes, bool is_signed);
ExprID expr_tab_new_float_literal(Table* table, double value, int width_in_bytes);
ExprID expr_tab_new_collection(Table* table, ExprKind kind, ExprID* items, size_t item_count);
ExprID expr_tab_new_sizeof(Table* table, RtTypeID tid);
ExprID expr_tab_new_ite(Table* table, ExprID cond_expr_id, ExprID then_expr_id, ExprID else_expr_id);
ExprID expr_tab_new_call(Table* table, ExprID func_expr_id, ExprID arg_expr_id);
ExprID expr_tab_new_bao(Table* table, ExprKind kind, ExprID lhs_arg_expr_id, ExprID rhs_arg_expr_id);
ExprID expr_tab_new_cmp(Table* table, ExprKind kind, ExprID lhs_arg_expr_id, ExprID rhs_arg_expr_id);
ExprID expr_tab_new_alloc_1(Table* table, Allocator allocator, ExprID stored_value);
ExprID expr_tab_new_alloc_n(Table* table, Allocator allocator, ExprID count, ExprID elem_size);
ExprID expr_tab_new_deref(Table* table, ExprID pointer_expr_id);
ExprID expr_tab_new_assign(Table* table, ExprID dst_ptr_expr_id, ExprID src_expr_id);
ExprID expr_tab_new_gep(Table* table, ExprID container_expr_id, ExprID index_expr_id);
ExprID expr_tab_new_let_in(Table* table, DefID def_id, ExprID init_expr_id, ExprID in_expr_id);
ExprID expr_tab_new_discard_in(Table* table, ExprID init_expr_id, ExprID in_expr_id);
