#include "mast.hh"
#include "gdef.hh"

#include <vector>
#include <iostream>
#include <iomanip>

#include "panic.hh"
#include "shared-enums.hh"

namespace monomorphizer::mast {

    extern mast::NodeID const NULL_NODE_ID = UNIVERSAL_NULL_ID;
    
    size_t const DEFAULT_NODE_MGR_CAPACITY = 16 * 1024;
    
    class NodeMgr {
        // The NodeMgr class manages parallel arrays that store attributes for
        // each node.
        // NOTE: we return pointers to info that are STABLE iff we do not create
        //       any new nodes.

      private:
        std::vector<NodeKind> m_kind_table;
        std::vector<NodeInfo> m_info_table;

      public:
        SingletonNodeCache m_singleton_cache;

      public:
        NodeMgr(size_t capacity);

        inline size_t node_count() {
            assert(
                m_kind_table.size() == m_info_table.size() &&
                "Parallel arrays of different lengths"
            );
            return m_kind_table.size();
        }

        inline void push(NodeKind kind) {
            // std::cout << "Pushing NK=" << (size_t)kind << std::endl;
            auto id = m_kind_table.size();
            m_kind_table.push_back(kind);
            m_info_table.emplace_back();
            assert(m_kind_table[id] == kind);
        }

        inline NodeKind kind_of(size_t index) {
            return m_kind_table[index];
        }

        inline NodeInfo* tmp_info_ptr(size_t index) {
            return &m_info_table[index];
        }

        inline SingletonNodeCache const& singleton_cache() const {
            return m_singleton_cache;
        }
    };

    static mast::TypeSpecID new_unit_ts();
    static mast::ExpID new_unit_exp();

    NodeMgr::NodeMgr(size_t capacity)
    :   m_kind_table(),
        m_info_table(),
        m_singleton_cache({
            NULL_NODE_ID,
            NULL_NODE_ID
        })
    {
        // reserving vectors:
        m_kind_table.reserve(capacity);
        m_info_table.reserve(capacity);
    }

    static NodeMgr* s_mgr = nullptr;

    void ensure_mast_init() {
        size_t capacity = DEFAULT_NODE_MGR_CAPACITY;
        if (!s_mgr) {
            // allocating:
            s_mgr = new NodeMgr(capacity);

            // initializing singleton cache:
            s_mgr->m_singleton_cache.ts_unit = new_unit_ts();
            s_mgr->m_singleton_cache.exp_unit = new_unit_exp();
        }
    }

    void drop_mast() {
        delete s_mgr;
        s_mgr = nullptr;
    }

    NodeKind get_node_kind(mast::NodeID node_id) {
        return s_mgr->kind_of(node_id);
    }
    NodeInfo* get_info_ptr(mast::NodeID node_id) {
        assert(node_id < s_mgr->node_count());
        auto node_index = static_cast<size_t>(node_id);
        return s_mgr->tmp_info_ptr(node_index);
    }

    mast::NodeID help_alloc_node(NodeKind kind) {
        auto node_id = s_mgr->node_count();
        s_mgr->push(kind);
        return node_id;
    }

