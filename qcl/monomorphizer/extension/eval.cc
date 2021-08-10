#include "eval.hh"

#include <cmath>

#include "mast.hh"
#include "panic.hh"
#include "sub.hh"
#include "defs.hh"
#include "mtype.hh"
#include "mval.hh"
#include "mtype.hh"
#include "arg-list.hh"
#include "modules.hh"

//
// Implementation: forward declarations:
//

namespace monomorphizer::eval {
    
    mast::TypeSpecID p2m_ts(mast::TypeSpecID ts_id, sub::Substitution* s);
    mast::ExpID p2m_exp(mast::ExpID exp_id, sub::Substitution* s);

    mtype::TID eval_poly_ts(mast::TypeSpecID poly_ts, sub::Substitution* s);
    mtype::TID eval_poly_exp(mast::ExpID exp_id, sub::Substitution* s);
    
    mtype::TID eval_mono_ts(mast::TypeSpecID ts_id);
    mval::ValueID eval_mono_exp(mast::ExpID exp_id);
    
}

//
// Implementation: p2m: polymorphic to monomorphic
//

namespace monomorphizer::eval {

    mast::TypeSpecID p2m_ts(
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
                auto ptd_ts = p2m_ts(old_ptd_ts, s);
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
                auto ptd_ts = p2m_ts(old_ptd_ts, s);
                bool contents_is_mut = info.contents_is_mut;
                auto old_count_exp = info.count_exp;
                auto count_exp = p2m_exp(old_count_exp, s);
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
                auto ptd_ts = p2m_ts(old_ptd_ts, s);
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
                    auto new_ts = p2m_ts(old_ts, s);
                    
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

                auto new_arg_ts = p2m_ts(old_arg_ts, s);
                auto new_ret_ts = p2m_ts(old_ret_ts, s);
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
                auto raw_info = mast::get_info_ptr(mast_ts_id);
                auto info = &raw_info->ts_get_poly_module_field;
                
                auto poly_mod_id = info->template_id;
                auto arg_count = info->actual_arg_count;
                auto arg_array = info->actual_arg_array;

                // constructing an ArgList by iterating in reverse order:
                arg_list::ArgListID actual_arg_list = arg_list::EMPTY;
                for (size_t i = 0; i < arg_count; i++) {
                    auto arg_index = arg_count - (i + 1);
                    auto arg_node_id = arg_array[arg_index];

                    bool elem_is_exp = mast::is_node_exp_not_ts(arg_node_id);
                    if (elem_is_exp) {
                        auto elem_exp_id = arg_node_id;
                        auto elem_exp_val = eval_mono_exp(elem_exp_id);
                        actual_arg_list = arg_list::cons_val(
                            actual_arg_list, 
                            elem_exp_val
                        );
                    } else {
                        auto elem_ts_id = arg_node_id;
                        auto elem_ts_tid = eval_mono_ts(elem_ts_id);
                        actual_arg_list = arg_list::cons_tid(
                            actual_arg_list, 
                            elem_ts_id
                        );
                    }
                }
                auto mono_mod_id = modules::instantiate_poly_mod(
                    poly_mod_id,
                    actual_arg_list
                );
                return mast::new_get_mono_module_field_ts(
                    mono_mod_id,
                    info->ts_field_index
                );
            } break;
            default: {
                throw new Panic("NotImplemented: unknown TS node kind");
            } break;
        }
    }

    mast::ExpID p2m_exp(
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
                auto new_fn_exp = p2m_exp(old_fn_exp, s);

                auto old_arg_exp = info->arg_exp_id;
                auto new_arg_exp = p2m_exp(old_arg_exp, s);

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
                auto new_arg_exp = p2m_exp(old_arg_exp, s);

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
                auto new_lt_arg_exp = p2m_exp(old_lt_arg_exp, s);

                auto old_rt_arg_exp = info->rt_arg_exp;
                auto new_rt_arg_exp = p2m_exp(old_rt_arg_exp, s);

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
                auto new_cond_exp = p2m_exp(old_cond_exp, s);

                auto old_then_exp = info->then_exp;
                auto new_then_exp = p2m_exp(old_then_exp, s);

                auto old_else_exp = info->else_exp;
                auto new_else_exp = p2m_exp(old_else_exp, s);

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
                auto new_tuple_exp = p2m_exp(old_tuple_exp, s);

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
                    "NotImplemented: p2m_exp for GetPolyModuleField"
                );
            } break;
            case mast::NodeKind::EXP_GET_MONO_MODULE_FIELD: {
                auto raw_info = mast::get_info_ptr(mast_exp_id);
                auto info = &raw_info->exp_get_mono_module_field;

                auto old_tuple_exp = info->template_id;
                auto new_tuple_exp = p2m_exp(old_tuple_exp, s);

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
                auto new_body_exp_id = p2m_exp(old_body_exp_id, s);

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
                auto new_init_exp_id = p2m_exp(old_init_exp_id, s);

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
                auto new_init_exp_id = p2m_exp(old_init_exp_id, s);

                auto old_count_exp_id = info->alloc_count_exp;
                auto new_count_exp_id = p2m_exp(new_init_exp_id, s);

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
// Implementation:
//

namespace monomorphizer::eval {

    mtype::TID eval_def_t(DefID def_id) {
        defs::DefKind def_kind = defs::get_def_kind(def_id);
        switch (def_kind) {
            case defs::DefKind::CONST_TOT_TID: {
                return defs::load_id_from_def_id(def_id);
            } break;
            case defs::DefKind::CONST_TS: {
                auto stored_ts_id = defs::load_id_from_def_id(def_id);
                return eval_mono_ts(stored_ts_id);
            } break;
            case defs::DefKind::BV_TS: {
                throw new Panic(
                    "InputError: `eval_def_t` cannot eval a bound var"
                );
            } break;
            default: {
                throw new Panic(
                    "InputError: unknown DefKind in `eval_def_t`"
                );
            }
        }
    }

    mval::ValueID eval_def_v(DefID def_id) {
        defs::DefKind def_kind = defs::get_def_kind(def_id);
        switch (def_kind) {
            case defs::DefKind::CONST_TOT_VAL: {
                return defs::load_id_from_def_id(def_id);
            } break;
            case defs::DefKind::CONST_EXP: {
                auto stored_val_id = defs::load_id_from_def_id(def_id);
                return eval_mono_exp(stored_val_id);
            } break;
            case defs::DefKind::BV_EXP: {
                throw new Panic(
                    "InputError: `eval_def_v` cannot eval a bound var"
                );
            } break;
            default: {
                throw new Panic(
                    "InputError: unknown DefKind in `eval_def_v`"
                );
            }
        }
    }

    mtype::TID eval_poly_ts(
        mast::TypeSpecID poly_ts,
        sub::Substitution* s
    ) {
        mast::TypeSpecID mono_ts = p2m_ts(poly_ts, s);
        return eval_mono_ts(mono_ts);
    }

    mtype::TID eval_poly_exp(mast::ExpID exp_id, sub::Substitution* s) {
        // todo: implement me
        mast::ExpID mono_exp = p2m_exp(exp_id, s);
        return eval_mono_exp(mono_exp);
    }

    mtype::TID eval_mono_ts(
        mast::TypeSpecID ts_id
    ) {
        mast::NodeKind ts_kind = mast::get_node_kind(ts_id);
        switch (ts_kind) {
            case mast::NodeKind::TS_UNIT: {
                return mtype::get_unit_tid();
            } break;

            case mast::NodeKind::TS_ID: {
                auto info = &mast::get_info_ptr(ts_id)->ts_id;
                DefID def_id = info->def_id;
                return eval_def_t(def_id);
            } break;

            case mast::NodeKind::TS_PTR: {
                auto info = &mast::get_info_ptr(ts_id)->ts_ptr;
                mtype::TID ptd_tid = eval_mono_ts(info->ptd_ts);
                return mtype::get_ptr_tid(ptd_tid, info->contents_is_mut);
            } break;
            
            case mast::NodeKind::TS_ARRAY: {
                auto info = &mast::get_info_ptr(ts_id)->ts_array;
                mtype::TID ptd_tid = eval_mono_ts(info->ptd_ts);
                mval::ValueID count_val_id = eval_mono_exp(info->count_exp);
                bool is_mut = info->contents_is_mut;
                return mtype::get_array_tid(ptd_tid, count_val_id, is_mut);
            } break;
            
            case mast::NodeKind::TS_SLICE: {
                auto info = &mast::get_info_ptr(ts_id)->ts_slice;
                mtype::TID ptd_tid = eval_mono_ts(info->ptd_ts);
                bool contents_is_mut = info->contents_is_mut;
                return mtype::get_slice_tid(ptd_tid, contents_is_mut);
            } break;
            
            case mast::NodeKind::TS_FUNC_SGN: {
                auto info = &mast::get_info_ptr(ts_id)->ts_func_sgn;
                auto arg_tid = eval_mono_ts(info->arg_ts);
                auto ret_tid = eval_mono_ts(info->ret_ts);
                auto ses = info->ret_ses;
                return mtype::get_function_tid(arg_tid, ret_tid, ses);
            } break;

            case mast::NodeKind::TS_TUPLE: {
                auto info = &mast::get_info_ptr(ts_id)->ts_tuple;
                auto elem_count = info->elem_ts_count;
                auto elem_array = info->elem_ts_array;

                // constructing an arg-list in reverse order:
                auto made_arg_list = arg_list::EMPTY;
                for (size_t i = 0; i < elem_count; i++) {
                    auto elem_index = elem_count - (i + 1);
                    auto elem_ts = elem_array[elem_index];
                    auto elem_ts_tid = eval_mono_ts(elem_ts);
                    made_arg_list = arg_list::cons_tid(
                        made_arg_list, 
                        elem_ts_tid
                    );
                }
                return mtype::get_tuple_tid(made_arg_list);
            } break;
            
            case mast::NodeKind::TS_GET_MONO_MODULE_FIELD: {
                auto raw_info = mast::get_info_ptr(ts_id);
                auto info = &raw_info->ts_get_mono_module_field;

                DefID def_id = modules::get_mono_mod_field_at(
                    info->template_id,
                    info->ts_field_index
                );
                return eval_def_t(def_id);
            } break;

            default: {
                throw new Panic("Invalid mono TS kind");
            }
        }
    }

    static ssize_t signed_int_exp_val(size_t mu, bool b) {
        ssize_t m = mu;
        ssize_t v = b ? -m : +m;
        return v;
    }
    static mval::ValueID eval_mono_int_exp(mast::ExpID exp_id) {
        auto info = &mast::get_info_ptr(exp_id)->exp_int;
        auto m = info->mantissa;
        auto b = info->is_neg;
        switch (info->suffix) {
            case IntegerSuffix::U1: {
                return mval::push_u1(m);
            }
            case IntegerSuffix::U8: {
                return mval::push_u8(m);
            }
            case IntegerSuffix::U16: {
                return mval::push_u16(m);
            }
            case IntegerSuffix::U32: {
                return mval::push_u32(m);
            }
            case IntegerSuffix::U64: {
                return mval::push_u64(m);
            }
            case IntegerSuffix::S8: {
                return mval::push_s8(signed_int_exp_val(m,b));
            }
            case IntegerSuffix::S16: {
                return mval::push_s16(signed_int_exp_val(m,b));
            }
            case IntegerSuffix::S32: {
                return mval::push_s32(signed_int_exp_val(m,b));
            }
            case IntegerSuffix::S64: {
                return mval::push_s64(signed_int_exp_val(m,b));
            }
        }
    }
    static mval::ValueID eval_mono_float_exp(mast::ExpID exp_id) {
        auto info = &mast::get_info_ptr(exp_id)->exp_float;
        switch (info->suffix) {
            case FloatSuffix::F32: {
                return mval::push_f32(info->value);
            }
            case FloatSuffix::F64: {
                return mval::push_f64(info->value);
            }
        }
    }
    static mval::ValueID eval_mono_string_exp(mast::ExpID exp_id) {
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
    static mval::ValueID eval_mono_func_call_exp(mast::ExpID exp_id) {
        auto info = &mast::get_info_ptr(exp_id)->exp_call;
        // todo: figure out how to evaluate function calls.
        //  - we need some 'stack' behavior, so must restore any
        //    store-clobbered DefIDs when processing function return
        //  - consider writing a function that allocates space for the
        //    arguments, copies them, 
        // todo: ensure evaluated functions are strictly TOT 
        throw new Panic("NotImplemented: eval for EXP_FUNC_CALL");
    }
    static mval::ValueID eval_mono_unary_op_exp(mast::ExpID exp_id) {
        auto info = &mast::get_info_ptr(exp_id)->exp_unary;
                
        mval::ValueID arg_val_id = eval_mono_exp(info->arg_exp);
        auto vk = mval::value_kind(arg_val_id);
        auto vi = mval::value_info(arg_val_id);

        switch (info->unary_op) {
            case UnaryOp::Pos: {
                switch (vk) {
                    // identity op
                    case mval::ValueKind::S8:
                    case mval::ValueKind::S16:
                    case mval::ValueKind::S32:
                    case mval::ValueKind::S64:
                    {
                        return arg_val_id;
                    }

                    // cast unsigned to signed
                    case mval::ValueKind::U8: return mval::push_s8(vi.u8);
                    case mval::ValueKind::U16: return mval::push_s16(vi.u16);
                    case mval::ValueKind::U32: return mval::push_s32(vi.u32);
                    case mval::ValueKind::U64: return mval::push_s64(vi.u64);

                    // any other arg is an error:
                    default: {
                        throw new Panic("Invalid arg to unary op '+'");
                    }
                }
            } break;
            case UnaryOp::Neg: {
                switch (vk) {
                    case mval::ValueKind::S8: return mval::push_s8(-vi.s8);
                    case mval::ValueKind::S16: return mval::push_s16(-vi.s16);
                    case mval::ValueKind::S32: return mval::push_s32(-vi.s32);
                    case mval::ValueKind::S64: return mval::push_s64(-vi.s64);
                    default: throw new Panic("Invalid arg to unary op '-'");
                }
            } break;
            case UnaryOp::LogicalNot: {
                switch (vk) {
                    case mval::ValueKind::U1: {
                        return mval::push_u1(!vi.u1);
                    }
                    default: {
                        throw new Panic("Invalid arg to unary op 'not'");
                    }
                }
            } break;
            case UnaryOp::DeRef: {
                throw new Panic("NotImplemented: eval UnaryOp::DeRef");
            } break;
        }
    }
    template <typename T> 
    inline static T ipow(T base, T exponent) {
        T result = 1;
        for (size_t i = 0; i < exponent; i++) {
            result *= base;
        }
        return result;
    }
    static mval::ValueID eval_mono_binary_op_exp(mast::ExpID exp_id) {
        auto info = &mast::get_info_ptr(exp_id)->exp_binary;
        
        mval::ValueID lt_arg_val_id = eval_mono_exp(info->lt_arg_exp);
        auto lt_vk = mval::value_kind(lt_arg_val_id);
        auto lt_vi = mval::value_info(lt_arg_val_id);

        mval::ValueID rt_arg_val_id = eval_mono_exp(info->rt_arg_exp);
        auto rt_vk = mval::value_kind(rt_arg_val_id);
        auto rt_vi = mval::value_info(rt_arg_val_id);

        assert(lt_vk == rt_vk && "NotImplemented: BinaryOp value promotions");
        auto vk = lt_vk;

        switch (info->binary_op) {
            case BinaryOp::Pow: {
                switch (vk) {
                    case mval::ValueKind::U8: return mval::push_u8(ipow(lt_vi.u8, rt_vi.u8));
                    case mval::ValueKind::U16: return mval::push_u16(ipow(lt_vi.u16, rt_vi.u16));
                    case mval::ValueKind::U32: return mval::push_u32(ipow(lt_vi.u32, rt_vi.u32));
                    case mval::ValueKind::U64: return mval::push_u64(ipow(lt_vi.u64, rt_vi.u64));
                    case mval::ValueKind::S8: return mval::push_s8(ipow(lt_vi.s8, rt_vi.s8));
                    case mval::ValueKind::S16: return mval::push_s16(ipow(lt_vi.s16, rt_vi.s16));
                    case mval::ValueKind::S32: return mval::push_s32(ipow(lt_vi.s32, rt_vi.s32));
                    case mval::ValueKind::S64: return mval::push_s64(ipow(lt_vi.s64, rt_vi.s64));
                    case mval::ValueKind::F32: return mval::push_f32(std::powf(lt_vi.f32, rt_vi.f32));
                    case mval::ValueKind::F64: return mval::push_f64(std::powf(lt_vi.f64, rt_vi.f64));
                    default: {
                        throw new Panic(
                            "ERROR: invalid arguments to BinOp '^' (exponent)"
                        );
                    }
                }
            }
            case BinaryOp::Mul: {
                switch (vk) {
                    case mval::ValueKind::U8: return mval::push_u8(lt_vi.u8 * rt_vi.u8);
                    case mval::ValueKind::U16: return mval::push_u16(lt_vi.u16 * rt_vi.u16);
                    case mval::ValueKind::U32: return mval::push_u32(lt_vi.u32 * rt_vi.u32);
                    case mval::ValueKind::U64: return mval::push_u64(lt_vi.u64 * rt_vi.u64);
                    case mval::ValueKind::S8: return mval::push_s8(lt_vi.s8 * rt_vi.s8);
                    case mval::ValueKind::S16: return mval::push_s16(lt_vi.s16 * rt_vi.s16);
                    case mval::ValueKind::S32: return mval::push_s32(lt_vi.s32 * rt_vi.s32);
                    case mval::ValueKind::S64: return mval::push_s64(lt_vi.s64 * rt_vi.s64);
                    case mval::ValueKind::F32: return mval::push_f32(lt_vi.f32 * rt_vi.f32);
                    case mval::ValueKind::F64: return mval::push_f64(lt_vi.f64 * rt_vi.f64);
                    default: {
                        throw new Panic("ERROR: invalid arguments to BinOp '*' (multiply)");
                    }
                }
            }
            case BinaryOp::Div: {
                switch (vk) {
                    case mval::ValueKind::U8: return mval::push_u8(lt_vi.u8 * rt_vi.u8);
                    case mval::ValueKind::U16: return mval::push_u16(lt_vi.u16 * rt_vi.u16);
                    case mval::ValueKind::U32: return mval::push_u32(lt_vi.u32 * rt_vi.u32);
                    case mval::ValueKind::U64: return mval::push_u64(lt_vi.u64 * rt_vi.u64);
                    case mval::ValueKind::S8: return mval::push_s8(lt_vi.s8 * rt_vi.s8);
                    case mval::ValueKind::S16: return mval::push_s16(lt_vi.s16 * rt_vi.s16);
                    case mval::ValueKind::S32: return mval::push_s32(lt_vi.s32 * rt_vi.s32);
                    case mval::ValueKind::S64: return mval::push_s64(lt_vi.s64 * rt_vi.s64);
                    case mval::ValueKind::F32: return mval::push_f32(lt_vi.f32 * rt_vi.f32);
                    case mval::ValueKind::F64: return mval::push_f64(lt_vi.f64 * rt_vi.f64);
                    default: {
                        throw new Panic("ERROR: invalid arguments to BinOp '^' (exponent)");
                    }
                }
            }
            case BinaryOp::Rem: {
                switch (vk) {
                    case mval::ValueKind::U8: return mval::push_u8(lt_vi.u8 % rt_vi.u8);
                    case mval::ValueKind::U16: return mval::push_u16(lt_vi.u16 % rt_vi.u16);
                    case mval::ValueKind::U32: return mval::push_u32(lt_vi.u32 % rt_vi.u32);
                    case mval::ValueKind::U64: return mval::push_u64(lt_vi.u64 % rt_vi.u64);
                    case mval::ValueKind::S8: return mval::push_s8(lt_vi.s8 % rt_vi.s8);
                    case mval::ValueKind::S16: return mval::push_s16(lt_vi.s16 % rt_vi.s16);
                    case mval::ValueKind::S32: return mval::push_s32(lt_vi.s32 % rt_vi.s32);
                    case mval::ValueKind::S64: return mval::push_s64(lt_vi.s64 % rt_vi.s64);
                    case mval::ValueKind::F32: return mval::push_f32(std::fmod(lt_vi.f32, rt_vi.f32));
                    case mval::ValueKind::F64: return mval::push_f64(std::fmod(lt_vi.f64, rt_vi.f64));
                    default: {
                        throw new Panic("ERROR: invalid arguments to BinOp '%' (exponent)");
                    }
                }
            }
            case BinaryOp::Add: {
                switch (vk) {
                    case mval::ValueKind::U8: return mval::push_u8(lt_vi.u8 + rt_vi.u8);
                    case mval::ValueKind::U16: return mval::push_u16(lt_vi.u16 + rt_vi.u16);
                    case mval::ValueKind::U32: return mval::push_u32(lt_vi.u32 + rt_vi.u32);
                    case mval::ValueKind::U64: return mval::push_u64(lt_vi.u64 + rt_vi.u64);
                    case mval::ValueKind::S8: return mval::push_s8(lt_vi.s8 + rt_vi.s8);
                    case mval::ValueKind::S16: return mval::push_s16(lt_vi.s16 + rt_vi.s16);
                    case mval::ValueKind::S32: return mval::push_s32(lt_vi.s32 + rt_vi.s32);
                    case mval::ValueKind::S64: return mval::push_s64(lt_vi.s64 + rt_vi.s64);
                    case mval::ValueKind::F32: return mval::push_f32(lt_vi.f32 + rt_vi.f32);
                    case mval::ValueKind::F64: return mval::push_f64(lt_vi.f64 + rt_vi.f64);
                    default: {
                        throw new Panic("ERROR: invalid arguments to BinOp '+' (add)");
                    }
                }
            }
            case BinaryOp::Sub: {
                switch (vk) {
                    case mval::ValueKind::U8: return mval::push_u8(lt_vi.u8 - rt_vi.u8);
                    case mval::ValueKind::U16: return mval::push_u16(lt_vi.u16 - rt_vi.u16);
                    case mval::ValueKind::U32: return mval::push_u32(lt_vi.u32 - rt_vi.u32);
                    case mval::ValueKind::U64: return mval::push_u64(lt_vi.u64 - rt_vi.u64);
                    case mval::ValueKind::S8: return mval::push_s8(lt_vi.s8 - rt_vi.s8);
                    case mval::ValueKind::S16: return mval::push_s16(lt_vi.s16 - rt_vi.s16);
                    case mval::ValueKind::S32: return mval::push_s32(lt_vi.s32 - rt_vi.s32);
                    case mval::ValueKind::S64: return mval::push_s64(lt_vi.s64 - rt_vi.s64);
                    case mval::ValueKind::F32: return mval::push_f32(lt_vi.f32 - rt_vi.f32);
                    case mval::ValueKind::F64: return mval::push_f64(lt_vi.f64 - rt_vi.f64);
                    default: {
                        throw new Panic("ERROR: invalid arguments to BinOp '-' (subtract)");
                    }
                }
            }
            case BinaryOp::LessThan: {
                switch (vk) {
                    case mval::ValueKind::U8: return mval::push_u8(lt_vi.u8 < rt_vi.u8);
                    case mval::ValueKind::U16: return mval::push_u16(lt_vi.u16 < rt_vi.u16);
                    case mval::ValueKind::U32: return mval::push_u32(lt_vi.u32 < rt_vi.u32);
                    case mval::ValueKind::U64: return mval::push_u64(lt_vi.u64 < rt_vi.u64);
                    case mval::ValueKind::S8: return mval::push_s8(lt_vi.s8 < rt_vi.s8);
                    case mval::ValueKind::S16: return mval::push_s16(lt_vi.s16 < rt_vi.s16);
                    case mval::ValueKind::S32: return mval::push_s32(lt_vi.s32 < rt_vi.s32);
                    case mval::ValueKind::S64: return mval::push_s64(lt_vi.s64 < rt_vi.s64);
                    case mval::ValueKind::F32: return mval::push_f32(lt_vi.f32 < rt_vi.f32);
                    case mval::ValueKind::F64: return mval::push_f64(lt_vi.f64 < rt_vi.f64);
                    default: {
                        throw new Panic("ERROR: invalid arguments to BinOp '%' (exponent)");
                    }
                }
            }
            case BinaryOp::LessThanOrEquals: {
                switch (vk) {
                    case mval::ValueKind::U8: return mval::push_u8(lt_vi.u8 <= rt_vi.u8);
                    case mval::ValueKind::U16: return mval::push_u16(lt_vi.u16 <= rt_vi.u16);
                    case mval::ValueKind::U32: return mval::push_u32(lt_vi.u32 <= rt_vi.u32);
                    case mval::ValueKind::U64: return mval::push_u64(lt_vi.u64 <= rt_vi.u64);
                    case mval::ValueKind::S8: return mval::push_s8(lt_vi.s8 <= rt_vi.s8);
                    case mval::ValueKind::S16: return mval::push_s16(lt_vi.s16 <= rt_vi.s16);
                    case mval::ValueKind::S32: return mval::push_s32(lt_vi.s32 <= rt_vi.s32);
                    case mval::ValueKind::S64: return mval::push_s64(lt_vi.s64 <= rt_vi.s64);
                    case mval::ValueKind::F32: return mval::push_f32(lt_vi.f32 <= rt_vi.f32);
                    case mval::ValueKind::F64: return mval::push_f64(lt_vi.f64 <= rt_vi.f64);
                    default: {
                        throw new Panic("ERROR: invalid arguments to BinOp '%' (exponent)");
                    }
                }
            }
            case BinaryOp::GreaterThan: {
                switch (vk) {
                    case mval::ValueKind::U8: return mval::push_u8(lt_vi.u8 > rt_vi.u8);
                    case mval::ValueKind::U16: return mval::push_u16(lt_vi.u16 > rt_vi.u16);
                    case mval::ValueKind::U32: return mval::push_u32(lt_vi.u32 > rt_vi.u32);
                    case mval::ValueKind::U64: return mval::push_u64(lt_vi.u64 > rt_vi.u64);
                    case mval::ValueKind::S8: return mval::push_s8(lt_vi.s8 > rt_vi.s8);
                    case mval::ValueKind::S16: return mval::push_s16(lt_vi.s16 > rt_vi.s16);
                    case mval::ValueKind::S32: return mval::push_s32(lt_vi.s32 > rt_vi.s32);
                    case mval::ValueKind::S64: return mval::push_s64(lt_vi.s64 > rt_vi.s64);
                    case mval::ValueKind::F32: return mval::push_f32(lt_vi.f32 > rt_vi.f32);
                    case mval::ValueKind::F64: return mval::push_f64(lt_vi.f64 > rt_vi.f64);
                    default: {
                        throw new Panic("ERROR: invalid arguments to BinOp '%' (exponent)");
                    }
                }
            }
            case BinaryOp::GreaterThanOrEquals: {
                switch (vk) {
                    case mval::ValueKind::U8: return mval::push_u8(lt_vi.u8 >= rt_vi.u8);
                    case mval::ValueKind::U16: return mval::push_u16(lt_vi.u16 >= rt_vi.u16);
                    case mval::ValueKind::U32: return mval::push_u32(lt_vi.u32 >= rt_vi.u32);
                    case mval::ValueKind::U64: return mval::push_u64(lt_vi.u64 >= rt_vi.u64);
                    case mval::ValueKind::S8: return mval::push_s8(lt_vi.s8 >= rt_vi.s8);
                    case mval::ValueKind::S16: return mval::push_s16(lt_vi.s16 >= rt_vi.s16);
                    case mval::ValueKind::S32: return mval::push_s32(lt_vi.s32 >= rt_vi.s32);
                    case mval::ValueKind::S64: return mval::push_s64(lt_vi.s64 >= rt_vi.s64);
                    case mval::ValueKind::F32: return mval::push_f32(lt_vi.f32 >= rt_vi.f32);
                    case mval::ValueKind::F64: return mval::push_f64(lt_vi.f64 >= rt_vi.f64);
                    default: {
                        throw new Panic("ERROR: invalid arguments to BinOp '%' (exponent)");
                    }
                }
            }
            case BinaryOp::Equals: {
                return mval::equals(lt_arg_val_id, rt_arg_val_id);
            }
            case BinaryOp::NotEquals: {
                return !mval::equals(lt_arg_val_id, rt_arg_val_id);
            }
            case BinaryOp::LogicalAnd: {
                switch (vk) {
                    case mval::ValueKind::U1: {
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
            case BinaryOp::LogicalOr: {
                switch (vk) {
                    case mval::ValueKind::U1: {
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
    static mval::ValueID eval_mono_ite_exp(mast::ExpID ite_exp) {
        auto info = &mast::get_info_ptr(ite_exp)->exp_if_then_else;
        auto cond_val_id = eval_mono_exp(info->cond_exp);
        auto cond_vk = mval::value_kind(cond_val_id);
        if (cond_vk != mval::ValueKind::U1) {
            throw new Panic("ERROR: expected boolean `cond` exp in ITE");
        }
        auto cond_vv = mval::value_info(cond_val_id).u1;

        return (
            (cond_vv) ?
            eval_mono_exp(info->then_exp) :
            eval_mono_exp(info->else_exp)
        );
    }
    static mval::ValueID eval_mono_get_tuple_field(mast::ExpID exp_id) {
        auto info = &mast::get_info_ptr(exp_id)->exp_get_tuple_field;
        auto tuple_val_id = eval_mono_exp(info->tuple_exp_id);
        auto index = info->index;
        auto opt_res = mval::get_seq_elem(tuple_val_id, index);
        if (opt_res.has_value()) {
            return opt_res.value();
        } else {
            throw new Panic("ERROR: sequence index out of bounds");
        }
    }
    mval::ValueID eval_mono_exp(mast::ExpID exp_id) {
        // todo: implement me
        mast::NodeKind exp_kind = mast::get_node_kind(exp_id);
        switch (exp_kind) {
            case mast::NodeKind::EXP_UNIT: {
                return mval::get_unit();
            } break;

            case mast::NodeKind::EXP_INT: {
                return eval_mono_int_exp(exp_id);
            } break;

            case mast::NodeKind::EXP_FLOAT: {
                return eval_mono_float_exp(exp_id);
            } break;
            case mast::NodeKind::EXP_STRING: {
                return eval_mono_string_exp(exp_id);
            } break;
            case mast::NodeKind::EXP_ID: {
                auto info = &mast::get_info_ptr(exp_id)->exp_id;
                return eval_def_v(info->def_id);
            } break;
            case mast::NodeKind::EXP_FUNC_CALL: {
                return eval_mono_func_call_exp(exp_id);
            } break;
            case mast::NodeKind::EXP_UNARY_OP: {
                return eval_mono_unary_op_exp(exp_id);
            } break;
            case mast::NodeKind::EXP_BINARY_OP: {
                return eval_mono_binary_op_exp(exp_id);
            } break;
            case mast::NodeKind::EXP_IF_THEN_ELSE: {
                return eval_mono_ite_exp(exp_id);
            } break;
            case mast::NodeKind::EXP_GET_TUPLE_FIELD: {
                return eval_mono_get_tuple_field(exp_id);
            } break;
            case mast::NodeKind::EXP_GET_POLY_MODULE_FIELD: {} break;
            case mast::NodeKind::EXP_GET_MONO_MODULE_FIELD: {} break;
            case mast::NodeKind::EXP_LAMBDA: {} break;
            case mast::NodeKind::EXP_ALLOCATE_ONE: {} break;
            case mast::NodeKind::EXP_ALLOCATE_MANY: {} break;
            case mast::NodeKind::EXP_CHAIN: {} break;

            default: {
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

    mtype::TID eval_type(mast::TypeSpecID ts_id) {
        auto s = sub::create();
        auto res = eval_poly_ts(ts_id, s);
        sub::destroy(s);
        return res;
    }
    mval::ValueID eval_exp(mast::ExpID exp_id) {
        auto s = sub::create();
        auto res = eval_poly_exp(exp_id, s);
        sub::destroy(s);
        return res;
    }

}