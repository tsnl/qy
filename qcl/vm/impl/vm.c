#include "vm.h"

#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <assert.h>

#include "table.h"
#include "expr.h"
#include "rtti.h"
#include "func.h"

//
// VM type definitions:
//

struct VM {
    TABLE(Expr)* expr_tab;
    TABLE(Func)* func_tab;
    RttiManager* rtti_mgr;
};

//
// VM management:
//

VM* vm_create() {
    VM* vm = malloc(sizeof(VM));
    vm->expr_tab = expr_tab_init();
    return vm;
}
void vm_destroy(VM* vm) {
    expr_tab_destroy(vm->expr_tab);
    free(vm);
}

//
// VM function management
//

FuncID vm_declare_fn(VM* vm, DefID opt_def_id) {
    
}
void vm_define_fn(VM* vm, FuncID func_id, ExprID expr_id) {

}
// todo: devise a way to substitute/alter polymorphic functions

//
// VM expr construction:
//

ExprID vm_mk_id_expr(VM* vm, DefID def_id) {
    return expr_tab_new_id(vm->expr_tab, def_id);
}
ExprID vm_mk_unit_expr(VM* vm) {
    return expr_tab_new_simplest(vm->expr_tab, VAL_UNIT);
}
ExprID vm_mk_literal_int_expr(VM* vm, uint64_t raw_val, size_t width_in_bytes, bool is_signed) {    
    return expr_tab_new_int_literal(vm->expr_tab, raw_val, width_in_bytes, is_signed);
}
ExprID vm_mk_literal_float_expr(VM* vm, double f, size_t width_in_bytes) {
    return expr_tab_new_float_literal(vm->expr_tab, f, width_in_bytes);
}
ExprID vm_mk_literal_string_expr(VM* vm, uint64_t bytes_count, char const* bytes) {
    return expr_tab_new_string_literal(vm->expr_tab, bytes, bytes_count);
}
ExprID vm_mk_literal_array_expr(VM* vm, uint64_t length, ExprID const* element_expr_id_array) {
    return expr_tab_new_collection(vm->expr_tab, EXPR_ARRAY, element_expr_id_array, length);
}
ExprID vm_mk_literal_tuple_expr(VM* vm, uint64_t length, ExprID const* element_expr_id_array) {
    return expr_tab_new_collection(vm->expr_tab, EXPR_TUPLE, element_expr_id_array, length);
}
ExprID vm_mk_sizeof_expr(VM* vm, RtTypeID rttid) {
    return expr_tab_new_sizeof(vm->expr_tab, rttid);
}
ExprID vm_mk_if_expr(VM* vm, ExprID cond_expr_id, ExprID then_expr_id, ExprID else_expr_id) {
    return expr_tab_new_ite(vm->expr_tab, cond_expr_id, then_expr_id, else_expr_id);
}
ExprID vm_mk_call1_expr(VM* vm, ExprID fn_expr_id, ExprID arg_expr_id, bool allow_non_tot) {
    return expr_tab_new_call(
        vm->expr_tab, fn_expr_id, arg_expr_id,
        0, NULL,
        0, NULL
    );
}
ExprID vm_mk_call2_expr(
    VM* vm, ExprID fn_expr_id, ExprID arg_expr_id, bool allow_non_tot,
    size_t template_val_arg_count, ExprID* mv_template_val_args,
    size_t template_type_arg_count, RtTypeID* mv_template_type_args
) {
    return expr_tab_new_call(
        vm->expr_tab, fn_expr_id, arg_expr_id,
        template_val_arg_count, mv_template_val_args,
        template_type_arg_count, mv_template_type_args
    );
}
ExprID vm_mk_bao_expr(VM* vm, BinaryArithmeticOperator bao, ExprID lhs_arg_expr, ExprID rhs_arg_expr) {
    ExprKind expr_kind;
    switch (bao) {
        case BAO_POW: { expr_kind = EXPR_BAO_POW; } break;
        case BAO_MUL: { expr_kind = EXPR_BAO_MUL; } break;
        case BAO_DIV: { expr_kind = EXPR_BAO_DIV; } break;
        case BAO_REM: { expr_kind = EXPR_BAO_REM; } break;
        case BAO_ADD: { expr_kind = EXPR_BAO_ADD; } break;
        case BAO_SUB: { expr_kind = EXPR_BAO_SUB; } break;
        default: {
            assert(0 && "Invalid BAO op");
        }
    }
    return expr_tab_new_bao(vm->expr_tab, expr_kind, lhs_arg_expr, rhs_arg_expr);
}
ExprID vm_mk_cmp_expr(VM* vm, BinaryComparisonOperator bco, ExprID lhs_arg_expr, ExprID rhs_arg_expr) {
    ExprKind expr_kind;
    switch (bco) {
        case CMP_LT: { expr_kind = EXPR_CMP_LT; } break;
        case CMP_GT: { expr_kind = EXPR_CMP_GT; } break;
        case CMP_LE: { expr_kind = EXPR_CMP_LE; } break;
        case CMP_GE: { expr_kind = EXPR_CMP_GE; } break;
        default: {
            assert(0 && "Invalid CMP op");
        }
    }
    return expr_tab_new_cmp(vm->expr_tab, expr_kind, lhs_arg_expr, rhs_arg_expr);
}
ExprID vm_mk_alloc_1_expr(VM* vm, Allocator allocator, ExprID stored_value) {
    return expr_tab_new_alloc_1(vm->expr_tab, allocator, stored_value);
}
ExprID vm_mk_alloc_n_expr(VM* vm, Allocator allocator, ExprID count, ExprID elem_size) {
    return expr_tab_new_alloc_n(vm->expr_tab, allocator, count, elem_size);
}
ExprID vm_mk_deref_expr(VM* vm, ExprID ptr_expr) {
    return expr_tab_new_deref(vm->expr_tab, ptr_expr);
}
ExprID vm_mk_assign_expr(VM* vm, ExprID ptr_expr, ExprID assigned_expr) {
    return expr_tab_new_assign(vm->expr_tab, ptr_expr, assigned_expr);
}
ExprID vm_mk_get_tuple_elem_expr(VM* vm, ExprID container_expr, ExprID element_index) {
    ExprID elem_ptr = expr_tab_new_gep(vm->expr_tab, container_expr, element_index);
    return vm_mk_deref_expr(vm, elem_ptr);
}
ExprID vm_mk_get_tuple_ptr_elem_ptr_expr(VM* vm, ExprID container_expr_ptr_id, ExprID element_index) {
    ExprID tuple = vm_mk_deref_expr(vm, container_expr_ptr_id);
    return expr_tab_new_gep(vm->expr_tab, container_expr_ptr_id, element_index);
}
ExprID vm_mk_get_adt_elem_expr(VM* vm, ExprID container_expr, ExprID element_index) {
    ExprID elem_ptr = expr_tab_new_gep(vm->expr_tab, container_expr, element_index);
    return vm_mk_deref_expr(vm, elem_ptr);
}
ExprID vm_mk_get_adt_ptr_elem_ptr_expr(VM* vm, ExprID container_expr_ptr_id, ExprID element_index) {
    ExprID tuple = vm_mk_deref_expr(vm, container_expr_ptr_id);
    return expr_tab_new_gep(vm->expr_tab, container_expr_ptr_id, element_index);
}
ExprID vm_mk_get_list_item_ptr_expr(VM* vm, ExprID array, ExprID index) {
    return expr_tab_new_gep(vm->expr_tab, array, index);
}
ExprID vm_mk_eval_in_expr(VM* vm, ExprID discarded_expr, ExprID in_expr) {
    return expr_tab_new_let_in(vm->expr_tab, NULL_DEF_ID, discarded_expr, in_expr);
}
ExprID vm_mk_let_in_expr(VM* vm, DefID def_id, ExprID init_expr, ExprID in_expr) {
    return expr_tab_new_let_in(vm->expr_tab, def_id, init_expr, in_expr);
}

//
// VM evaluation:
//

Const vm_evaluate_value(VM* vm, ExprID expr_id) {
    Expr* e = expr(vm->expr_tab, expr_id);
    switch (e->kind) {
        case EXPR_UNIT: {

        } break;

        case EXPR_UINT: {

        } break;

        case EXPR_SINT: {

        } break;

        case EXPR_FLOAT: {

        } break;

        case EXPR_STRING: {

        } break;

        default: {
            assert(0 && "Unknown expression to evaluate");
        } break;
    }
    // todo: create a root eval-frame and start evaluating symbols in it.
    // todo: devise a way to initialize global constants.
}

RtTypeID vm_evaluate_rttid(ExprID expr_id) {

}