    mast::TypeSpecID new_unit_ts() {
        auto new_node_id = help_alloc_node(NodeKind::TS_UNIT);
        return new_node_id;
    }
    mast::TypeSpecID get_unit_ts() {
        return s_mgr->singleton_cache().ts_unit;
    }
    mast::TypeSpecID new_gid_ts(GDefID def_id) {
        auto new_node_id = help_alloc_node(NodeKind::TS_GID);
        auto info_ptr = &get_info_ptr(new_node_id)->ts_gid;

        info_ptr->def_id = def_id;

        return new_node_id;
    }
    mast::TypeSpecID new_lid_ts(intern::IntStr int_str_id) {
        auto new_node_id = help_alloc_node(NodeKind::TS_LID);
        auto info_ptr = &get_info_ptr(new_node_id)->ts_lid;

        info_ptr->int_str_id = int_str_id;

        return new_node_id;
    }
    mast::TypeSpecID new_ptr_ts(
        mast::TypeSpecID ptd_ts,
        bool contents_is_mut
    ) {
        auto new_node_id = help_alloc_node(NodeKind::TS_PTR);
        auto info_ptr = &get_info_ptr(new_node_id)->ts_ptr;

        info_ptr->ptd_ts = ptd_ts;
        info_ptr->contents_is_mut = contents_is_mut;

        return new_node_id;
    }
    mast::TypeSpecID new_array_ts(
        mast::TypeSpecID ptd_ts,
        mast::ExpID count_exp,
        bool contents_is_mut
    ) {
        auto new_node_id = help_alloc_node(NodeKind::TS_ARRAY);
        auto info_ptr = &get_info_ptr(new_node_id)->ts_array;

        info_ptr->ptd_ts = ptd_ts;
        info_ptr->count_exp = count_exp;
        info_ptr->contents_is_mut = contents_is_mut;

        return new_node_id;
    }
    mast::TypeSpecID new_slice_ts(
        mast::TypeSpecID ptd_ts,
        bool contents_is_mut
    ) {
        auto new_node_id = help_alloc_node(NodeKind::TS_SLICE);
        auto info_ptr = &get_info_ptr(new_node_id)->ts_slice;

        info_ptr->ptd_ts = ptd_ts;
        info_ptr->contents_is_mut = contents_is_mut;

        return new_node_id;
    }
    mast::TypeSpecID new_func_sgn_ts(
        mast::TypeSpecID arg_ts,
        mast::TypeSpecID ret_ts,
        SES ret_ses
    ) {
        auto new_node_id = help_alloc_node(NodeKind::TS_FUNC_SGN);
        auto info_ptr = &get_info_ptr(new_node_id)->ts_func_sgn;

        info_ptr->arg_ts = arg_ts;
        info_ptr->ret_ts = ret_ts;
        info_ptr->ret_ses = ret_ses;

        return new_node_id;
    }
    mast::TypeSpecID new_tuple_ts(
        size_t elem_ts_count,
        mast::TypeSpecID* mv_elem_ts_array
    ) {
        auto new_node_id = help_alloc_node(NodeKind::TS_TUPLE);
        auto info_ptr = &get_info_ptr(new_node_id)->ts_tuple;

        info_ptr->elem_ts_count = elem_ts_count;
        info_ptr->elem_ts_array = mv_elem_ts_array;

        return new_node_id;
    }
    mast::TypeSpecID new_get_mono_module_field_ts(
        MonoModID mono_mod_id,
        size_t field_index
    ) {
        auto new_node_id = help_alloc_node(NodeKind::TS_GET_MONO_MODULE_FIELD);
        auto info_ptr = &get_info_ptr(new_node_id)->ts_get_mono_module_field;
        
        info_ptr->template_id = mono_mod_id;
        info_ptr->ts_field_index = field_index;

        return new_node_id;
    }
    mast::TypeSpecID new_get_poly_module_field_ts(
        PolyModID poly_mod_id,
        size_t field_index,
        size_t actual_arg_count,
        mast::NodeID* mv_actual_arg_array
    ) {
        auto new_node_id = help_alloc_node(NodeKind::TS_GET_POLY_MODULE_FIELD);
        auto info_ptr = &get_info_ptr(new_node_id)->ts_get_poly_module_field;
        
        info_ptr->template_id = poly_mod_id;
        info_ptr->ts_field_index = field_index;
        info_ptr->actual_arg_count = actual_arg_count;
        info_ptr->actual_arg_array = mv_actual_arg_array;

        return new_node_id;
    }

