#include "eval.hh"

#include <iostream>
#include <set>
#include <cmath>
#include <cassert>
#include <cstdint>

#include "mast.hh"
#include "panic.hh"
#include "sub.hh"
#include "gdef.hh"
#include "mtype.hh"
#include "mval.hh"
#include "mtype.hh"
#include "arg-list.hh"
#include "modules.hh"
#include "stack.hh"
#include "intern.hh"

//
// Implementation: forward declarations:
//

namespace monomorphizer::eval {

    using ssize_t = int64_t;

    //
    // FIXME: should 'ignore_gdef_id_set' be an argument to `eval_poly_?_impl`, which calls itself instead of `eval_poly_?`?
    //  - this detects cycles that occur from nested inter-dependent instantiations
    //  - otherwise, the program would hang
    //

    mast::TypeSpecID p2m_ts(mast::TypeSpecID ts_id, sub::Substitution* s, stack::Stack* st, std::set<GDefID>& ignore_gdef_id_set, MonoModID mono_mod_id);
    mast::ExpID p2m_exp(mast::ExpID exp_id, sub::Substitution* s, stack::Stack* st, std::set<GDefID>& ignore_gdef_id_set, MonoModID mono_mod_id);
    mast::ElemID p2m_elem(mast::ElemID elem_id, sub::Substitution* s, stack::Stack* st, std::set<GDefID>& ignore_gdef_id_set, MonoModID mono_mod_id);

    static mtype::TID eval_poly_ts_impl(mast::TypeSpecID poly_ts, sub::Substitution* s, stack::Stack* st, MonoModID mono_mod_id);
    static mval::VID eval_poly_exp_impl(mast::ExpID exp_id, sub::Substitution* s, stack::Stack* st, MonoModID mono_mod_id);

    static mtype::TID eval_poly_ts(mast::TypeSpecID poly_ts, sub::Substitution* s, MonoModID mono_mod_id);
    static mval::VID eval_poly_exp(mast::ExpID exp_id, sub::Substitution* s, MonoModID mono_mod_id);
    
    static mtype::TID eval_mono_ts(mast::TypeSpecID ts_id, stack::Stack* stack, MonoModID mono_mod_id);
    static mval::VID eval_mono_exp(mast::ExpID exp_id, stack::Stack* stack, MonoModID mono_mod_id);
    
}

//
// Implementation: p2m: polymorphic to monomorphic
//

namespace monomorphizer::eval {

    static arg_list::ArgListID arg_list_from_node_array(
        size_t arg_count,
        mast::NodeID* arg_array,
        sub::Substitution* s,
        stack::Stack* st,
        MonoModID mono_mod_id
    ) {
        arg_list::ArgListID actual_arg_list = arg_list::EMPTY_ARG_LIST;
        for (size_t i = 0; i < arg_count; i++) {
            auto arg_index = arg_count - (i + 1);
            auto arg_node_id = arg_array[arg_index];

            bool elem_is_exp = mast::is_node_exp_not_ts(arg_node_id);
            if (elem_is_exp) {
                auto elem_exp_id = arg_node_id;
                auto elem_exp_val = eval_poly_exp_impl(elem_exp_id, s, st, mono_mod_id);
                // std::cout << "INFO: arg_list_from_node_array: Inserting VID in list: " << elem_exp_val << std::endl;
                actual_arg_list = arg_list::cons_val(actual_arg_list, elem_exp_val);
            } else {
                auto elem_ts_id = arg_node_id;
                auto elem_ts_tid = eval_poly_ts_impl(elem_ts_id, s, st, mono_mod_id);
                // std::cout << "INFO: arg_list_from_node_array: Inserting TID in list: " << elem_ts_tid << std::endl;
                actual_arg_list = arg_list::cons_tid(actual_arg_list, elem_ts_tid);
            }
        }
        return actual_arg_list;
    }

    mast::TypeSpecID p2m_ts(
        mast::TypeSpecID mast_ts_id,
        sub::Substitution* s,
        stack::Stack* st,
        std::set<GDefID>& ignore_gdef_id_set,
        MonoModID mono_mod_id
    ) {
        // std::cout << "DEBUG: p2m_ts: sub is..." << std::endl;
        // sub::debug_print(s);

        auto ts_kind = mast::get_node_kind(mast_ts_id);
        switch (ts_kind) {
            case mast::TS_UNIT: 
            case mast::TS_LID: 
            {
                return mast_ts_id;
            }
            case mast::TS_GID: 
            {
                // This substitution may require us to rewrite this ID with another.
                auto info = mast::get_info_ptr(mast_ts_id)->ts_gid;
                GDefID old_def_id = info.def_id;
                gdef::DefKind old_def_kind = gdef::get_def_kind(old_def_id);
                switch (old_def_kind) {
                    case gdef::DefKind::CONST_TOT_TID:
                    {
                        // no substitution/copying possible: substitutions only replace BV_? or expressions/typespecs,
                        // neither of which is stored here.
                        // Hence, this operation is identity.
                        return mast_ts_id;
                    }
                    case gdef::DefKind::CONST_TS:
                    {
                        // must apply this substitution to the stored ID UNLESS in the ignore set:
                        auto found_tuple = ignore_gdef_id_set.insert(old_def_id);
                        if (found_tuple.second) {
                            // evaluating the nested expression:
                            mast::TypeSpecID old_target = gdef::get_def_target(old_def_id);
                            mast::TypeSpecID new_target = p2m_ts(old_target, s, st, ignore_gdef_id_set, mono_mod_id);
                            
                            // removing the gdef ID from the 'ignore' set and...
                            ignore_gdef_id_set.erase(old_def_id);

                            // ... promptly returning:
                            if (new_target != old_target) {
                                char* cp_name = strdup(gdef::get_def_name(old_def_id));
                                GDefID new_def_id = gdef::declare_global_def(gdef::DefKind::CONST_TS, cp_name);
                                gdef::set_def_target(new_def_id, new_target);
                                return mast::new_gid_ts(new_def_id);
                            } else {
                                return mast_ts_id;
                            }
                        } else {
                            // cycle detected: just return the expression as-is.
                            return mast_ts_id;
                        }
                    }
                    case gdef::DefKind::BV_TS:
                    {
                        GDefID new_def_id = sub::rw_def_id(s, old_def_id);
                        if (new_def_id == old_def_id) {
                            return mast_ts_id;
                        } else {
                            // std::cout << "INFO: REPLACEMENT: " << old_def_id << " -> " << new_def_id << std::endl;
                            return mast::new_gid_ts(new_def_id);
                        }
                    }
                    default:
                    {
                        throw new Panic("Invalid GDefID in TypeSpecID");
                    }
                }
            } break;
            case mast::TS_PTR: {
                auto info = mast::get_info_ptr(mast_ts_id)->ts_ptr;
                auto old_ptd_ts = info.ptd_ts;
                auto ptd_ts = p2m_ts(old_ptd_ts, s, st, ignore_gdef_id_set, mono_mod_id);
                bool contents_is_mut = info.contents_is_mut;
                if (old_ptd_ts != ptd_ts) {
                    return mast::new_ptr_ts(ptd_ts, contents_is_mut);
                } else {
                    return mast_ts_id;
                }
            } break;
            case mast::TS_ARRAY: {
                auto info = mast::get_info_ptr(mast_ts_id)->ts_array;
                auto old_ptd_ts = info.ptd_ts;
                auto ptd_ts = p2m_ts(old_ptd_ts, s, st, ignore_gdef_id_set, mono_mod_id);
                bool contents_is_mut = info.contents_is_mut;
                auto old_count_exp = info.count_exp;
                auto count_exp = p2m_exp(old_count_exp, s, st, ignore_gdef_id_set, mono_mod_id);
                if (old_ptd_ts != ptd_ts || old_count_exp != count_exp) {
                    return mast::new_array_ts(
                        ptd_ts, count_exp, 
                        contents_is_mut
                    );
                } else {
                    return mast_ts_id;
                }
            } break;
            case mast::TS_SLICE: {
                auto info = mast::get_info_ptr(mast_ts_id)->ts_slice;
                auto old_ptd_ts = info.ptd_ts;
                auto ptd_ts = p2m_ts(old_ptd_ts, s, st, ignore_gdef_id_set, mono_mod_id);
                bool contents_is_mut = info.contents_is_mut;
                if (old_ptd_ts != ptd_ts) {
                    return mast::new_slice_ts(ptd_ts, contents_is_mut);
                } else {
                    return mast_ts_id;
                }
            } break;
            case mast::TS_TUPLE: {
                auto info = mast::get_info_ptr(mast_ts_id)->ts_tuple;

                size_t const elem_count = info.elem_ts_count;
                auto new_elem_ts_array = new mast::TypeSpecID[elem_count];
                bool any_elem_changed = false;
                for (size_t i = 0; i < elem_count; i++) {
                    auto old_ts = info.elem_ts_array[i];
                    auto new_ts = p2m_ts(old_ts, s, st, ignore_gdef_id_set, mono_mod_id);
                    
                    if (new_ts != old_ts) {
                        any_elem_changed = true;
                    }

                    new_elem_ts_array[i] = new_ts;
                }
                if (any_elem_changed) {
                    return mast::new_tuple_ts(
                        elem_count,
                        new_elem_ts_array
                    );
                } else {
                    delete[] new_elem_ts_array;
                    return mast_ts_id;
                }
            } break;
            case mast::TS_FUNC_SGN: {
                auto info = &mast::get_info_ptr(mast_ts_id)->ts_func_sgn;

                auto old_arg_ts = info->arg_ts;
                auto old_ret_ts = info->ret_ts;

                auto new_arg_ts = p2m_ts(old_arg_ts, s, st, ignore_gdef_id_set, mono_mod_id);
                auto new_ret_ts = p2m_ts(old_ret_ts, s, st, ignore_gdef_id_set, mono_mod_id);
                auto ret_ses = info->ret_ses;

                if (new_arg_ts != old_arg_ts || new_ret_ts != old_ret_ts) {
                    return mast::new_func_sgn_ts(
                        new_arg_ts,
                        new_ret_ts,
                        ret_ses
                    );
                } else {
                    return mast_ts_id;
                }
            } break;
            case mast::TS_GET_MONO_MODULE_FIELD: {
                // preserved exactly as is
                return mast_ts_id;
            } break;
            case mast::TS_GET_POLY_MODULE_FIELD: {
                // instantiating the LHS module using the actual args given
                auto raw_info = mast::get_info_ptr(mast_ts_id);
                auto info = &raw_info->ts_get_poly_module_field;
                
                auto poly_mod_id = info->template_id;
                auto arg_count = info->actual_arg_count;
                auto arg_array = info->actual_arg_array;

                // constructing an ArgList by iterating in reverse order:
                arg_list::ArgListID actual_arg_list = arg_list_from_node_array(
                    arg_count,
                    arg_array,
                    s, st, mono_mod_id
                );

                auto mono_mod_id = modules::instantiate_poly_mod(poly_mod_id, actual_arg_list);
                return mast::new_get_mono_module_field_ts(mono_mod_id, info->ts_field_index);
            } break;
            default: {
                // std::cout << "INFO: unknown TS node kind = " << ts_kind << std::endl;
                throw new Panic("NotImplemented: unknown TS node kind");
            } break;
        }
    }

