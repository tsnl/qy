#include "expr.h"

#include <assert.h>
#include <stdlib.h>

#include "core.h"

//
//
// Expression definitions:
//
//

Table* expr_tab_init() {
    size_t cache_line_size = 64;
    size_t max_expr_count = 8192;
    size_t expr_per_block_count = cache_line_size / sizeof(Expr);
    size_t max_block_count = max_expr_count / expr_per_block_count;

    return tab_new(
        sizeof(Expr),
        expr_per_block_count, max_block_count
    );
}

void expr_tab_destroy(Table* table) {
    tab_del(table);
}

ExprID mint_partial_expr(Table* table, ExprKind kind) {
    size_t new_ix = tab_append(table);
    Expr* ep = tab_gp(table, new_ix);
    ep->kind = kind;
    return 1 + new_ix;
}

ExprID expr_tab_new_id(Table* table, DefID def_id) {
    // todo: implement me
    assert(0 && "NotImplemented");
}

ExprID expr_tab_new_simplest(Table* table, ExprKind kind) {
    assert(
        kind == EXPR_UNIT ||
        kind == EXPR_STRING
    );
    ExprID id = mint_partial_expr(table, kind);
    return id;
}

ExprID expr_tab_new_int_literal(Table* table, uint64_t value, size_t width_in_bytes, bool is_signed) {
    if (is_signed) {
        ExprID eid = mint_partial_expr(table, EXPR_SINT);
        Expr* e = expr(table, eid);
        e->data.s_int.value = (int64_t) value;
        e->data.s_int.width_in_bytes = width_in_bytes;
        return eid;
    } else {
        ExprID eid = mint_partial_expr(table, EXPR_UINT);
        Expr* e = expr(table, eid);
        e->data.u_int.value = value;
        e->data.u_int.width_in_bytes = width_in_bytes;
        return eid;
    }
}

ExprID expr_tab_new_float_literal(Table* table, double value, size_t width_in_bytes) {
    ExprID eid = mint_partial_expr(table, EXPR_FLOAT);
    Expr* e = expr(table, eid);
    e->data.float_.value = value;
    e->data.float_.width_in_bytes = width_in_bytes;
    return eid;
}

ExprID expr_tab_new_string_literal(Table* table, char const* bytes, size_t bytes_count) {
    ExprID eid = mint_partial_expr(table, EXPR_STRING);
    Expr* e = expr(table, eid);
    e->data.str_literal.ptr = bytes;
    e->data.str_literal.len = bytes_count;
    return eid;
}

ExprID expr_tab_new_collection(Table* table, ExprKind kind, ExprID const* items, size_t item_count) {
    ExprID eid = mint_partial_expr(table, kind);
    Expr* e = expr(table, eid);
    e->data.collection.count = item_count;
    e->data.collection.items = items;
    return eid;
}

ExprID expr_tab_new_sizeof(Table* table, RtTypeID tid) {
    ExprID eid = mint_partial_expr(table, EXPR_SIZEOF);
    Expr* e = expr(table, eid);
    e->data.sizeof_.tid = tid;
    return eid;
}

ExprID expr_tab_new_ite(Table* table, ExprID cond_expr_id, ExprID then_expr_id, ExprID else_expr_id) {
    ExprID eid = mint_partial_expr(table, EXPR_IF);
    Expr* e = expr(table, eid);
    e->data.ite.cond_expr_id = cond_expr_id;
    e->data.ite.then_expr_id = then_expr_id;
    e->data.ite.else_expr_id = else_expr_id;
    return eid;
}

ExprID expr_tab_new_call(
    TABLE(Expr)* table, ExprID func_expr_id, ExprID arg_expr_id, 
    size_t val_template_count, ExprID* val_args,
    size_t type_template_count, RtTypeID* type_args
) {
    ExprID eid = mint_partial_expr(table, EXPR_CALL);
    Expr* e = expr(table, eid);
    e->data.call.fn_expr_id = func_expr_id;
    e->data.call.arg_expr_id = arg_expr_id;
    
    // e->data.call.opt_template_args; 
    if (val_template_count == 0 && type_template_count == 0) {
        e->data.call.opt_template_args = NULL;
    } else {
        ActualTemplateArgs* p = malloc(sizeof(ActualTemplateArgs));
        {
            p->type_args = type_args;
            p->type_count = type_template_count;
            p->val_args = val_args;
            p->val_count = val_template_count;
        }
        e->data.call.opt_template_args = p;
    }
    return eid;
}