    mast::ExpID new_unit_exp() {
        auto new_node_id = help_alloc_node(NodeKind::EXP_UNIT);
        return new_node_id;
    }
    mast::TypeSpecID get_unit_exp() {
        return s_mgr->singleton_cache().exp_unit;
    }
    mast::ExpID new_int_exp(
        size_t mantissa,
        IntegerSuffix typing_suffix,
        bool is_neg
    ) {
        auto new_node_id = help_alloc_node(NodeKind::EXP_INT);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_int;

        info_ptr->mantissa = mantissa;
        info_ptr->suffix = typing_suffix;
        info_ptr->is_neg = is_neg;
        
        return new_node_id;
    }
    mast::ExpID new_float_exp(
        double value,
        FloatSuffix typing_suffix
    ) {
        auto new_node_id = help_alloc_node(NodeKind::EXP_FLOAT);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_float;

        info_ptr->value = value;
        info_ptr->suffix = typing_suffix;

        return new_node_id;
    }
    mast::ExpID new_string_exp(
        size_t code_point_count,
        int* code_point_array
    ) {
        auto new_node_id = help_alloc_node(NodeKind::EXP_STRING);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_str;

        info_ptr->code_point_count = code_point_count;
        info_ptr->code_point_array = new int[code_point_count];
        for (size_t i = 0; i < code_point_count; i++) {
            info_ptr->code_point_array[i] = code_point_array[i];
        }

        return new_node_id;
    }
    mast::ExpID new_gid_exp(GDefID def_id) {
        auto new_node_id = help_alloc_node(NodeKind::EXP_GID);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_gid;

        info_ptr->def_id = def_id;

        return new_node_id;
    }
    mast::ExpID new_lid_exp(intern::IntStr int_str_id) {
        auto new_node_id = help_alloc_node(NodeKind::EXP_LID);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_lid;

        info_ptr->int_str_id = int_str_id;

        return new_node_id;
    }
    mast::ExpID new_func_call_exp(
        mast::ExpID called_fn,
        mast::ExpID arg_exp_id,
        bool call_is_non_tot
    ) {
        auto new_node_id = help_alloc_node(NodeKind::EXP_FUNC_CALL);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_call;
        
        info_ptr->called_fn = called_fn;
        info_ptr->call_is_non_tot = call_is_non_tot;
        info_ptr->arg_exp_id = arg_exp_id;

        return new_node_id;
    }
    mast::ExpID new_tuple_exp(
        size_t tuple_item_count,
        mast::ExpID* mv_tuple_item_array
    ) {
        auto new_node_id = help_alloc_node(NodeKind::EXP_TUPLE);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_tuple;
        
        info_ptr->item_count = tuple_item_count;
        info_ptr->item_array = mv_tuple_item_array;

        return new_node_id;
    }
    mast::ExpID new_unary_op_exp(
        UnaryOp unary_op,
        mast::ExpID arg_exp
    ) {
        auto new_node_id = help_alloc_node(NodeKind::EXP_UNARY_OP);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_unary;

        info_ptr->unary_op = unary_op;
        info_ptr->arg_exp = arg_exp;

        return new_node_id;
    }
    mast::ExpID new_binary_op_exp(
        BinaryOp binary_op,
        mast::ExpID lt_arg_exp,
        mast::ExpID rt_arg_exp
    ) {
        auto new_node_id = help_alloc_node(NodeKind::EXP_BINARY_OP);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_binary;

        info_ptr->binary_op = binary_op;
        info_ptr->lt_arg_exp = lt_arg_exp;
        info_ptr->rt_arg_exp = rt_arg_exp;

        return new_node_id;
    }
    mast::ExpID new_if_then_else_exp(
        mast::ExpID cond_exp,
        mast::ExpID then_exp,
        mast::ExpID else_exp
    ) {
        auto new_node_id = help_alloc_node(NodeKind::EXP_IF_THEN_ELSE);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_if_then_else;

        info_ptr->cond_exp = cond_exp;
        info_ptr->then_exp = then_exp;
        info_ptr->else_exp = else_exp;

        return new_node_id;
    }
    mast::ExpID new_get_tuple_field_by_index_exp(
        mast::ExpID tuple_exp_id,
        size_t index
    ) {
        auto new_node_id = help_alloc_node(NodeKind::EXP_GET_TUPLE_FIELD);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_get_tuple_field;

        info_ptr->tuple_exp_id = tuple_exp_id;
        info_ptr->index = index;

        return new_node_id;
    }
    mast::ExpID new_lambda_exp(
        uint32_t arg_name_count,
        intern::IntStr* mv_arg_name_array,
        uint32_t ctx_enclosed_name_count,
        intern::IntStr* mv_ctx_enclosed_name_array,
        mast::ExpID body_exp_id
    ) {
        auto new_node_id = help_alloc_node(EXP_LAMBDA);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_lambda;

        info_ptr->arg_name_count = arg_name_count;
        info_ptr->ctx_enclosed_name_count = ctx_enclosed_name_count;
        info_ptr->arg_name_array = mv_arg_name_array;
        info_ptr->ctx_enclosed_name_array = mv_ctx_enclosed_name_array;
        info_ptr->body_exp = body_exp_id;

        return new_node_id;
    }
    mast::ExpID new_allocate_one_exp(
        mast::ExpID stored_val_exp_id,
        AllocationTarget allocation_target,
        bool allocation_is_mut
    ) {
        auto new_node_id = help_alloc_node(NodeKind::EXP_ALLOCATE_ONE);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_allocate_one;

        info_ptr->stored_val_exp_id = stored_val_exp_id;
        info_ptr->allocation_target = allocation_target;
        info_ptr->allocation_is_mut = allocation_is_mut;

        return new_node_id;
    }
    mast::ExpID new_allocate_many_exp(
        mast::ExpID initializer_stored_val_exp_id,
        mast::ExpID alloc_count_exp,
        AllocationTarget allocation_target,
        bool allocation_is_mut
    ) {
        auto new_node_id = help_alloc_node(NodeKind::EXP_ALLOCATE_MANY);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_allocate_many;

        info_ptr->initializer_stored_val_exp_id = initializer_stored_val_exp_id;
        info_ptr->alloc_count_exp = alloc_count_exp;
        info_ptr->allocation_target = allocation_target;
        info_ptr->allocation_is_mut = allocation_is_mut;

        return new_node_id;
    }
    mast::ExpID new_chain_exp(
        size_t prefix_elem_id_count,
        mast::ElemID* mv_prefix_elem_id_array,
        mast::ExpID ret_exp_id
    ) {
        auto new_node_id = help_alloc_node(EXP_CHAIN);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_chain;

        info_ptr->prefix_elem_count = prefix_elem_id_count;
        info_ptr->prefix_elem_array = mv_prefix_elem_id_array;
        info_ptr->ret_exp_id = ret_exp_id;

        return new_node_id;
    }
    mast::ExpID new_get_mono_module_field_exp(
        MonoModID mono_mod_id,
        size_t field_index
    ) {
        auto new_node_id = help_alloc_node(NodeKind::EXP_GET_MONO_MODULE_FIELD);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_get_mono_module_field;
        
        info_ptr->template_id = mono_mod_id;
        info_ptr->field_index = field_index;

        return new_node_id;
    }
    mast::ExpID new_get_poly_module_field_exp(
        PolyModID poly_mod_id,
        size_t field_index,
        size_t actual_arg_count,
        mast::NodeID* mv_actual_arg_array
    ) {
        auto new_node_id = help_alloc_node(NodeKind::EXP_GET_POLY_MODULE_FIELD);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_get_poly_module_field;

        info_ptr->template_id = poly_mod_id;
        info_ptr->field_index = field_index;
        info_ptr->arg_count = actual_arg_count;
        info_ptr->arg_array = mv_actual_arg_array;

        return new_node_id;
    }
    mast::ExpID new_cast_exp(
        mast::TypeSpecID ts_id,
        mast::ExpID exp_id
    ) {
        auto new_node_id = help_alloc_node(NodeKind::EXP_CAST);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_cast;

        info_ptr->ts_id = ts_id;
        info_ptr->exp_id = exp_id;

        return new_node_id;
    }