    mast::ExpID p2m_exp(
        mast::ExpID mast_exp_id, 
        sub::Substitution* s,
        stack::Stack* st,
        std::set<GDefID>& ignored_gdef_id_set,
        MonoModID mono_mod_id
    ) {
        auto exp_kind = mast::get_node_kind(mast_exp_id);
        switch (exp_kind) {
            case mast::EXP_UNIT:
            case mast::EXP_INT:
            case mast::EXP_FLOAT: 
            case mast::EXP_STRING:
            case mast::EXP_LID:
            {
                return mast_exp_id;
            } break;
            
            case mast::EXP_GID:
            {
                // must replace this GDefID or its referenced contents with substitution `s`
                auto info = &mast::get_info_ptr(mast_exp_id)->exp_gid;
                GDefID old_def_id = info->def_id;
                gdef::DefKind old_def_kind = gdef::get_def_kind(old_def_id);
                switch (old_def_kind) {
                    case gdef::DefKind::CONST_TOT_VAL:
                    {
                        // no substitution/copying needed
                        return mast_exp_id;
                    }
                    case gdef::DefKind::CONST_EXP:
                    {
                        // must apply this substitution to the stored ID UNLESS we are already in the process of 
                        // expanding this ID (i.e., a cycle has occurred)
                        auto found_tuple = ignored_gdef_id_set.insert(old_def_id);
                        if (found_tuple.second) {
                            // insertion succeeded <=> this GDefID was freshly added
                            mast::ExpID old_target = gdef::get_def_target(old_def_id);
                            mast::ExpID new_target = p2m_exp(old_target, s, st, ignored_gdef_id_set, mono_mod_id);
                            if (new_target != old_target) {
                                char* cp_name = strdup(gdef::get_def_name(old_def_id));
                                GDefID new_def_id = gdef::declare_global_def(gdef::DefKind::CONST_EXP, cp_name);
                                gdef::set_def_target(new_def_id, new_target);
                                return mast::new_gid_exp(new_def_id);
                            } else {
                                return mast_exp_id;
                            }
                        } else {
                            return mast_exp_id;
                        }
                    }
                    case gdef::DefKind::BV_EXP:
                    {
                        // replacing the whole GDefID (with a total constant one)
                        GDefID new_def_id = sub::rw_def_id(s, old_def_id);
                        if (new_def_id == old_def_id) {
                            return mast_exp_id;
                        } else {
                            // std::cout 
                            //     << "INFO: Rewrite in BV_EXP: " 
                            //     << "replacing " << old_def_id << " with " << new_def_id << " such that "
                            //     << "new target is " << gdef::get_def_target(new_def_id)
                            //     << std::endl;
                            return mast::new_gid_exp(new_def_id);
                        }
                    }
                    default:
                    {
                        throw new Panic("Invalid GDefID in ExpID");
                    }
                }
            } break;

            case mast::EXP_FUNC_CALL:
            {
                auto info = &mast::get_info_ptr(mast_exp_id)->exp_call;
                
                auto old_fn_exp = info->called_fn;
                auto new_fn_exp = p2m_exp(old_fn_exp, s, st, ignored_gdef_id_set, mono_mod_id);

                auto old_arg_exp = info->arg_exp_id;
                auto new_arg_exp = p2m_exp(old_arg_exp, s, st, ignored_gdef_id_set, mono_mod_id);

                bool call_is_non_tot = info->call_is_non_tot;

                bool changed = (
                    (old_fn_exp != new_fn_exp) ||
                    (old_arg_exp != new_arg_exp)
                );
                if (changed) {
                    return mast::new_func_call_exp(
                        new_fn_exp,
                        new_arg_exp,
                        call_is_non_tot
                    );
                } else {
                    return mast_exp_id;
                }
            } break;

            case mast::EXP_UNARY_OP:
            {
                auto info = &mast::get_info_ptr(mast_exp_id)->exp_unary;

                auto old_arg_exp = info->arg_exp;
                auto new_arg_exp = p2m_exp(old_arg_exp, s, st, ignored_gdef_id_set, mono_mod_id);

                auto unary_op = info->unary_op;

                if (old_arg_exp != new_arg_exp) {
                    return mast::new_unary_op_exp(unary_op, new_arg_exp);
                } else {
                    return mast_exp_id;
                }
            } break;

            case mast::EXP_BINARY_OP:
            {
                auto info = &mast::get_info_ptr(mast_exp_id)->exp_binary;

                auto binary_op = info->binary_op;

                auto old_lt_arg_exp = info->lt_arg_exp;
                auto new_lt_arg_exp = p2m_exp(old_lt_arg_exp, s, st, ignored_gdef_id_set, mono_mod_id);

                auto old_rt_arg_exp = info->rt_arg_exp;
                auto new_rt_arg_exp = p2m_exp(old_rt_arg_exp, s, st, ignored_gdef_id_set, mono_mod_id);

                bool changed = (
                    (old_lt_arg_exp != new_lt_arg_exp) ||
                    (old_rt_arg_exp != new_rt_arg_exp)
                );
                if (changed) {
                    return mast::new_binary_op_exp(
                        binary_op,
                        new_lt_arg_exp,
                        new_rt_arg_exp
                    );
                } else {
                    return mast_exp_id;
                }
            } break;

            case mast::EXP_IF_THEN_ELSE:
            {
                auto info = &mast::get_info_ptr(mast_exp_id)->exp_if_then_else;

                auto old_cond_exp = info->cond_exp;
                auto new_cond_exp = p2m_exp(old_cond_exp, s, st, ignored_gdef_id_set, mono_mod_id);

                auto old_then_exp = info->then_exp;
                auto new_then_exp = p2m_exp(old_then_exp, s, st, ignored_gdef_id_set, mono_mod_id);

                auto old_else_exp = info->else_exp;
                auto new_else_exp = p2m_exp(old_else_exp, s, st, ignored_gdef_id_set, mono_mod_id);

                bool changed = (
                    (old_cond_exp != new_cond_exp) ||
                    (old_then_exp != new_then_exp) ||
                    (old_else_exp != new_else_exp)
                );
                if (changed) {
                    return mast::new_if_then_else_exp(
                        new_cond_exp,
                        new_then_exp,
                        new_else_exp
                    );
                } else {
                    return mast_exp_id;
                }
            } break;

            case mast::EXP_GET_TUPLE_FIELD:
            {
                auto raw_info = mast::get_info_ptr(mast_exp_id);
                auto info = &raw_info->exp_get_tuple_field;

                auto old_tuple_exp = info->tuple_exp_id;
                auto new_tuple_exp = p2m_exp(old_tuple_exp, s, st, ignored_gdef_id_set, mono_mod_id);

                auto index = info->index;

                bool changed = (old_tuple_exp != new_tuple_exp);
                if (changed) {
                    return mast::new_get_tuple_field_by_index_exp(
                        new_tuple_exp,
                        index
                    );
                } else {
                    return mast_exp_id;
                }
            } break;

            case mast::EXP_GET_POLY_MODULE_FIELD:
            {
                // instantiating the LHS module using the actual args given
                auto raw_info = mast::get_info_ptr(mast_exp_id);
                auto info = &raw_info->exp_get_poly_module_field;

                auto poly_mod_id = info->template_id;
                auto arg_count = info->arg_count;
                auto arg_array = info->arg_array;

                // constructing an ArgList by iterating in reverse order:
                arg_list::ArgListID actual_arg_list = arg_list_from_node_array(
                    arg_count,
                    arg_array,
                    s, st,
                    mono_mod_id
                );

                auto mono_mod_id = modules::instantiate_poly_mod(poly_mod_id, actual_arg_list);
                return mast::new_get_mono_module_field_exp(mono_mod_id, info->field_index);
            } break;

            case mast::EXP_GET_MONO_MODULE_FIELD:
            {
                return mast_exp_id;
            } break;

            case mast::EXP_LAMBDA:
            {
                auto raw_info = mast::get_info_ptr(mast_exp_id);
                auto info = &raw_info->exp_lambda;

                auto old_body_exp_id = info->body_exp;
                auto new_body_exp_id = p2m_exp(old_body_exp_id, s, st, ignored_gdef_id_set, mono_mod_id);

                bool changed = (old_body_exp_id != new_body_exp_id);
                mast::ExpID lambda_exp_id;
                if (changed) {
                    auto arg_name_count = info->arg_name_count;
                    auto new_arg_name_array = new intern::IntStr[arg_name_count];
                    for (uint32_t i = 0; i < arg_name_count; i++) {
                        // function args are never rewritten by monomorphization
                        new_arg_name_array[i] = info->arg_name_array[i];
                    }

                    auto ctx_enclosed_name_count = info->ctx_enclosed_name_count;
                    auto ctx_enclosed_name_array = new intern::IntStr[ctx_enclosed_name_count];
                    for (uint32_t i = 0; i < arg_name_count; i++) {
                        ctx_enclosed_name_array[i] = info->ctx_enclosed_name_array[i];
                    }

                    lambda_exp_id = mast::new_lambda_exp(
                        arg_name_count, 
                        new_arg_name_array,
                        ctx_enclosed_name_count,
                        ctx_enclosed_name_array,
                        new_body_exp_id
                    );
                } else {
                    lambda_exp_id = mast_exp_id;
                }

                modules::register_lambda(mono_mod_id, lambda_exp_id);

                return lambda_exp_id;
            } break;

            case mast::EXP_ALLOCATE_ONE:
            {
                auto info = &mast::get_info_ptr(mast_exp_id)->exp_allocate_one;

                auto old_init_exp_id = info->stored_val_exp_id;
                auto new_init_exp_id = p2m_exp(old_init_exp_id, s, st, ignored_gdef_id_set, mono_mod_id);

                bool changed = (old_init_exp_id != new_init_exp_id);
                if (changed) {
                    return mast::new_allocate_one_exp(
                        new_init_exp_id,
                        info->allocation_target,
                        info->allocation_is_mut
                    );
                } else {
                    return mast_exp_id;
                }
            } break;

            case mast::EXP_ALLOCATE_MANY:
            {
                auto info = &mast::get_info_ptr(mast_exp_id)->exp_allocate_many;

                auto old_init_exp_id = info->initializer_stored_val_exp_id;
                auto new_init_exp_id = p2m_exp(old_init_exp_id, s, st, ignored_gdef_id_set, mono_mod_id);

                auto old_count_exp_id = info->alloc_count_exp;
                auto new_count_exp_id = p2m_exp(new_init_exp_id, s, st, ignored_gdef_id_set, mono_mod_id);

                bool changed = (old_init_exp_id != new_init_exp_id);
                if (changed) {
                    return mast::new_allocate_many_exp(
                        new_init_exp_id,
                        new_count_exp_id,
                        info->allocation_target,
                        info->allocation_is_mut
                    );
                } else {
                    return mast_exp_id;
                }
            } break;

            case mast::EXP_CHAIN:
            {
                auto info = &mast::get_info_ptr(mast_exp_id)->exp_chain;
                
                size_t elem_count = info->prefix_elem_count;
                mast::ElemID* old_elem_array = info->prefix_elem_array;
                mast::ElemID* new_elem_array;
                if (elem_count) {
                    new_elem_array = new mast::ElemID[elem_count];
                    // std::cout << "INFO: p2m_exp::EXP_CHAIN has elem-array " << new_elem_array << std::endl;
                    for (size_t i = 0; i < elem_count; i++) {
                        new_elem_array[i] = p2m_elem(old_elem_array[i], s, st, ignored_gdef_id_set, mono_mod_id);
                    }
                } else {
                    new_elem_array = nullptr;
                }

                mast::ExpID ret_exp_id = p2m_exp(info->ret_exp_id, s, st, ignored_gdef_id_set, mono_mod_id);

                return mast::new_chain_exp(elem_count, new_elem_array, ret_exp_id);
            } break;

            case mast::EXP_TUPLE:
            {
                auto info = &mast::get_info_ptr(mast_exp_id)->exp_tuple;
                
                auto item_count = info->item_count;
                auto old_item_array = info->item_array;
                auto new_item_array = new mast::ExpID[item_count];
                for (size_t i = 0; i < item_count; i++) {
                    new_item_array[i] = p2m_exp(old_item_array[i], s, st, ignored_gdef_id_set, mono_mod_id);
                }

                return mast::new_tuple_exp(item_count, new_item_array);
            } break;

            case mast::EXP_CAST:
            {
                auto info = &mast::get_info_ptr(mast_exp_id)->exp_cast;

                auto old_ts_id = info->ts_id;
                auto new_ts_id = p2m_ts(old_ts_id, s, st, ignored_gdef_id_set, mono_mod_id);

                auto old_exp_id = info->exp_id;
                auto new_exp_id = p2m_exp(old_exp_id, s, st, ignored_gdef_id_set, mono_mod_id);

                return mast::new_cast_exp(new_ts_id, new_exp_id);
            } break;

            default:
            {
                throw new Panic("NotImplemented: p2m_exp for unknown exp kind");
            } break;
        }
    }