ExprID expr_tab_new_bao(Table* table, ExprKind kind, ExprID lhs_arg_expr_id, ExprID rhs_arg_expr_id) {
    ExprID eid = mint_partial_expr(table, kind);
    Expr* e = expr(table, eid);
    e->data.bao.lhs_arg_expr_id = lhs_arg_expr_id;
    e->data.bao.rhs_arg_expr_id = rhs_arg_expr_id;
    return eid;
}

ExprID expr_tab_new_cmp(Table* table, ExprKind kind, ExprID lhs_arg_expr_id, ExprID rhs_arg_expr_id) {
    ExprID eid = mint_partial_expr(table, kind);
    Expr* e = expr(table, eid);
    e->data.cmp.lhs_arg_expr_id = lhs_arg_expr_id;
    e->data.cmp.rhs_arg_expr_id = rhs_arg_expr_id;
    return eid;
}

ExprID expr_tab_new_alloc_1(Table* table, Allocator allocator, ExprID stored_value_expr_id) {
    ExprID eid = mint_partial_expr(table, EXPR_ALLOC_1);
    Expr* e = expr(table, eid);
    e->data.alloc_1.allocator = allocator;
    e->data.alloc_1.stored_value_expr_id = stored_value_expr_id;
}

ExprID expr_tab_new_alloc_n(Table* table, Allocator allocator, ExprID count_expr_id, ExprID elem_size_expr_id) {
    ExprID eid = mint_partial_expr(table, EXPR_ALLOC_N);
    Expr* e = expr(table, eid);
    e->data.alloc_n.allocator = allocator;
    e->data.alloc_n.count_expr_id = count_expr_id;
    e->data.alloc_n.elem_size_expr_id = elem_size_expr_id;
    return eid;
}

ExprID expr_tab_new_deref(Table* table, ExprID pointer_expr_id) {
    ExprID eid = mint_partial_expr(table, EXPR_DEREF);
    Expr* e = expr(table, eid);
    e->data.deref.ptr_expr_id = pointer_expr_id;
    return eid;
}

ExprID expr_tab_new_assign(Table* table, ExprID dst_ptr_expr_id, ExprID src_expr_id) {
    ExprID eid = mint_partial_expr(table, EXPR_ASSIGN);
    Expr* e = expr(table, eid);
    e->data.assign.dst_expr_id = dst_ptr_expr_id;
    e->data.assign.src_expr_id = src_expr_id;
    return eid;
}

ExprID expr_tab_new_gep(Table* table, ExprID container_expr_id, ExprID index_expr_id) {
    ExprID eid = mint_partial_expr(table, EXPR_GEP);
    Expr* e = expr(table, eid);
    e->data.get_elem_ptr.tuple_expr_id = container_expr_id;
    e->data.get_elem_ptr.index_expr_id = index_expr_id;
    return eid;
}

ExprID expr_tab_new_let_in(Table* table, DefID def_id, ExprID init_expr_id, ExprID in_expr_id) {
    ExprID eid = mint_partial_expr(table, EXPR_DISCARD_IN);
    Expr* e = expr(table, eid);
    e->data.let_in.def_id = def_id;
    e->data.let_in.init_expr_id = init_expr_id;
    e->data.let_in.in_expr_id = in_expr_id;
    return eid;
}

ExprID expr_tab_new_discard_in(Table* table, ExprID init_expr_id, ExprID in_expr_id) {
    ExprID eid = mint_partial_expr(table, EXPR_DISCARD_IN);
    Expr* e = expr(table, eid);
    e->data.discard.discarded_expr_id = init_expr_id;
    e->data.discard.in_expr_id = in_expr_id;
    return eid;
}

Expr* expr(Table* table, ExprID expr_id) {
    return expr(table, expr_id - 1);
}