    mast::ElemID new_bind1v_elem(
        intern::IntStr bound_id,
        mast::ExpID init_exp_id
    ) {
        auto new_node_id = help_alloc_node(NodeKind::ELEM_BIND1V);
        auto info_ptr = &get_info_ptr(new_node_id)->elem_bind1v;

        info_ptr->bound_id = bound_id;
        info_ptr->init_exp_id = init_exp_id;

        std::cout << "NOTE: Created mast::Bind1VElem with node-kind " << get_node_kind(new_node_id) << std::endl;
        return new_node_id;
    }
    mast::ElemID new_bind1t_elem(
        intern::IntStr bound_id,
        mast::TypeSpecID init_ts_id
    ) {
        auto new_node_id = help_alloc_node(NodeKind::ELEM_BIND1T);
        auto info_ptr = &get_info_ptr(new_node_id)->elem_bind1t;

        info_ptr->bound_id = bound_id;
        info_ptr->init_ts_id = init_ts_id;

        std::cout << "NOTE: Created mast::Bind1TElem with node-kind " << get_node_kind(new_node_id) << std::endl;
        return new_node_id;
    }
    mast::ElemID new_do_elem(
        mast::ExpID eval_exp_id
    ) {
        auto new_node_id = help_alloc_node(NodeKind::ELEM_DO);
        auto info_ptr = &get_info_ptr(new_node_id)->elem_do;

        info_ptr->eval_exp_id = eval_exp_id;

        std::cout << "NOTE: Created mast::DoElem with node-kind " << get_node_kind(new_node_id) << std::endl;
        return new_node_id;
    }

}