    mast::ElemID p2m_elem(
        mast::ElemID elem_id, 
        sub::Substitution* s, 
        stack::Stack* st, 
        std::set<GDefID>& ignored_gdef_id_set,
        MonoModID mono_mod_id
    ) {
        mast::NodeKind elem_kind = mast::get_node_kind(elem_id);
        switch (elem_kind) {
            case mast::ELEM_BIND1T:
            {
                auto info = &mast::get_info_ptr(elem_id)->elem_bind1t;
                auto bound_id = info->bound_id;
                auto init_ts_id = p2m_ts(info->init_ts_id, s, st, ignored_gdef_id_set, mono_mod_id);
                return mast::new_bind1t_elem(bound_id, init_ts_id);
            } break;
            case mast::ELEM_BIND1V:
            {
                auto info = &mast::get_info_ptr(elem_id)->elem_bind1v;
                auto bound_id = info->bound_id;
                auto init_exp_id = p2m_exp(info->init_exp_id, s, st, ignored_gdef_id_set, mono_mod_id);
                return mast::new_bind1v_elem(bound_id, init_exp_id);
            } break;
            case mast::ELEM_DO:
            {
                auto info = &mast::get_info_ptr(elem_id)->elem_do;
                auto discarded_exp_id = p2m_exp(info->eval_exp_id, s, st, ignored_gdef_id_set, mono_mod_id);
                return mast::new_do_elem(discarded_exp_id);
            } break;
            default:
            {
                // std::cout << "ERROR_EXTRA: unknown elem kind: " << elem_kind << std::endl;
                throw new Panic("NotImplemented: p2m_elem for unknown elem kind");
            } break;
        }
    }

}

//
// Implementation:
//

namespace monomorphizer::eval {

    mtype::TID eval_def_t(GDefID def_id, stack::Stack* st, MonoModID mono_mod_id) {
        gdef::DefKind def_kind = gdef::get_def_kind(def_id);
        switch (def_kind) {
            case gdef::DefKind::CONST_TOT_TID: {
                return gdef::get_def_target(def_id);
            } break;
            case gdef::DefKind::CONST_TS: {
                auto stored_ts_id = gdef::get_def_target(def_id);
                return eval_mono_ts(stored_ts_id, st, mono_mod_id);
            } break;
            case gdef::DefKind::BV_TS: {
//                std::cout << "ERROR: DefID = " << def_id << std::endl;
                throw new Panic("InputError: `eval_def_t` cannot eval a bound var");
            } break;
            default: {
                throw new Panic("InputError: unknown DefKind in `eval_def_t`");
            }
        }
    }

    mval::VID eval_def_v(GDefID def_id, stack::Stack* st, MonoModID mono_mod_id) {
        gdef::DefKind def_kind = gdef::get_def_kind(def_id);
        switch (def_kind) {
            case gdef::DefKind::CONST_TOT_VAL: {
                return gdef::get_def_target(def_id);
            } break;
            case gdef::DefKind::CONST_EXP: {
                auto stored_val_id = gdef::get_def_target(def_id);
                return eval_mono_exp(stored_val_id, st, mono_mod_id);
            } break;
            case gdef::DefKind::BV_EXP: {
                throw new Panic("InputError: `eval_def_v` cannot eval a bound var");
            } break;
            default: {
                throw new Panic("InputError: unknown DefKind in `eval_def_v`");
            }
        }
    }

}

//
// Implementation:
//

namespace monomorphizer::eval {

    static mtype::TID eval_poly_ts_impl(
        mast::TypeSpecID poly_ts,
        sub::Substitution* s,
        stack::Stack* st,
        MonoModID mono_mod_id
    ) {
        mast::TypeSpecID mono_ts; {
            std::set<GDefID> ignored_def_id_set;
            mono_ts = p2m_ts(poly_ts, s, st, ignored_def_id_set, mono_mod_id);
        }
        return eval_mono_ts(mono_ts, st, mono_mod_id);
    }
    static mval::VID eval_poly_exp_impl(
        mast::ExpID exp_id,
        sub::Substitution* s,
        stack::Stack* st,
        MonoModID mono_mod_id
    ) {
        mast::ExpID mono_exp; {
            std::set<GDefID> ignored_def_id_set;
            mono_exp = p2m_exp(exp_id, s, st, ignored_def_id_set, mono_mod_id);
        }
        return eval_mono_exp(mono_exp, st, mono_mod_id);
    }

    mtype::TID eval_poly_ts(
        mast::TypeSpecID poly_ts,
        sub::Substitution* s,
        MonoModID mono_mod_id
    ) {
        stack::Stack* st = stack::create_stack();
        auto res = eval_poly_ts_impl(poly_ts, s, st, mono_mod_id);
        stack::destroy_stack(st);
        return res;
    }
    mast::ExpID eval_poly_exp(
        mast::ExpID exp_id,
        sub::Substitution* s,
        MonoModID mono_mod_id
    ) {
        stack::Stack* st = stack::create_stack();
        auto res = eval_poly_exp_impl(exp_id, s, st, mono_mod_id);
        stack::destroy_stack(st);
        return res;
    }

    //
    // `eval_mono_ts` implementation:
    //

