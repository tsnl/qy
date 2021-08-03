#include "mast.hh"
#include "defs.hh"

#include <vector>

namespace monomorphizer::mast {

    extern NodeID const NULL_NODE_ID = -1;
    
    size_t const DEFAULT_NODE_MGR_CAPACITY = 16 * 1024;
    
    class NodeMgr {
        // The NodeMgr class manages parallel arrays that store attributes for
        // each node.
        // NOTE: we return pointers to info that are STABLE iff we do not create
        //       any new nodes.

      private:
        std::vector<NodeKind> m_kind_table;
        std::vector<NodeInfo> m_info_table;
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
            m_kind_table.push_back(kind);
            m_info_table.emplace_back();
        }

        inline NodeInfo* tmp_info_ptr(size_t index) {
            return &m_info_table[index];
        }

        inline SingletonNodeCache const& singleton_cache() const {
            return m_singleton_cache;
        }
    };

    static TypeSpecID new_unit_ts();
    static ExpID new_unit_exp();

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
        
        // initializing singleton cache:
        m_singleton_cache.ts_unit = new_unit_ts();
        m_singleton_cache.exp_unit = new_unit_exp();
    }

    static NodeMgr* s_mgr = nullptr;

    void ensure_init() {
        size_t capacity = DEFAULT_NODE_MGR_CAPACITY;
        if (!s_mgr) {
            s_mgr = new NodeMgr(capacity);
        }
    }

    void drop() {
        delete s_mgr;
        s_mgr = nullptr;
    }

    NodeInfo* get_info_ptr(NodeID node_id) {
        assert(node_id < s_mgr->node_count());
        auto node_index = static_cast<size_t>(node_id);
        return s_mgr->tmp_info_ptr(node_index);
    }
    NodeID help_alloc_node(NodeKind kind) {
        auto node_id = s_mgr->node_count();
        s_mgr->push(kind);
        return node_id;
    }
    TypeSpecID help_new_compound_ts(
        size_t elem_ts_count,
        NameNodeRelation* elem_ts_array,
        NodeKind node_kind
    ) {
        auto node_id = help_alloc_node(node_kind);
        CompoundTypeSpecNodeInfo* info_ptr = &get_info_ptr(node_id)->ts_compound;

        info_ptr->elem_ts_count = elem_ts_count;
        info_ptr->elem_ts_array = new NameNodeRelation[elem_ts_count];
        for (size_t i = 0; i < elem_ts_count; i++) {
            info_ptr->elem_ts_array[i] = elem_ts_array[i];
        }

        return node_id;
    }
    TypeSpecID new_unit_ts() {
        auto new_node_id = help_alloc_node(NodeKind::TS_UNIT);
        return new_node_id;
    }
    TypeSpecID get_unit_ts() {
        return s_mgr->singleton_cache().ts_unit;
    }
    TypeSpecID new_id_ts(DefID def_id) {
        auto new_node_id = help_alloc_node(NodeKind::TS_ID);
        auto info_ptr = &get_info_ptr(new_node_id)->ts_id;

        info_ptr->def_id = def_id;

        return new_node_id;
    }
    TypeSpecID new_ptr_ts(
        TypeSpecID ptd_ts,
        bool contents_is_mut
    ) {
        auto new_node_id = help_alloc_node(NodeKind::TS_PTR);
        auto info_ptr = &get_info_ptr(new_node_id)->ts_ptr;

        info_ptr->ptd_ts = ptd_ts;
        info_ptr->contents_is_mut = contents_is_mut;

        return new_node_id;
    }
    TypeSpecID new_array_ts(
        TypeSpecID ptd_ts,
        ExpID count_exp,
        bool contents_is_mut
    ) {
        auto new_node_id = help_alloc_node(NodeKind::TS_ARRAY);
        auto info_ptr = &get_info_ptr(new_node_id)->ts_array;

        info_ptr->ptd_ts = ptd_ts;
        info_ptr->count_exp = count_exp;
        info_ptr->contents_is_mut = contents_is_mut;

        return new_node_id;
    }
    TypeSpecID new_slice_ts(
        TypeSpecID ptd_ts,
        bool contents_is_mut
    ) {
        auto new_node_id = help_alloc_node(NodeKind::TS_SLICE);
        auto info_ptr = &get_info_ptr(new_node_id)->ts_slice;

        info_ptr->ptd_ts = ptd_ts;
        info_ptr->contents_is_mut = contents_is_mut;

        return new_node_id;
    }
    TypeSpecID new_func_sgn_ts(
        TypeSpecID arg_ts,
        TypeSpecID ret_ts,
        SES ret_ses
    ) {
        auto new_node_id = help_alloc_node(NodeKind::TS_FUNC_SGN);
        auto info_ptr = &get_info_ptr(new_node_id)->ts_func_sgn;

        info_ptr->arg_ts = arg_ts;
        info_ptr->ret_ts = ret_ts;
        info_ptr->ret_ses = ret_ses;

        return new_node_id;
    }
    TypeSpecID new_tuple_ts(
        size_t elem_ts_count,
        TypeSpecID* elem_ts_array
    ) {
        auto new_node_id = help_alloc_node(NodeKind::TS_TUPLE);
        auto info_ptr = &get_info_ptr(new_node_id)->ts_tuple;

        info_ptr->elem_ts_count = elem_ts_count;
        info_ptr->elem_ts_array = new TypeSpecID[elem_ts_count];
        for (size_t i = 0; i < elem_ts_count; i++) {
            info_ptr->elem_ts_array[i] = elem_ts_array[i];
        }

        return new_node_id;
    }
    TypeSpecID new_struct_ts(
        size_t elem_ts_count,
        NameNodeRelation* elem_ts_array
    ) {
        return help_new_compound_ts(
            elem_ts_count, elem_ts_array, 
            NodeKind::TS_STRUCT
        );
    }
    TypeSpecID new_union_ts(
        size_t elem_ts_count,
        NameNodeRelation* elem_ts_array
    ) {
        return help_new_compound_ts(
            elem_ts_count, elem_ts_array, 
            NodeKind::TS_UNION
        );
    }
    ExpID new_unit_exp() {
        auto new_node_id = help_alloc_node(NodeKind::EXP_UNIT);
        return new_node_id;
    }
    TypeSpecID get_unit_exp() {
        return s_mgr->singleton_cache().exp_unit;
    }
    ExpID new_int_exp(
        size_t mantissa,
        bool is_neg
    ) {
        auto new_node_id = help_alloc_node(NodeKind::EXP_INT);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_int;

        info_ptr->mantissa = mantissa;
        info_ptr->is_neg = is_neg;

        return new_node_id;
    }
    ExpID new_float_exp(
        double value
    ) {
        auto new_node_id = help_alloc_node(NodeKind::EXP_FLOAT);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_float;

        info_ptr->value = value;

        return new_node_id;
    }
    ExpID new_string_exp(
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
    ExpID new_id_exp(
        DefID def_id
    ) {
        auto new_node_id = help_alloc_node(NodeKind::EXP_ID);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_id;

        info_ptr->def_id = def_id;

        return new_node_id;
    }
    ExpID new_func_call_exp(
        ExpID called_fn,
        size_t arg_exp_id_count,
        ExpID* arg_exp_id_array,
        bool call_is_non_tot
    ) {
        auto new_node_id = help_alloc_node(NodeKind::EXP_FUNC_CALL);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_call;
        
        info_ptr->arg_exp_count = arg_exp_id_count;
        info_ptr->arg_exp_array = new ExpID[arg_exp_id_count];
        for (size_t i = 0; i < arg_exp_id_count; i++) {
            info_ptr->arg_exp_array[i] = info_ptr->arg_exp_array[i];
        }

        return new_node_id;
    }
    ExpID new_unary_op_exp(
        UnaryOp unary_op,
        ExpID arg_exp
    ) {
        auto new_node_id = help_alloc_node(NodeKind::EXP_UNARY_OP);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_unary;

        info_ptr->unary_op = unary_op;
        info_ptr->arg_exp = arg_exp;

        return new_node_id;
    }
    ExpID new_binary_op_exp(
        BinaryOp binary_op,
        ExpID lt_arg_exp,
        ExpID rt_arg_exp
    ) {
        auto new_node_id = help_alloc_node(NodeKind::EXP_BINARY_OP);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_binary;

        info_ptr->binary_op = binary_op;
        info_ptr->lt_arg_exp = lt_arg_exp;
        info_ptr->rt_arg_exp = rt_arg_exp;

        return new_node_id;
    }
    ExpID new_if_then_else_exp(
        ExpID cond_exp,
        ExpID then_exp,
        ExpID else_exp
    ) {
        auto new_node_id = help_alloc_node(NodeKind::EXP_IF_THEN_ELSE);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_if_then_else;

        info_ptr->cond_exp = cond_exp;
        info_ptr->then_exp = then_exp;
        info_ptr->else_exp = else_exp;

        return new_node_id;
    }
    ExpID new_get_tuple_field_by_index_exp(
        ExpID tuple_exp_id,
        ExpID index_exp_id
    ) {
        auto new_node_id = help_alloc_node(NodeKind::EXP_GET_TUPLE_FIELD_BY_INDEX);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_get_tuple_field_by_index;

        info_ptr->tuple_exp_id = tuple_exp_id;
        info_ptr->index_exp_id = index_exp_id;

        return new_node_id;
    }
    ExpID new_lambda_exp(
        size_t arg_name_count,
        DefID* arg_name_array,
        ExpID body_exp
    ) {
        auto new_node_id = help_alloc_node(NodeKind::EXP_LAMBDA);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_lambda;

        info_ptr->arg_name_count = arg_name_count;
        info_ptr->arg_name_array = new DefID[arg_name_count];
        for (size_t i = 0; i < arg_name_count; i++) {
            info_ptr->arg_name_array[i] = arg_name_array[i];
        }

        return new_node_id;
    }
    ExpID new_allocate_one_exp(
        ExpID stored_val_exp_id,
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
    ExpID new_allocate_many_exp(
        ExpID initializer_stored_val_exp_id,
        ExpID alloc_count_exp,
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
    ExpID new_chain_exp(
        size_t prefix_elem_id_count,
        ElemID* prefix_elem_id_array,
        ExpID ret_exp_id
    ) {
        auto new_node_id = help_alloc_node(NodeKind::EXP_CHAIN);
        auto info_ptr = &get_info_ptr(new_node_id)->exp_chain;

        info_ptr->prefix_elem_count = prefix_elem_id_count;
        info_ptr->prefix_elem_array = new ElemID[prefix_elem_id_count];
        for (size_t i = 0; i < prefix_elem_id_count; i++) {
            info_ptr->prefix_elem_array[i] = prefix_elem_id_array[i];
        }

        return new_node_id;
    }
    ElemID new_bind1v_elem(
        DefID bound_def_id, 
        ExpID init_exp_id
    ) {
        auto new_node_id = help_alloc_node(NodeKind::ELEM_BIND1V);
        auto info_ptr = &get_info_ptr(new_node_id)->elem_bind1v;

        info_ptr->bound_def_id = bound_def_id;
        info_ptr->init_exp_id = init_exp_id;

        return new_node_id;
    }
    ElemID new_do_elem(
        ExpID eval_exp_id
    ) {
        auto new_node_id = help_alloc_node(NodeKind::ELEM_DO);
        auto info_ptr = &get_info_ptr(new_node_id)->elem_do;

        info_ptr->eval_exp_id = eval_exp_id;

        return new_node_id;
    }

}
