#include "expr.h"

#include <assert.h>
#include <stdlib.h>

#include "core.h"

//
//
// Type definitions:
//
//

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
    
    uint8_t u8_literal;
    uint16_t u16_literal;
    uint32_t u32_literal;
    uint64_t u64_literal;

    int8_t s8_literal;
    int16_t s16_literal;
    int32_t s32_literal;
    int64_t s64_literal;

    float f32_literal;
    double f64_literal;

    struct {
        char const* ptr;
        size_t      len;
    } str_literal;

    struct {
        ExprID* items;
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

ExprID help_append_expr(Table* table, ExprKind kind) {
    size_t new_ix = tab_append(table);
    Expr* ep = tab_gp(table, new_ix);
    ep->kind = kind;
    return new_ix;
}

Expr* expr_tab_get_expr(Table* table, ExprID id) {
    Expr* ep = tab_gp(table, id);
    return ep;
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
    ExprID id = help_append_expr(table, kind);
    return id;
}

ExprID expr_tab_new_int_literal(Table* table, uint64_t value, int width_in_bytes, bool is_signed) {
    if (is_signed) {
        ExprID eid = help_append_expr(table, EXPR_SINT);
        Expr* e = tab_gp(table, eid);
        switch (width_in_bytes) {
            case 1: {
                e->data.s8_literal = (int8_t)value;
            } break;
            case 2: {
                e->data.s16_literal = (int16_t)value;
            } break;
            case 4: {
                e->data.s32_literal = (int32_t)value;
            } break;
            case 8: {
                e->data.s64_literal = (int64_t)value;
            } break;
            default: {
                assert(0 && "EXPR: Invalid signed int width in bytes");
            } break;
        }
        return eid;
    } else {
        ExprID eid = help_append_expr(table, EXPR_SINT);
        Expr* e = tab_gp(table, eid);
        switch (width_in_bytes) {
            case 1: {
                e->data.u8_literal = (uint8_t)value;
            } break;
            case 2: {
                e->data.u16_literal = (uint16_t)value;
            } break;
            case 4: {
                e->data.u32_literal = (uint32_t)value;
            } break;
            case 8: {
                e->data.u64_literal = (uint64_t)value;
            } break;
            default: {
                assert(0 && "EXPR: Invalid unsigned int width in bytes");
            } break;
        }
        return eid;
    }
}

ExprID expr_tab_new_float_literal(Table* table, double value, int width_in_bytes) {
    ExprID eid = help_append_expr(table, EXPR_FLOAT);
    Expr* e = tab_gp(table, eid);
    switch (width_in_bytes) {
        case 4: {
            e->data.f32_literal = (float)value;
        } break;
        case 8: {
            e->data.f64_literal = value;
        } break;
        default: {
            assert(0 && "EXPR: Invalid float width in bytes");
        } break;
    }
    return eid;
}

ExprID expr_tab_new_collection(Table* table, ExprKind kind, ExprID* items, size_t item_count) {
    ExprID eid = help_append_expr(table, kind);
    Expr* e = tab_gp(table, eid);
    e->data.collection.count = item_count;
    e->data.collection.items = items;
    return eid;
}

ExprID expr_tab_new_sizeof(Table* table, RtTypeID tid) {
    ExprID eid = help_append_expr(table, EXPR_SIZEOF);
    Expr* e = tab_gp(table, eid);
    e->data.sizeof_.tid = tid;
    return eid;
}

ExprID expr_tab_new_ite(Table* table, ExprID cond_expr_id, ExprID then_expr_id, ExprID else_expr_id) {
    ExprID eid = help_append_expr(table, EXPR_IF);
    Expr* e = tab_gp(table, eid);
    e->data.ite.cond_expr_id = cond_expr_id;
    e->data.ite.then_expr_id = then_expr_id;
    e->data.ite.else_expr_id = else_expr_id;
    return eid;
}

ExprID expr_tab_new_call(Table* table, ExprID func_expr_id, ExprID arg_expr_id) {
    ExprID eid = help_append_expr(table, EXPR_CALL);
    Expr* e = tab_gp(table, eid);
    e->data.call.fn_expr_id = func_expr_id;
    e->data.call.arg_expr_id = arg_expr_id;
    return eid;
}

ExprID expr_tab_new_bao(Table* table, ExprKind kind, ExprID lhs_arg_expr_id, ExprID rhs_arg_expr_id) {
    ExprID eid = help_append_expr(table, kind);
    Expr* e = tab_gp(table, eid);
    e->data.bao.lhs_arg_expr_id = lhs_arg_expr_id;
    e->data.bao.rhs_arg_expr_id = rhs_arg_expr_id;
    return eid;
}

ExprID expr_tab_new_cmp(Table* table, ExprKind kind, ExprID lhs_arg_expr_id, ExprID rhs_arg_expr_id) {
    ExprID eid = help_append_expr(table, kind);
    Expr* e = tab_gp(table, eid);
    e->data.cmp.lhs_arg_expr_id = lhs_arg_expr_id;
    e->data.cmp.rhs_arg_expr_id = rhs_arg_expr_id;
    return eid;
}

ExprID expr_tab_new_alloc_1(Table* table, Allocator allocator, ExprID stored_value_expr_id) {
    ExprID eid = help_append_expr(table, EXPR_ALLOC_1);
    Expr* e = tab_gp(table, eid);
    e->data.alloc_1.allocator = allocator;
    e->data.alloc_1.stored_value_expr_id = stored_value_expr_id;
}

ExprID expr_tab_new_alloc_n(Table* table, Allocator allocator, ExprID count_expr_id, ExprID elem_size_expr_id) {
    ExprID eid = help_append_expr(table, EXPR_ALLOC_N);
    Expr* e = tab_gp(table, eid);
    e->data.alloc_n.allocator = allocator;
    e->data.alloc_n.count_expr_id = count_expr_id;
    e->data.alloc_n.elem_size_expr_id = elem_size_expr_id;
    return eid;
}

ExprID expr_tab_new_deref(Table* table, ExprID pointer_expr_id) {
    ExprID eid = help_append_expr(table, EXPR_DEREF);
    Expr* e = tab_gp(table, eid);
    e->data.deref.ptr_expr_id = pointer_expr_id;
    return eid;
}

ExprID expr_tab_new_assign(Table* table, ExprID dst_ptr_expr_id, ExprID src_expr_id) {
    ExprID eid = help_append_expr(table, EXPR_ASSIGN);
    Expr* e = tab_gp(table, eid);
    e->data.assign.dst_expr_id = dst_ptr_expr_id;
    e->data.assign.src_expr_id = src_expr_id;
    return eid;
}

ExprID expr_tab_new_gep(Table* table, ExprID container_expr_id, ExprID index_expr_id) {
    ExprID eid = help_append_expr(table, EXPR_GEP);
    Expr* e = tab_gp(table, eid);
    e->data.get_elem_ptr.tuple_expr_id = container_expr_id;
    e->data.get_elem_ptr.index_expr_id = index_expr_id;
    return eid;
}

ExprID expr_tab_new_let_in(Table* table, DefID def_id, ExprID init_expr_id, ExprID in_expr_id) {
    ExprID eid = help_append_expr(table, EXPR_DISCARD_IN);
    Expr* e = tab_gp(table, eid);
    e->data.let_in.def_id = def_id;
    e->data.let_in.init_expr_id = init_expr_id;
    e->data.let_in.in_expr_id = in_expr_id;
    return eid;
}

ExprID expr_tab_new_discard_in(Table* table, ExprID init_expr_id, ExprID in_expr_id) {
    ExprID eid = help_append_expr(table, EXPR_DISCARD_IN);
    Expr* e = tab_gp(table, eid);
    e->data.discard.discarded_expr_id = init_expr_id;
    e->data.discard.in_expr_id = in_expr_id;
    return eid;
}