    mtype::TID eval_mono_ts(
        mast::TypeSpecID ts_id,
        stack::Stack* st,
        MonoModID mono_mod_id
    ) {
        mast::NodeKind ts_kind = mast::get_node_kind(ts_id);
        switch (ts_kind) {
            case mast::TS_UNIT: {
                return mtype::get_unit_tid();
            } break;

            case mast::TS_LID: {
                auto info = &mast::get_info_ptr(ts_id)->ts_lid;
                return stack::lookup_t_in_stack(st, info->int_str_id);
            } break;

            case mast::TS_GID: {
                auto info = &mast::get_info_ptr(ts_id)->ts_gid;
                GDefID def_id = info->def_id;
                auto out_tid = eval_def_t(def_id, st, mono_mod_id);
                // std::cout << "INFO: TS_GID " << ts_id << " evaluates to " << out_tid << std::endl;
                return out_tid;
            } break;

            case mast::TS_PTR: {
                auto info = &mast::get_info_ptr(ts_id)->ts_ptr;
                mtype::TID ptd_tid = eval_mono_ts(info->ptd_ts, st, mono_mod_id);
                return mtype::get_ptr_tid(ptd_tid, info->contents_is_mut);
            } break;
            
            case mast::TS_ARRAY: {
                auto info = &mast::get_info_ptr(ts_id)->ts_array;
                mtype::TID ptd_tid = eval_mono_ts(info->ptd_ts, st, mono_mod_id);
                mval::VID count_val_id = eval_mono_exp(info->count_exp, st, mono_mod_id);
                bool is_mut = info->contents_is_mut;
                return mtype::get_array_tid(ptd_tid, count_val_id, is_mut);
            } break;
            
            case mast::TS_SLICE: {
                auto info = &mast::get_info_ptr(ts_id)->ts_slice;
                mtype::TID ptd_tid = eval_mono_ts(info->ptd_ts, st, mono_mod_id);
                bool contents_is_mut = info->contents_is_mut;
                return mtype::get_slice_tid(ptd_tid, contents_is_mut);
            } break;
            
            case mast::TS_FUNC_SGN: {
                auto info = &mast::get_info_ptr(ts_id)->ts_func_sgn;
                auto arg_tid = eval_mono_ts(info->arg_ts, st, mono_mod_id);
                auto ret_tid = eval_mono_ts(info->ret_ts, st, mono_mod_id);
                auto ses = info->ret_ses;
                return mtype::get_function_tid(arg_tid, ret_tid, ses);
            } break;

            case mast::TS_TUPLE: {
                // std::cout << "DEBUG: eval_mono_ts for mast::TS_TUPLE" << std::endl;
                // std::cout.flush();
                
                auto info = &mast::get_info_ptr(ts_id)->ts_tuple;
                auto elem_count = info->elem_ts_count;
                auto elem_array = info->elem_ts_array;

                // constructing an arg-list in reverse order:
                // In the future, iterating through this list should produce elements in original order.
                auto made_arg_list = arg_list::EMPTY_ARG_LIST;
                for (size_t i = 0; i < elem_count; i++) {
                    // std::cout << "DEBUG: BP 1." << i << std::endl;
                    // std::cout << "- elem_array = " << elem_array << std::endl;
                    // std::cout.flush();
                    auto elem_index = elem_count - (i + 1);
                    auto elem_ts = elem_array[elem_index];
                    // std::cout << "DEBUG: BP 2." << i << std::endl;
                    // std::cout.flush();
                    auto elem_ts_tid = eval_mono_ts(elem_ts, st, mono_mod_id);
                    // std::cout << "DEBUG: BP 3." << i << std::endl;
                    // std::cout.flush();
                    made_arg_list = arg_list::cons_tid(
                        made_arg_list, 
                        elem_ts_tid
                    );
                    // std::cout << "DEBUG: BP 4." << i << std::endl;
                    // std::cout.flush();
                }
                assert(arg_list::count_arg_list_items(made_arg_list) == elem_count);
                
                // std::cout << "DEBUG: Constructed ArgList for TS_TUPLE" << std::endl;
                // std::cout.flush();

                auto ret_id = mtype::get_tuple_tid(made_arg_list);

                // std::cout << "DEBUG: Ret-ID: " << ret_id << std::endl;
                // std::cout.flush();

                return ret_id;
            } break;
            
            case mast::TS_GET_MONO_MODULE_FIELD: {
                auto raw_info = mast::get_info_ptr(ts_id);
                auto info = &raw_info->ts_get_mono_module_field;

                GDefID def_id = modules::get_mono_mod_field_at(
                    info->template_id,
                    info->ts_field_index
                );
                return eval_def_t(def_id, st, mono_mod_id);
            } break;

            default: {
                throw new Panic("Invalid mono TS kind");
            }
        }
    }

    //
    // `eval_mono_elem` implementation:
    //

    void eval_mono_elem(mast::ElemID elem_id, stack::Stack* st, MonoModID mono_mod_id) {
        mast::NodeKind elem_kind = mast::get_node_kind(elem_id);
        switch (elem_kind)
        {
            case mast::ELEM_BIND1T:
            {
                auto info = &mast::get_info_ptr(elem_id)->elem_bind1t;
                stack::def_t_in_stack(st, info->bound_id, eval_mono_ts(info->init_ts_id, st, mono_mod_id));
            } break;
            case mast::ELEM_BIND1V:
            {
                auto info = &mast::get_info_ptr(elem_id)->elem_bind1v;
                stack::def_v_in_stack(st, info->bound_id, eval_mono_exp(info->init_exp_id, st, mono_mod_id));
            } break;
            case mast::ELEM_DO:
            {
                auto info = &mast::get_info_ptr(elem_id)->elem_do;
                eval_mono_exp(info->eval_exp_id, st, mono_mod_id);
            } break;
            default:
            {
                // std::cout << "DEBUG: unknown elem kind: " << elem_kind << std::endl;
                throw new Panic("Unknown/invalid 'elem' kind encountered while evaluating");
            }
        }
    }

    //
    // `eval_mono_exp` implementation:
    //