namespace monomorphizer::mast {

    bool is_node_exp_not_ts(mast::NodeID node_id) {
        mast::NodeKind nk = mast::get_node_kind(node_id);
        switch (nk) {
            // type specs:
            case mast::NodeKind::TS_UNIT:
            case mast::NodeKind::TS_GID:
            case mast::NodeKind::TS_PTR:
            case mast::NodeKind::TS_ARRAY:
            case mast::NodeKind::TS_SLICE:
            case mast::NodeKind::TS_FUNC_SGN:
            case mast::NodeKind::TS_TUPLE:
            case mast::NodeKind::TS_GET_POLY_MODULE_FIELD:
            case mast::NodeKind::TS_GET_MONO_MODULE_FIELD: {
                return false;
            } break;
            
            // expressions:
            case mast::NodeKind::EXP_UNIT:
            case mast::NodeKind::EXP_INT:
            case mast::NodeKind::EXP_FLOAT:
            case mast::NodeKind::EXP_STRING:
            case mast::NodeKind::EXP_GID:
            case mast::NodeKind::EXP_FUNC_CALL:
            case mast::NodeKind::EXP_UNARY_OP:
            case mast::NodeKind::EXP_BINARY_OP:
            case mast::NodeKind::EXP_IF_THEN_ELSE:
            case mast::NodeKind::EXP_GET_TUPLE_FIELD:
            case mast::NodeKind::EXP_GET_POLY_MODULE_FIELD:
            case mast::NodeKind::EXP_GET_MONO_MODULE_FIELD:
            case mast::NodeKind::EXP_LAMBDA:
            case mast::NodeKind::EXP_ALLOCATE_ONE:
            case mast::NodeKind::EXP_ALLOCATE_MANY:
            case mast::NodeKind::EXP_CHAIN: {
                return true;
            }

            // otherwise, error
            default: {
                throw new Panic(
                    "Tried binding invalid AST node kind: "
                    "expected TypeSpec or Exp only"
                );
            }
        }
    }

}
