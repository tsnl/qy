#include "eval.hh"

#include "mast.hh"
#include "panic.hh"
#include "sub.hh"
#include "defs.hh"

//
// Implementation: forward declarations:
//

namespace monomorphizer::eval {
    
    mast::TypeSpecID monomorphize_type_spec(
        mast::TypeSpecID mast_ts_id,
        sub::Substitution* sub
    );
    mast::ExpID monomorphize_exp(
        mast::ExpID mast_exp_id,
        sub::Substitution* sub
    );
}

//
// Implementation: monomorphize_it family
//

namespace monomorphizer::eval {

    mast::TypeSpecID monomorphize_type_spec(
        mast::TypeSpecID mast_ts_id,
        sub::Substitution* s
    ) {
        auto ts_kind = mast::get_node_kind(mast_ts_id);
        switch (ts_kind) {
            case mast::NodeKind::TS_ID: {
                // IDs accessed from within a monomorphic module are always
                // monomorphic.
                // However, this substitution may require us to rewrite this ID
                // with another.
                auto info = mast::get_info_ptr(mast_ts_id)->ts_id;
                DefID old_def_id = info.def_id;
                defs::DefKind old_def_kind = defs::get_def_kind(old_def_id);
                switch (old_def_kind) {
                    case defs::DefKind::CONST_TOT_TID: 
                    {
                        // no substitution/copying needed
                        return mast_ts_id;
                    }
                    case defs::DefKind::CONST_TS:
                    case defs::DefKind::BV_TS:
                    {
                        DefID new_def_id = sub::rw_def_id(s, old_def_id);
                        if (new_def_id == old_def_id) {
                            return mast_ts_id;
                        } else {
                            return mast::new_id_ts(new_def_id);
                        }
                    }
                    default:
                    {
                        throw new Panic("Invalid DefID in TypeSpecID");
                    }
                }
            } break;
            case mast::NodeKind::TS_PTR: {
                auto info = mast::get_info_ptr(mast_ts_id)->ts_ptr;
                auto old_ptd_ts = info.ptd_ts;
                auto ptd_ts = monomorphize_type_spec(old_ptd_ts, s);
                bool contents_is_mut = info.contents_is_mut;
                if (old_ptd_ts != ptd_ts) {
                    return mast::new_ptr_ts(ptd_ts, contents_is_mut);
                } else {
                    return mast_ts_id;
                }
            } break;
            case mast::NodeKind::TS_ARRAY: {
                auto info = mast::get_info_ptr(mast_ts_id)->ts_array;
                auto old_ptd_ts = info.ptd_ts;
                auto ptd_ts = monomorphize_type_spec(old_ptd_ts, s);
                bool contents_is_mut = info.contents_is_mut;
                auto old_count_exp = info.count_exp;
                auto count_exp = monomorphize_exp(old_count_exp, s);
                if (old_ptd_ts != ptd_ts || old_count_exp != count_exp) {
                    return mast::new_array_ts(
                        ptd_ts, count_exp, 
                        contents_is_mut
                    );
                } else {
                    return mast_ts_id;
                }
            } break;
            case mast::NodeKind::TS_SLICE: {
                auto info = mast::get_info_ptr(mast_ts_id)->ts_slice;
                auto old_ptd_ts = info.ptd_ts;
                auto ptd_ts = monomorphize_type_spec(old_ptd_ts, s);
                bool contents_is_mut = info.contents_is_mut;
                if (old_ptd_ts != ptd_ts) {
                    return mast::new_slice_ts(ptd_ts, contents_is_mut);
                } else {
                    return mast_ts_id;
                }
            } break;
            case mast::NodeKind::TS_TUPLE: {
                auto info = mast::get_info_ptr(mast_ts_id)->ts_tuple;

                size_t const elem_count = info.elem_ts_count;
                auto new_elem_ts_array = new mast::TypeSpecID[elem_count];
                bool any_elem_changed = false;
                for (size_t i = 0; i < elem_count; i++) {
                    auto old_ts = info.elem_ts_array[i];
                    auto new_ts = monomorphize_type_spec(old_ts, s);
                    
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
            case mast::NodeKind::TS_FUNC_SGN: {
                auto info = &mast::get_info_ptr(mast_ts_id)->ts_func_sgn;

                auto old_arg_ts = info->arg_ts;
                auto old_ret_ts = info->ret_ts;

                auto new_arg_ts = monomorphize_type_spec(old_arg_ts, s);
                auto new_ret_ts = monomorphize_type_spec(old_ret_ts, s);
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
            case mast::NodeKind::TS_GET_MONO_MODULE_FIELD: {
                // preserved exactly as is
                return mast_ts_id;
            } break;
            case mast::NodeKind::TS_GET_POLY_MODULE_FIELD: {
                // instantiating the LHS module using the actual args given
                // todo: need to 'eval' the args
                throw new Panic("NotImplemented: GetPolyModuleField");
            } break;
            default: {
                throw new Panic("NotImplemented: unknown TS node kind");
            } break;
        }
    }

    mast::ExpID monomorphize_exp(
        mast::ExpID mast_exp_id,
        sub::Substitution* s
    ) {
        auto exp_kind = mast::get_node_kind(mast_exp_id);
        switch (exp_kind) {
            case mast::NodeKind::EXP_UNIT:
            case mast::NodeKind::EXP_INT:
            case mast::NodeKind::EXP_FLOAT: 
            case mast::NodeKind::EXP_STRING:
            {
                return mast_exp_id;
            } break;
            
            case mast::NodeKind::EXP_ID: {
                // IDs accessed from within a monomorphic module are always
                // monomorphic.
                // However, this substitution may require us to rewrite this ID
                // with another.
                auto info = &mast::get_info_ptr(mast_exp_id)->exp_id;
                DefID old_def_id = info->def_id;
                defs::DefKind old_def_kind = defs::get_def_kind(old_def_id);
                switch (old_def_kind) {
                    case defs::DefKind::CONST_TOT_VAL: 
                    {
                        // no substitution/copying needed
                        return mast_exp_id;
                    }
                    case defs::DefKind::CONST_EXP:
                    case defs::DefKind::BV_EXP:
                    {
                        // updating 
                        DefID new_def_id = sub::rw_def_id(s, old_def_id);
                        if (new_def_id == old_def_id) {
                            return mast_exp_id;
                        } else {
                            return mast::new_id_ts(new_def_id);
                        }
                    }
                    default:
                    {
                        throw new Panic("Invalid DefID in ExpID");
                    }
                }
            } break;

            case mast::NodeKind::EXP_FUNC_CALL: {
                auto info = &mast::get_info_ptr(mast_exp_id)->exp_call;
                
                auto old_fn_exp = info->called_fn;
                auto new_fn_exp = monomorphize_exp(old_fn_exp, s);

                auto old_arg_exp = info->arg_exp_id;
                auto new_arg_exp = monomorphize_exp(old_arg_exp, s);

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
            case mast::NodeKind::EXP_UNARY_OP: {
                auto info = &mast::get_info_ptr(mast_exp_id)->exp_unary;

                auto old_arg_exp = info->arg_exp;
                auto new_arg_exp = monomorphize_exp(old_arg_exp, s);

                auto unary_op = info->unary_op;

                if (old_arg_exp != new_arg_exp) {
                    return mast::new_unary_op_exp(unary_op, new_arg_exp);
                } else {
                    return mast_exp_id;
                }
            } break;
            case mast::NodeKind::EXP_BINARY_OP: {
                auto info = &mast::get_info_ptr(mast_exp_id)->exp_binary;

                auto binary_op = info->binary_op;

                auto old_lt_arg_exp = info->lt_arg_exp;
                auto new_lt_arg_exp = monomorphize_exp(old_lt_arg_exp, s);

                auto old_rt_arg_exp = info->rt_arg_exp;
                auto new_rt_arg_exp = monomorphize_exp(old_rt_arg_exp, s);

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

            case mast::NodeKind::EXP_IF_THEN_ELSE: {
                auto info = &mast::get_info_ptr(mast_exp_id)->exp_if_then_else;

                auto old_cond_exp = info->cond_exp;
                auto new_cond_exp = monomorphize_exp(old_cond_exp, s);

                auto old_then_exp = info->then_exp;
                auto new_then_exp = monomorphize_exp(old_then_exp, s);

                auto old_else_exp = info->else_exp;
                auto new_else_exp = monomorphize_exp(old_else_exp, s);

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

            case mast::NodeKind::EXP_GET_TUPLE_FIELD: {
                auto raw_info = mast::get_info_ptr(mast_exp_id);
                auto info = &raw_info->exp_get_tuple_field;

                auto old_tuple_exp = info->tuple_exp_id;
                auto new_tuple_exp = monomorphize_exp(old_tuple_exp, s);

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

            case mast::NodeKind::EXP_GET_POLY_MODULE_FIELD: {
                auto raw_info = mast::get_info_ptr(mast_exp_id);
                auto info = &raw_info->exp_get_poly_module_field;

                throw new Panic(
                    "NotImplemented: monomorphize_exp for GetPolyModuleField"
                );
            } break;
            case mast::NodeKind::EXP_GET_MONO_MODULE_FIELD: {
                auto raw_info = mast::get_info_ptr(mast_exp_id);
                auto info = &raw_info->exp_get_mono_module_field;

                auto old_tuple_exp = info->template_id;
                auto new_tuple_exp = monomorphize_exp(old_tuple_exp, s);

                auto index = info->field_index;

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
            case mast::NodeKind::EXP_LAMBDA: {
                auto raw_info = mast::get_info_ptr(mast_exp_id);
                auto info = &raw_info->exp_lambda;

                auto old_body_exp_id = info->body_exp;
                auto new_body_exp_id = monomorphize_exp(old_body_exp_id, s);

                bool changed = (old_body_exp_id != new_body_exp_id);
                if (changed) {
                    size_t arg_name_count = info->arg_name_count;
                    DefID* new_arg_name_array = new DefID[arg_name_count];
                    for (size_t i = 0; i < arg_name_count; i++) {
                        new_arg_name_array[i] = info->arg_name_array[i];
                        
                        // function args are never rewritten by monomorphization
                        // since they are bound, and hence never rewritten.
                        // DefID repl_def_name = sub::rw_def_id(
                        //     s,
                        //     orig_def_name
                        // );
                    }
                    return mast::new_lambda_exp(
                        arg_name_count, 
                        new_arg_name_array,
                        new_body_exp_id
                    );
                } else {
                    return mast_exp_id;
                }
            } break;
            case mast::NodeKind::EXP_ALLOCATE_ONE: {
                auto info = &mast::get_info_ptr(mast_exp_id)->exp_allocate_one;

                auto old_init_exp_id = info->stored_val_exp_id;
                auto new_init_exp_id = monomorphize_exp(old_init_exp_id, s);

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
            case mast::NodeKind::EXP_ALLOCATE_MANY: {
                auto info = &mast::get_info_ptr(mast_exp_id)->exp_allocate_many;

                auto old_init_exp_id = info->initializer_stored_val_exp_id;
                auto new_init_exp_id = monomorphize_exp(old_init_exp_id, s);

                auto old_count_exp_id = info->alloc_count_exp;
                auto new_count_exp_id = monomorphize_exp(new_init_exp_id, s);

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
            case mast::NodeKind::EXP_CHAIN: {
                auto info = &mast::get_info_ptr(mast_exp_id)->exp_chain;
                throw new Panic("NotImplemented: EXP_CHAIN");
            } break;
            default: {
                throw new Panic("NotImplemented: unknown exp kind");
            } break;
        }
    }

}

//
// Interface:
//

namespace monomorphizer::eval {

    mtype::MTypeID eval_type(mast::TypeSpecID ts_id) {
        // todo: implement me
    }

    mval::ValueID eval_exp(mast::ExpID exp_id) {
        // todo: implement me
    }

}