    static ssize_t signed_int_exp_val(size_t mu, bool b) {
        ssize_t m = mu;
        ssize_t v = b ? -m : +m;
        return v;
    }
    static mval::VID eval_mono_int_exp(mast::ExpID exp_id) {
        auto info = &mast::get_info_ptr(exp_id)->exp_int;
        auto m = info->mantissa;
        auto b = info->is_neg;
        switch (info->suffix) {
            case IS_U1: {
                return mval::push_u1(m);
            }
            case IS_U8: {
                return mval::push_u8(static_cast<uint8_t>(m));
            }
            case IS_U16: {
                return mval::push_u16(static_cast<uint16_t>(m));
            }
            case IS_U32: {
                return mval::push_u32(static_cast<uint32_t>(m));
            }
            case IS_U64: {
                return mval::push_u64(static_cast<uint64_t>(m));
            }
            case IS_S8: {
                return mval::push_s8(
                    static_cast<int8_t>(signed_int_exp_val(m,b))
                );
            }
            case IS_S16: {
                return mval::push_s16(
                    static_cast<int16_t>(signed_int_exp_val(m,b))
                );
            }
            case IS_S32: {
                return mval::push_s32(
                    static_cast<int32_t>(signed_int_exp_val(m,b))
                );
            }
            case IS_S64: {
                return mval::push_s64(
                    static_cast<int64_t>(signed_int_exp_val(m,b))
                );
            }
        }
    }
    static mval::VID eval_mono_float_exp(mast::ExpID exp_id) {
        auto info = &mast::get_info_ptr(exp_id)->exp_float;
        switch (info->suffix) {
            case FS_F32: {
                return mval::push_f32(info->value);
            }
            case FS_F64: {
                return mval::push_f64(info->value);
            }
        }
    }
    static mval::VID eval_mono_string_exp(mast::ExpID exp_id) {
        auto info = &mast::get_info_ptr(exp_id)->exp_str;
        auto code_point_count = info->code_point_count;
        auto code_point_array = new int[code_point_count];
        for (size_t i = 0; i < code_point_count; i++) {
            code_point_array[i] = info->code_point_array[i];
        }
        return mval::push_str(
            code_point_count,
            code_point_array
        );
    }
    static mval::VID eval_mono_func_call_exp(mast::ExpID exp_id, stack::Stack* st, MonoModID mono_mod_id) {
        // std::cout << "DEBUG: INTRODUCTION: eval_mono_func_call_exp" << std::endl;
        // std::cout.flush();
        
        auto info = &mast::get_info_ptr(exp_id)->exp_call;

        // checking that the SES is TOT: only total functions can be evaluated at compile-time.
        if (info->call_is_non_tot) {
            throw new Panic("Cannot evaluate a non-total function at compile-time.");
        }

        // first, evaluating the argument and function in the outer stack frame:
        mval::VID fun_vid = eval_mono_exp(info->called_fn, st, mono_mod_id);
        mval::VID raw_arg_vid = eval_mono_exp(info->arg_exp_id, st, mono_mod_id);
        
        // reaching inside the `fun` VID to retrieve the body expression to evaluate, args to pass.
        // std::cout << "DEBUG: preparing to reach inside func value_info" << std::endl;
        // std::cout.flush();
        assert(mval::value_kind(fun_vid) == mval::ValueKind::VK_FUNCTION);
        size_t func_info_index = mval::value_info(fun_vid).func_info_index;
        mval::FuncInfo* func_info_p = mval::get_func_info(func_info_index);
        auto fn_enclosed_id_count = func_info_p->ctx_enclosed_id_count;
        auto fn_enclosed_id_array = func_info_p->ctx_enclosed_id_array;
        auto fn_arg_name_array = func_info_p->arg_name_array;
        auto fn_arg_name_count = func_info_p->arg_name_count;
        auto fn_body_exp_id = func_info_p->body_exp_id;
        // std::cout << "DEBUG: ... done" << std::endl;
        // std::cout.flush();

        // NOTE: we do not perform type conversion on the argument or return
        //       type for calls-- types must be cast explicitly.
        mval::VID arg_vid = raw_arg_vid;

        // pushing a new frame to the stack, computing the return value:
        // std::cout << "DEBUG: preparing to push stack frame" << std::endl;
        // std::cout.flush();
        stack::push_stack_frame(st);
        // std::cout << "DEBUG: ... done" << std::endl;
        // std::cout.flush();
        mval::VID ret_val_id;
        {
            // setting up the stack frame with ctx_enclosed_ids
            // std::cout << "DEBUG: preparing to set up stack frame with ctx_enclosed_ids (cf nonlocal)" << std::endl;
            // std::cout.flush();
            for (uint32_t i = 0; i < fn_enclosed_id_count; i++) {
                auto enclosed_mapping = fn_enclosed_id_array[i];
                if (intern::is_interned_string_tid_not_vid(enclosed_mapping.name)) {
                    // target is an mtype::TID
                    mtype::TID target = enclosed_mapping.target;
                    stack::def_t_in_stack(st, enclosed_mapping.name, target);
                } else {
                    // target is an mval::VID
                    mval::VID target = enclosed_mapping.target;
                    stack::def_v_in_stack(st, enclosed_mapping.name, target);
                }
            }
            // std::cout << "DEBUG: ... done" << std::endl;
            // std::cout.flush();

            // setting up the stack frame with arguments
            // std::cout << "DEBUG: preparing to set up stack frame with func args" << std::endl;
            // std::cout << "DEBUG: \targ-count: " << fn_arg_name_count << std::endl;
            // std::cout.flush();
            if (fn_arg_name_count == 0) {
                // no arguments need be bound
            } else if (fn_arg_name_count == 1) {
                stack::def_v_in_stack(st, fn_arg_name_array[0], arg_vid);
            } else {
                assert(mval::value_kind(arg_vid) == mval::ValueKind::VK_TUPLE);
                auto arg_seq_info_index = mval::value_info(arg_vid).sequence_info_index;
                for (uint32_t j = 0; j < fn_arg_name_count; j++) {
                    intern::IntStr arg_name = fn_arg_name_array[j];
                    mval::VID arg_bound = mval::get_seq_elem1(arg_seq_info_index, j).value_or(mval::NULL_VID);
                    assert(arg_bound != mval::NULL_VID);
                    // std::cout << "DEBUG: get-seq-elem " << j << " OK" << std::endl;
                    // std::cout.flush();
                    stack::def_v_in_stack(st, arg_name, arg_bound);
                }
            }
            // std::cout << "DEBUG: ... done" << std::endl;
            // std::cout.flush();

            // std::cout << "DEBUG: Preparing to evaluate body in EXP_FUNC_CALL" << std::endl;
            // std::cout.flush();

            // evaluating the return expression in this stack frame:
            ret_val_id = eval_mono_exp(fn_body_exp_id, st, mono_mod_id);

            // std::cout << "DEBUG: ... done" << std::endl;
            // std::cout.flush();
        }
        stack::pop_stack_frame(st);

        // std::cout << "DEBUG: CONCLUSION: EXP_FUNC_CALL ret_val_id = " << ret_val_id << std::endl;
        // std::cout.flush();

        return ret_val_id;
    }
    static mval::VID eval_mono_unary_op_exp(mast::ExpID exp_id, stack::Stack* st, MonoModID mono_mod_id) {
        auto info = &mast::get_info_ptr(exp_id)->exp_unary;
                
        mval::VID arg_val_id = eval_mono_exp(info->arg_exp, st, mono_mod_id);
        auto vk = mval::value_kind(arg_val_id);
        auto vi = mval::value_info(arg_val_id);

        switch (info->unary_op) {
            case UNARY_POS: {
                switch (vk) {
                    // identity op
                    case mval::VK_S8:
                    case mval::VK_S16:
                    case mval::VK_S32:
                    case mval::VK_S64:
                    case mval::VK_F32:
                    case mval::VK_F64:
                    {
                        return arg_val_id;
                    }

                    // cast unsigned to signed
                    case mval::VK_U8: return mval::push_s8(vi.u8);
                    case mval::VK_U16: return mval::push_s16(vi.u16);
                    case mval::VK_U32: return mval::push_s32(vi.u32);
                    case mval::VK_U64: return mval::push_s64(vi.u64);

                    // any other arg is an error:
                    default: {
                        throw new Panic("Invalid arg to unary op '+'");
                    }
                }
            } break;
            case UNARY_NEG: {
                switch (vk) {
                    case mval::VK_S8: return mval::push_s8(-vi.s8);
                    case mval::VK_S16: return mval::push_s16(-vi.s16);
                    case mval::VK_S32: return mval::push_s32(-vi.s32);
                    case mval::VK_S64: return mval::push_s64(-vi.s64);
                    case mval::VK_F32: return mval::push_f32(-vi.f32);
                    case mval::VK_F64: return mval::push_f64(-vi.f64);
                    default: throw new Panic("Invalid arg to unary op '-'");
                }
            } break;
            case UNARY_LOGICAL_NOT: {
                switch (vk) {
                    case mval::VK_U1: {
                        return mval::push_u1(!vi.u1);
                    }
                    default: {
                        throw new Panic("Invalid arg to unary op 'not'");
                    }
                }
            } break;
            case UNARY_DE_REF: {
                throw new Panic("NotImplemented: eval UNARY_DeRef");
            } break;
        }
    }
    template <typename T> 
    inline static T ipow(T base, T exponent) {
        T result = 1;
        for (T i = 0; i < exponent; i++) {
            result *= base;
        }
        return result;
    }
    static mval::VID eval_mono_binary_op_exp(mast::ExpID exp_id, stack::Stack* st, MonoModID mono_mod_id) {
        auto info = &mast::get_info_ptr(exp_id)->exp_binary;
        
        mval::VID lt_arg_val_id = eval_mono_exp(info->lt_arg_exp, st, mono_mod_id);
        auto lt_vk = mval::value_kind(lt_arg_val_id);
        auto lt_vi = mval::value_info(lt_arg_val_id);

        mval::VID rt_arg_val_id = eval_mono_exp(info->rt_arg_exp, st, mono_mod_id);
        auto rt_vk = mval::value_kind(rt_arg_val_id);
        auto rt_vi = mval::value_info(rt_arg_val_id);

        assert(lt_vk == rt_vk && "NotImplemented: BinaryOp value promotions");
        auto vk = lt_vk;

        switch (info->binary_op) {
            case BINARY_POW: {
                switch (vk) {
                    case mval::VK_U8: return mval::push_u8(ipow(lt_vi.u8, rt_vi.u8));
                    case mval::VK_U16: return mval::push_u16(ipow(lt_vi.u16, rt_vi.u16));
                    case mval::VK_U32: return mval::push_u32(ipow(lt_vi.u32, rt_vi.u32));
                    case mval::VK_U64: return mval::push_u64(ipow(lt_vi.u64, rt_vi.u64));
                    case mval::VK_S8: return mval::push_s8(ipow(lt_vi.s8, rt_vi.s8));
                    case mval::VK_S16: return mval::push_s16(ipow(lt_vi.s16, rt_vi.s16));
                    case mval::VK_S32: return mval::push_s32(ipow(lt_vi.s32, rt_vi.s32));
                    case mval::VK_S64: return mval::push_s64(ipow(lt_vi.s64, rt_vi.s64));
                    case mval::VK_F32: return mval::push_f32(std::powf(lt_vi.f32, rt_vi.f32));
                    case mval::VK_F64: return mval::push_f64(std::powf(lt_vi.f64, rt_vi.f64));
                    default: {
                        throw new Panic(
                            "ERROR: invalid arguments to BinOp '^' (exponent)"
                        );
                    }
                }
            }
            case BINARY_MUL: {
                switch (vk) {
                    case mval::VK_U8: return mval::push_u8(lt_vi.u8 * rt_vi.u8);
                    case mval::VK_U16: return mval::push_u16(lt_vi.u16 * rt_vi.u16);
                    case mval::VK_U32: return mval::push_u32(lt_vi.u32 * rt_vi.u32);
                    case mval::VK_U64: return mval::push_u64(lt_vi.u64 * rt_vi.u64);
                    case mval::VK_S8: return mval::push_s8(lt_vi.s8 * rt_vi.s8);
                    case mval::VK_S16: return mval::push_s16(lt_vi.s16 * rt_vi.s16);
                    case mval::VK_S32: return mval::push_s32(lt_vi.s32 * rt_vi.s32);
                    case mval::VK_S64: return mval::push_s64(lt_vi.s64 * rt_vi.s64);
                    case mval::VK_F32: return mval::push_f32(lt_vi.f32 * rt_vi.f32);
                    case mval::VK_F64: return mval::push_f64(lt_vi.f64 * rt_vi.f64);
                    default: {
                        throw new Panic("ERROR: invalid arguments to BinOp '*' (multiply)");
                    }
                }
            }
            case BINARY_DIV: {
                switch (vk) {
                    case mval::VK_U8: return mval::push_u8(lt_vi.u8 * rt_vi.u8);
                    case mval::VK_U16: return mval::push_u16(lt_vi.u16 * rt_vi.u16);
                    case mval::VK_U32: return mval::push_u32(lt_vi.u32 * rt_vi.u32);
                    case mval::VK_U64: return mval::push_u64(lt_vi.u64 * rt_vi.u64);
                    case mval::VK_S8: return mval::push_s8(lt_vi.s8 * rt_vi.s8);
                    case mval::VK_S16: return mval::push_s16(lt_vi.s16 * rt_vi.s16);
                    case mval::VK_S32: return mval::push_s32(lt_vi.s32 * rt_vi.s32);
                    case mval::VK_S64: return mval::push_s64(lt_vi.s64 * rt_vi.s64);
                    case mval::VK_F32: return mval::push_f32(lt_vi.f32 * rt_vi.f32);
                    case mval::VK_F64: return mval::push_f64(lt_vi.f64 * rt_vi.f64);
                    default: {
                        throw new Panic("ERROR: invalid arguments to BinOp '^' (exponent)");
                    }
                }
            }
            case BINARY_REM: {
                switch (vk) {
                    case mval::VK_U8: return mval::push_u8(lt_vi.u8 % rt_vi.u8);
                    case mval::VK_U16: return mval::push_u16(lt_vi.u16 % rt_vi.u16);
                    case mval::VK_U32: return mval::push_u32(lt_vi.u32 % rt_vi.u32);
                    case mval::VK_U64: return mval::push_u64(lt_vi.u64 % rt_vi.u64);
                    case mval::VK_S8: return mval::push_s8(lt_vi.s8 % rt_vi.s8);
                    case mval::VK_S16: return mval::push_s16(lt_vi.s16 % rt_vi.s16);
                    case mval::VK_S32: return mval::push_s32(lt_vi.s32 % rt_vi.s32);
                    case mval::VK_S64: return mval::push_s64(lt_vi.s64 % rt_vi.s64);
                    case mval::VK_F32: return mval::push_f32(std::fmod(lt_vi.f32, rt_vi.f32));
                    case mval::VK_F64: return mval::push_f64(std::fmod(lt_vi.f64, rt_vi.f64));
                    default: {
                        throw new Panic("ERROR: invalid arguments to BinOp '%' (exponent)");
                    }
                }
            }
            case BINARY_ADD: {
                switch (vk) {
                    case mval::VK_U8: return mval::push_u8(lt_vi.u8 + rt_vi.u8);
                    case mval::VK_U16: return mval::push_u16(lt_vi.u16 + rt_vi.u16);
                    case mval::VK_U32: return mval::push_u32(lt_vi.u32 + rt_vi.u32);
                    case mval::VK_U64: return mval::push_u64(lt_vi.u64 + rt_vi.u64);
                    case mval::VK_S8: return mval::push_s8(lt_vi.s8 + rt_vi.s8);
                    case mval::VK_S16: return mval::push_s16(lt_vi.s16 + rt_vi.s16);
                    case mval::VK_S32: return mval::push_s32(lt_vi.s32 + rt_vi.s32);
                    case mval::VK_S64: return mval::push_s64(lt_vi.s64 + rt_vi.s64);
                    case mval::VK_F32: return mval::push_f32(lt_vi.f32 + rt_vi.f32);
                    case mval::VK_F64: return mval::push_f64(lt_vi.f64 + rt_vi.f64);
                    default: {
                        throw new Panic("ERROR: invalid arguments to BinOp '+' (add)");
                    }
                }
            }
            case BINARY_SUB: {
                switch (vk) {
                    case mval::VK_U8: return mval::push_u8(lt_vi.u8 - rt_vi.u8);
                    case mval::VK_U16: return mval::push_u16(lt_vi.u16 - rt_vi.u16);
                    case mval::VK_U32: return mval::push_u32(lt_vi.u32 - rt_vi.u32);
                    case mval::VK_U64: return mval::push_u64(lt_vi.u64 - rt_vi.u64);
                    case mval::VK_S8: return mval::push_s8(lt_vi.s8 - rt_vi.s8);
                    case mval::VK_S16: return mval::push_s16(lt_vi.s16 - rt_vi.s16);
                    case mval::VK_S32: return mval::push_s32(lt_vi.s32 - rt_vi.s32);
                    case mval::VK_S64: return mval::push_s64(lt_vi.s64 - rt_vi.s64);
                    case mval::VK_F32: return mval::push_f32(lt_vi.f32 - rt_vi.f32);
                    case mval::VK_F64: return mval::push_f64(lt_vi.f64 - rt_vi.f64);
                    default: {
                        throw new Panic("ERROR: invalid arguments to BinOp '-' (subtract)");
                    }
                }
            }
            case BINARY_LT: {
                switch (vk) {
                    case mval::VK_U8: return mval::push_u8(lt_vi.u8 < rt_vi.u8);
                    case mval::VK_U16: return mval::push_u16(lt_vi.u16 < rt_vi.u16);
                    case mval::VK_U32: return mval::push_u32(lt_vi.u32 < rt_vi.u32);
                    case mval::VK_U64: return mval::push_u64(lt_vi.u64 < rt_vi.u64);
                    case mval::VK_S8: return mval::push_s8(lt_vi.s8 < rt_vi.s8);
                    case mval::VK_S16: return mval::push_s16(lt_vi.s16 < rt_vi.s16);
                    case mval::VK_S32: return mval::push_s32(lt_vi.s32 < rt_vi.s32);
                    case mval::VK_S64: return mval::push_s64(lt_vi.s64 < rt_vi.s64);
                    case mval::VK_F32: return mval::push_f32(lt_vi.f32 < rt_vi.f32);
                    case mval::VK_F64: return mval::push_f64(lt_vi.f64 < rt_vi.f64);
                    default: {
                        throw new Panic("ERROR: invalid arguments to BinOp '%' (exponent)");
                    }
                }
            }
            case BINARY_LE: {
                switch (vk) {
                    case mval::VK_U8: return mval::push_u8(lt_vi.u8 <= rt_vi.u8);
                    case mval::VK_U16: return mval::push_u16(lt_vi.u16 <= rt_vi.u16);
                    case mval::VK_U32: return mval::push_u32(lt_vi.u32 <= rt_vi.u32);
                    case mval::VK_U64: return mval::push_u64(lt_vi.u64 <= rt_vi.u64);
                    case mval::VK_S8: return mval::push_s8(lt_vi.s8 <= rt_vi.s8);
                    case mval::VK_S16: return mval::push_s16(lt_vi.s16 <= rt_vi.s16);
                    case mval::VK_S32: return mval::push_s32(lt_vi.s32 <= rt_vi.s32);
                    case mval::VK_S64: return mval::push_s64(lt_vi.s64 <= rt_vi.s64);
                    case mval::VK_F32: return mval::push_f32(lt_vi.f32 <= rt_vi.f32);
                    case mval::VK_F64: return mval::push_f64(lt_vi.f64 <= rt_vi.f64);
                    default: {
                        throw new Panic("ERROR: invalid arguments to BinOp '%' (exponent)");
                    }
                }
            }
            case BINARY_GT: {
                switch (vk) {
                    case mval::VK_U8: return mval::push_u8(lt_vi.u8 > rt_vi.u8);
                    case mval::VK_U16: return mval::push_u16(lt_vi.u16 > rt_vi.u16);
                    case mval::VK_U32: return mval::push_u32(lt_vi.u32 > rt_vi.u32);
                    case mval::VK_U64: return mval::push_u64(lt_vi.u64 > rt_vi.u64);
                    case mval::VK_S8: return mval::push_s8(lt_vi.s8 > rt_vi.s8);
                    case mval::VK_S16: return mval::push_s16(lt_vi.s16 > rt_vi.s16);
                    case mval::VK_S32: return mval::push_s32(lt_vi.s32 > rt_vi.s32);
                    case mval::VK_S64: return mval::push_s64(lt_vi.s64 > rt_vi.s64);
                    case mval::VK_F32: return mval::push_f32(lt_vi.f32 > rt_vi.f32);
                    case mval::VK_F64: return mval::push_f64(lt_vi.f64 > rt_vi.f64);
                    default: {
                        throw new Panic("ERROR: invalid arguments to BinOp '%' (exponent)");
                    }
                }
            }
            case BINARY_GE: {
                switch (vk) {
                    case mval::VK_U8: return mval::push_u8(lt_vi.u8 >= rt_vi.u8);
                    case mval::VK_U16: return mval::push_u16(lt_vi.u16 >= rt_vi.u16);
                    case mval::VK_U32: return mval::push_u32(lt_vi.u32 >= rt_vi.u32);
                    case mval::VK_U64: return mval::push_u64(lt_vi.u64 >= rt_vi.u64);
                    case mval::VK_S8: return mval::push_s8(lt_vi.s8 >= rt_vi.s8);
                    case mval::VK_S16: return mval::push_s16(lt_vi.s16 >= rt_vi.s16);
                    case mval::VK_S32: return mval::push_s32(lt_vi.s32 >= rt_vi.s32);
                    case mval::VK_S64: return mval::push_s64(lt_vi.s64 >= rt_vi.s64);
                    case mval::VK_F32: return mval::push_f32(lt_vi.f32 >= rt_vi.f32);
                    case mval::VK_F64: return mval::push_f64(lt_vi.f64 >= rt_vi.f64);
                    default: {
                        throw new Panic("ERROR: invalid arguments to BinOp '%' (exponent)");
                    }
                }
            }
            case BINARY_EQ: {
                auto truth_val = mval::equals(lt_arg_val_id, rt_arg_val_id);
                return mval::push_u1(truth_val);
            }
            case BINARY_NE: {
                auto truth_val = !mval::equals(lt_arg_val_id, rt_arg_val_id);
                return mval::push_u1(truth_val);
            }
            case BINARY_LOGICAL_AND: {
                switch (vk) {
                    case mval::VK_U1: {
                        return mval::push_u1(lt_vi.u1 & rt_vi.u1);
                    }
                    default: {
                        throw new Panic(
                            "ERROR: invalid arguments to BinOp "
                            "'and' (logical and)"
                        );
                    }
                }
            }
            case BINARY_LOGICAL_OR: {
                switch (vk) {
                    case mval::VK_U1: {
                        return mval::push_u1(lt_vi.u1 | rt_vi.u1);
                    }
                    default: {
                        throw new Panic(
                            "ERROR: invalid arguments to BinOp 'or' "
                            "(logical or)");
                    }
                }
            }
        }
    }
    static mval::VID eval_mono_ite_exp(mast::ExpID ite_exp, stack::Stack* st, MonoModID mono_mod_id) {
        auto info = &mast::get_info_ptr(ite_exp)->exp_if_then_else;
        auto cond_val_id = eval_mono_exp(info->cond_exp, st, mono_mod_id);
        auto cond_vk = mval::value_kind(cond_val_id);
        if (cond_vk != mval::VK_U1) {
            throw new Panic("ERROR: expected boolean `cond` exp in ITE");
        }
        auto cond_vv = mval::value_info(cond_val_id).u1;

        return (
            (cond_vv) ?
            eval_mono_exp(info->then_exp, st, mono_mod_id) :
            eval_mono_exp(info->else_exp, st, mono_mod_id)
        );
    }
    static mval::VID eval_mono_get_tuple_field_exp(mast::ExpID exp_id, stack::Stack* st, MonoModID mono_mod_id) {
        auto info = &mast::get_info_ptr(exp_id)->exp_get_tuple_field;
        auto tuple_val_id = eval_mono_exp(info->tuple_exp_id, st, mono_mod_id);
        auto index = info->index;
        auto opt_res = mval::get_seq_elem2(tuple_val_id, index);
        if (opt_res.has_value()) {
            return opt_res.value();
        } else {
            throw new Panic("ERROR: sequence index out of bounds");
        }
    }
    static mval::VID eval_mono_get_module_field_exp(mast::ExpID exp_id, stack::Stack* st, MonoModID mono_mod_id) {
        auto info = &mast::get_info_ptr(exp_id)->exp_get_mono_module_field;
        GDefID field_def_id = modules::get_mono_mod_field_at(info->template_id, info->field_index);
        return eval_def_v(field_def_id, st, mono_mod_id);
    }
    static mval::VID eval_mono_lambda_exp(
        mast::ExpID exp_id, 
        stack::Stack* st,
        MonoModID mono_mod_id
    ) {
        auto info = &mast::get_info_ptr(exp_id)->exp_lambda;

        // copying argument name array:
        uint32_t arg_name_count = info->arg_name_count;
        auto copied_arg_name_array = new intern::IntStr[arg_name_count];
        {
            for (uint32_t i = 0; i < arg_name_count; i++) {
                copied_arg_name_array[i] = info->arg_name_array[i];
            }
        }

        // evaluating and binding each enclosed non-local/contextual identifier:
        uint32_t enclosed_name_count = info->ctx_enclosed_name_count;
        auto enclosed_bind_array = new mval::CtxEnclosedId[enclosed_name_count];
        {
            for (uint32_t i = 0; i < enclosed_name_count; i++) {
                intern::IntStr enclosed_name = info->ctx_enclosed_name_array[i];
                bool is_name_tid_not_vid = intern::is_interned_string_tid_not_vid(enclosed_name);

                enclosed_bind_array[i].name = enclosed_name;
                enclosed_bind_array[i].target = (
                    (is_name_tid_not_vid) ?
                    eval_mono_ts(stack::lookup_t_in_stack(st, enclosed_name), st, mono_mod_id) :
                    eval_mono_exp(stack::lookup_v_in_stack(st, enclosed_name), st, mono_mod_id)
                );
            }
        }

        // referencing the body MAST expression (effectively providing instructions in padded bytecode)
        auto body_exp = info->body_exp;

        // creating and returning function value:
        return mval::push_function(
            arg_name_count,
            copied_arg_name_array,
            enclosed_name_count,
            enclosed_bind_array,
            body_exp,
            mono_mod_id
        );
    }
    mval::VID eval_mono_chain_exp(mast::ExpID exp_id, stack::Stack* st, MonoModID mono_mod_id) {
        auto info = &mast::get_info_ptr(exp_id)->exp_chain;
        
        stack::push_stack_frame(st);
        mval::VID res;
        {
            auto elem_count = info->prefix_elem_count;
            auto elem_array = info->prefix_elem_array;
            for (size_t i = 0; i < elem_count; i++) {
                eval_mono_elem(elem_array[i], st, mono_mod_id);
            }
            
            res = eval_mono_exp(info->ret_exp_id, st, mono_mod_id);
        }
        stack::pop_stack_frame(st);

        return res;
    }
    static mval::VID help_eval_mono_cast_exp__to_float(mval::VID src_vid, int dst_width_in_bits);
    static mval::VID help_eval_mono_cast_exp__to_int(mval::VID src_vid, int dst_width_in_bits, bool dst_is_signed);
    static mval::VID help_eval_mono_cast_exp__to_tuple(mtype::TID constructor_tid, mval::VID initializer_vid);
    static mval::VID help_eval_mono_cast_exp__to_array(mtype::TID constructor_tid, mval::VID initializer_vid);
    static mval::VID help_eval_mono_cast_exp__to_slice(mtype::TID constructor_tid, mval::VID initializer_vid);
    static mval::VID help_eval_mono_cast_exp__to_pointer(mtype::TID constructor_tid, mval::VID initializer_vid);
    static mval::VID help_cast(mtype::TID constructor_tid, mval::VID initializer_vid) {
        // std::cout << "DEBUG: Invoking `help_cast`" << std::endl;
        
        auto constructor_tid_kind = mtype::kind_of_tid(constructor_tid);
        switch (constructor_tid_kind)
        {
            // Unit, String: trivial cast works since passes type-check.
            case mtype::TK_UNIT: return initializer_vid;
            case mtype::TK_STRING: return initializer_vid;

            // Cast_ToInt:
            case mtype::TK_S8: return help_eval_mono_cast_exp__to_int(initializer_vid, 8, true);
            case mtype::TK_S16: return help_eval_mono_cast_exp__to_int(initializer_vid, 16, true);
            case mtype::TK_S32: return help_eval_mono_cast_exp__to_int(initializer_vid, 32, true);
            case mtype::TK_S64: return help_eval_mono_cast_exp__to_int(initializer_vid, 64, true);   
            case mtype::TK_U1: return help_eval_mono_cast_exp__to_int(initializer_vid, 1, false);
            case mtype::TK_U8: return help_eval_mono_cast_exp__to_int(initializer_vid, 8, false);
            case mtype::TK_U16: return help_eval_mono_cast_exp__to_int(initializer_vid, 16, false);
            case mtype::TK_U32: return help_eval_mono_cast_exp__to_int(initializer_vid, 32, false);
            case mtype::TK_U64: return help_eval_mono_cast_exp__to_int(initializer_vid, 64, false);
            
            // Cast_ToFloat:
            case mtype::TK_F32: return help_eval_mono_cast_exp__to_float(initializer_vid, 32);
            case mtype::TK_F64: return help_eval_mono_cast_exp__to_float(initializer_vid, 64);

            // Cast_To{Array|Slice|Pointer}:
            case mtype::TK_ARRAY: return help_eval_mono_cast_exp__to_array(constructor_tid, initializer_vid);
            case mtype::TK_SLICE: return help_eval_mono_cast_exp__to_slice(constructor_tid, initializer_vid);
            case mtype::TK_POINTER: return help_eval_mono_cast_exp__to_pointer(constructor_tid, initializer_vid);

            // Cast_ToTuple:
            case mtype::TK_TUPLE: return help_eval_mono_cast_exp__to_tuple(constructor_tid, initializer_vid);

            case mtype::TK_ERROR:
            default:
            {
                throw new Panic("Unknown/invalid constructor type-kind in CastOp");
            }
        }
    }
    mval::VID help_eval_mono_cast_exp__to_int(
        mval::VID src_vid, 
        int dst_width_in_bits, 
        bool dst_is_signed
    ) {
        mval::ValueKind src_val_kind = mval::value_kind(src_vid);
        
        // first, loading the value to convert into a `size_t` word:
        size_t val_bit_pattern; {
            switch (src_val_kind) {
                case mval::VK_S8: { val_bit_pattern = mval::value_info(src_vid).s8; } break;
                case mval::VK_S16: { val_bit_pattern = mval::value_info(src_vid).s16; } break;
                case mval::VK_S32: { val_bit_pattern = mval::value_info(src_vid).s32; } break;
                case mval::VK_S64: { val_bit_pattern = mval::value_info(src_vid).s64; } break;

                case mval::VK_U1: { val_bit_pattern = mval::value_info(src_vid).u1; } break;
                case mval::VK_U8: { val_bit_pattern = mval::value_info(src_vid).u8; } break;
                case mval::VK_U16: { val_bit_pattern = mval::value_info(src_vid).u16; } break;
                case mval::VK_U32: { val_bit_pattern = mval::value_info(src_vid).u32; } break;
                case mval::VK_U64: { val_bit_pattern = mval::value_info(src_vid).u64; } break;
                
                case mval::VK_F32: { val_bit_pattern = static_cast<size_t>(mval::value_info(src_vid).f32); } break;
                case mval::VK_F64: { val_bit_pattern = static_cast<size_t>(mval::value_info(src_vid).f64); } break;

                default:
                {
                    throw new Panic("NotImplemented: invalid Cast_ToInt operation");
                }
            }
        }

        // next, converting this word into the desired type and returning:
        if (dst_is_signed) {
            switch (dst_width_in_bits) {
                case 8: return mval::push_s8(static_cast<int8_t>(val_bit_pattern));
                case 16: return mval::push_s16(static_cast<int16_t>(val_bit_pattern));
                case 32: return mval::push_s32(static_cast<int32_t>(val_bit_pattern));
                case 64: return mval::push_s64(static_cast<int64_t>(val_bit_pattern));
                default: 
                {
                    throw new Panic("NotImplemented: unknown dst_width_in_bits for Cast op with SignedInt dst");
                }
            }
        } else {
            switch (dst_width_in_bits) {
                case 1: return mval::push_u1(!!val_bit_pattern);
                case 8: return mval::push_u8(static_cast<uint8_t>(val_bit_pattern));
                case 16: return mval::push_u16(static_cast<uint16_t>(val_bit_pattern));
                case 32: return mval::push_u32(static_cast<uint32_t>(val_bit_pattern));
                case 64: return mval::push_u64(static_cast<uint64_t>(val_bit_pattern));
                default:
                {
                    throw new Panic("NotImplemented: unknown dst_width_in_bits for Cast op with UnsignedInt dst");
                }
            }
        }
    }
    mval::VID help_eval_mono_cast_exp__to_float(
        mval::VID src_vid, 
        int dst_width_in_bits
    ) {
        mval::ValueKind src_val_kind = mval::value_kind(src_vid);
        
        // first, loading the value to convert into a `size_t` word:
        double val_bit_pattern; {
            switch (src_val_kind) {
                case mval::VK_S8: { val_bit_pattern = double(mval::value_info(src_vid).s8); } break;
                case mval::VK_S16: { val_bit_pattern = double(mval::value_info(src_vid).s16); } break;
                case mval::VK_S32: { val_bit_pattern = double(mval::value_info(src_vid).s32); } break;
                case mval::VK_S64: { val_bit_pattern = double(mval::value_info(src_vid).s64); } break;

                case mval::VK_U1: { val_bit_pattern = double(mval::value_info(src_vid).u1); } break;
                case mval::VK_U8: { val_bit_pattern = double(mval::value_info(src_vid).u8); } break;
                case mval::VK_U16: { val_bit_pattern = double(mval::value_info(src_vid).u16); } break;
                case mval::VK_U32: { val_bit_pattern = double(mval::value_info(src_vid).u32); } break;
                case mval::VK_U64: { val_bit_pattern = double(mval::value_info(src_vid).u64); } break;
                
                case mval::VK_F32: { val_bit_pattern = double(mval::value_info(src_vid).f32); } break;
                case mval::VK_F64: { val_bit_pattern = double(mval::value_info(src_vid).f64); } break;

                default:
                {
                    throw new Panic("NotImplemented: invalid Cast_ToFloat operation");
                }
            }
        }

        // next, converting this word into the desired type and returning:
        {
            switch (dst_width_in_bits) {
                case 32: return mval::push_f32(static_cast<float>(val_bit_pattern));
                case 64: return mval::push_f64(static_cast<double>(val_bit_pattern));
                default: 
                {
                    throw new Panic("NotImplemented: unknown dst_width_in_bits for Cast op with SignedInt dst");
                }
            }
        }
    }
    mval::VID help_eval_mono_cast_exp__to_tuple(mtype::TID constructor_tid, mval::VID initializer_vid) {
        mval::ValueKind initializer_value_kind = mval::value_kind(initializer_vid);

        if (initializer_value_kind != mval::VK_TUPLE) {
            throw new Panic("Invalid Cast_ToTuple exp argument");
        }
        
        auto seq_info_index = mval::value_info(initializer_vid).sequence_info_index;

        // verifying that the constructor type and initializer value have the same element-count:
        auto initializer_count = mval::get_seq_count(seq_info_index);
        auto constructor_count = mtype::get_tuple_count(constructor_tid);
        if (initializer_count != constructor_count) {
            std::cout 
                << "Initializer count: " << initializer_count << std::endl
                << "Constructor count: " << constructor_count << std::endl;
            std::cout.flush();
            throw new Panic("Invalid Cast_ToTuple exp argument: mismatched tuple counts");
        }
        
        // recursively converting each element data-type:
        auto elem_item_count = initializer_count;
        auto elem_item_array = new mval::VID[elem_item_count];
        arg_list::ArgListID remaining_arg_list = mtype::get_tuple_arg_list(constructor_tid);
        for (size_t i = 0; i < elem_item_count; i++) {
            // removing the next TID from the arg-list, which stores IDs in reverse-order:
            assert(remaining_arg_list != arg_list::EMPTY_ARG_LIST);
            mtype::TID this_arg_tid = arg_list::head(remaining_arg_list);
            remaining_arg_list = arg_list::tail(remaining_arg_list);

            // acquiring the corresponding VID from the initializer:
            mval::VID this_arg_vid = mval::get_seq_elem2(initializer_vid, i).value_or(mval::NULL_VID);
            assert(this_arg_vid != mval::NULL_VID);

            // converting and storing on `elem_item_array`, the output array:
            elem_item_array[i] = help_cast(this_arg_tid, this_arg_vid);
        }
        return mval::push_tuple(elem_item_count, elem_item_array);
    }
    mval::VID help_eval_mono_cast_exp__to_array(mtype::TID constructor_tid, mval::VID initializer_vid) {
        throw new Panic("NotImplemented: help_eval_mono_cast_exp__to_array");
        // only accepts arrays
    }
    mval::VID help_eval_mono_cast_exp__to_slice(mtype::TID constructor_tid, mval::VID initializer_vid) {
        throw new Panic("NotImplemented: help_eval_mono_cast_exp__to_slice");
        // only accepts slices
        //  - cannot convert arrays to slices because of allocation constraints
    }
    mval::VID help_eval_mono_cast_exp__to_pointer(mtype::TID constructor_tid, mval::VID initializer_vid) {
        throw new Panic("NotImplemented: help_eval_mono_cast_exp__to_pointer");
        // only accepts pointers, BUT
        // can be mutable or immutable.
    }
    mval::VID eval_mono_cast_exp(mast::ExpID exp_id, stack::Stack* st, MonoModID mono_mod_id) {
        auto info = &mast::get_info_ptr(exp_id)->exp_cast;

        // std::cout << "DEBUG: CastExp (1/3) Evaluating constructor_tid" << std::endl;
        auto constructor_tid = eval_mono_ts(info->ts_id, st, mono_mod_id);
        // std::cout.flush();

        // std::cout << "DEBUG: CastExp (2/3) Evaluating initializer_vid" << std::endl;
        auto initializer_vid = eval_mono_exp(info->exp_id, st, mono_mod_id);
        // std::cout.flush();

        // std::cout << "DEBUG: CastExp (3/3) Invoking `help_cast` to do the rest..." << std::endl;
        // std::cout.flush();
        return help_cast(constructor_tid, initializer_vid);
    }
    mval::VID eval_mono_tuple_exp(mast::ExpID exp_id, stack::Stack* st, MonoModID mono_mod_id) {
        auto info = &mast::get_info_ptr(exp_id)->exp_tuple;

        size_t item_count = info->item_count;
        mast::ExpID* old_item_array = info->item_array;
        mval::VID* new_item_array = new mval::VID[item_count];
        for (size_t i = 0; i < item_count; i++) {
            new_item_array[i] = eval_mono_exp(old_item_array[i], st, mono_mod_id);
        }

        return mval::push_tuple(item_count, new_item_array);
    }
    mval::VID eval_mono_exp(mast::ExpID exp_id, stack::Stack* st, MonoModID mono_mod_id) {
        mast::NodeKind exp_kind = mast::get_node_kind(exp_id);
        switch (exp_kind) {
            case mast::EXP_UNIT: {
                return mval::get_unit();
            } break;
            case mast::EXP_INT: {
                return eval_mono_int_exp(exp_id);
            } break;
            case mast::EXP_FLOAT: {
                return eval_mono_float_exp(exp_id);
            } break;
            case mast::EXP_STRING: {
                return eval_mono_string_exp(exp_id);
            } break;
            case mast::EXP_LID: {
                auto info = &mast::get_info_ptr(exp_id)->exp_lid;
                return stack::lookup_v_in_stack(st, info->int_str_id);
            }
            case mast::EXP_GID: {
                auto info = &mast::get_info_ptr(exp_id)->exp_gid;
                return eval_def_v(info->def_id, st, mono_mod_id);
            } break;
            case mast::EXP_FUNC_CALL: {
                return eval_mono_func_call_exp(exp_id, st, mono_mod_id);
            } break;
            case mast::EXP_UNARY_OP: {
                return eval_mono_unary_op_exp(exp_id, st, mono_mod_id);
            } break;
            case mast::EXP_BINARY_OP: {
                return eval_mono_binary_op_exp(exp_id, st, mono_mod_id);
            } break;
            case mast::EXP_IF_THEN_ELSE: {
                return eval_mono_ite_exp(exp_id, st, mono_mod_id);
            } break;
            case mast::EXP_GET_TUPLE_FIELD: {
                return eval_mono_get_tuple_field_exp(exp_id, st, mono_mod_id);
            } break;
            case mast::EXP_GET_MONO_MODULE_FIELD: {
                return eval_mono_get_module_field_exp(exp_id, st, mono_mod_id);
            } break;
            case mast::EXP_LAMBDA: {
                return eval_mono_lambda_exp(exp_id, st, mono_mod_id);
            } break;
            case mast::EXP_ALLOCATE_ONE: {
                throw new Panic("NotImplemented: eval_mono EXP_ALLOCATE_ONE");
            } break;
            case mast::EXP_ALLOCATE_MANY: {
                // should always return an array
                throw new Panic("NotImplemented: eval_mono EXP_ALLOCATE_MANY");
            } break;
            case mast::EXP_CHAIN: {
                return eval_mono_chain_exp(exp_id, st, mono_mod_id);
            } break;
            
            case mast::EXP_CAST: {
                return eval_mono_cast_exp(exp_id, st, mono_mod_id);
            }

            case mast::EXP_TUPLE: {
                return eval_mono_tuple_exp(exp_id, st, mono_mod_id);
            }

            case mast::EXP_GET_POLY_MODULE_FIELD:
            {
                throw new Panic("EXP_GET_POLY_MODULE_FIELD remains after `p2m`");
            }
            default: 
            {
                std::cout << "INFO: Invalid arg exp kind = " << exp_kind << std::endl;
                throw new Panic("Invalid arg exp to eval_mono_exp");
            }
        }
        throw new Panic("NotImplemented: `eval_mono_exp` for valid exp_id");
    }

}

//
// Interface:
//

namespace monomorphizer::eval {

    mtype::TID eval_type(mast::TypeSpecID ts_id, sub::Substitution* s, MonoModID mono_mod_id) {
        return eval_poly_ts(ts_id, s, mono_mod_id);
    }
    mval::VID eval_exp(mast::ExpID exp_id, sub::Substitution* s, MonoModID mono_mod_id) {
        return eval_poly_exp(exp_id, s, mono_mod_id);
    }

}
