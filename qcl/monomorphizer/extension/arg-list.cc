#include "arg-list.hh"

#include <vector>
#include <deque>
#include <cstddef>

#include "mval.hh"

//
// Implementation: arg-list tries:
//

namespace monomorphizer::arg_list {

    using ArgTrieNodeID = size_t;
    
    ArgTrieNodeID const NULL_ATN_ID = -1;
    
    struct ArgTrieNode;
    struct ArgTrieEdge;

    struct ArgTrieNode {
        std::vector<ArgTrieEdge> m_forward_type_edges;
        std::vector<ArgTrieEdge> m_forward_value_edges;
        ArgTrieNodeID m_parent_node_id;
        size_t m_incoming_edge_appended_id;

        ArgTrieNode(
            ArgTrieNodeID parent_node_id,
            size_t incoming_edge_appended_id
        );
    };
    struct ArgTrieEdge {
        size_t m_appended_id;
        ArgTrieNodeID m_dst;

        ArgTrieEdge(
            size_t appended_id,
            ArgTrieNodeID dst_node_id
        );
    };

    static std::deque<ArgTrieNode> s_atn_table = {};
    static std::vector<ArgTrieEdge> s_atn_root_type_edges;
    static std::vector<ArgTrieEdge> s_atn_root_value_edges;

    ArgTrieNodeID new_atn(
        ArgTrieNodeID parent_node_id, 
        size_t incoming_edge_appended_id
    ) {
        ArgTrieNodeID new_id = s_atn_table.size();
        s_atn_table.emplace_back(parent_node_id, incoming_edge_appended_id);
        return new_id;
    }

    ArgTrieNodeID get_atn_with_value_prepended(
        ArgTrieNodeID root, 
        mval::ValueID appended_value_id
    );
    ArgTrieNodeID get_atn_with_type_prepended(
        ArgTrieNodeID root, 
        mtype::TID appended_type_id
    );

    ArgTrieNode::ArgTrieNode(
        ArgTrieNodeID parent_node_id,
        size_t incoming_edge_appended_id
    )
    :   m_forward_type_edges(),
        m_forward_value_edges(),
        m_parent_node_id(parent_node_id),
        m_incoming_edge_appended_id(incoming_edge_appended_id)
    {}

    ArgTrieEdge::ArgTrieEdge(
        size_t appended_id,
        ArgTrieNodeID dst_node_id
    )
    :   m_appended_id(appended_id),
        m_dst(dst_node_id)
    {}

    ArgTrieNodeID get_cached_dst(
        std::vector<ArgTrieEdge> const& edges_vec,
        size_t const appended_id,
        bool const check_id_val_equality
    ) {
        for (auto edge: edges_vec) {
            auto edge_id = edge.m_appended_id;
            auto dst_id = edge.m_dst;

            if (check_id_val_equality) {
                if (mval::equals(edge_id, appended_id)) {
                    return dst_id;
                }
            } else {
                if (edge_id == appended_id) {
                    return dst_id;
                }
            }
        }
        return NULL_ATN_ID;
    }
    ArgTrieNodeID help_get_atn_with_id_appended(
        ArgTrieNodeID root,
        size_t appended_id,
        bool appended_id_is_value_not_type_id
    ) {
        std::vector<ArgTrieEdge>* edges_vec_p = (
            (root == NULL_ATN_ID) ? 
            (
                appended_id_is_value_not_type_id ?
                    &s_atn_root_type_edges : 
                    &s_atn_root_value_edges
            ) 
            :
            (
                appended_id_is_value_not_type_id ?
                    &s_atn_table[root].m_forward_type_edges :
                    &s_atn_table[root].m_forward_value_edges
            )
        );
        ArgTrieNodeID cached_dst_node_id = get_cached_dst(
            *edges_vec_p,
            appended_id,
            appended_id_is_value_not_type_id
        );
        if (cached_dst_node_id != NULL_ATN_ID) {
            return cached_dst_node_id;
        } else {
            ArgTrieNodeID fresh_dst_id = new_atn(root, appended_id);
            edges_vec_p->emplace_back(
                appended_id,
                fresh_dst_id
            );
            return fresh_dst_id;
        }
    }
    ArgTrieNodeID get_atn_with_value_prepended(
        ArgTrieNodeID root, 
        mval::ValueID appended_value_id
    ) {
        return help_get_atn_with_id_appended(
            root,
            appended_value_id,
            true
        );
    }
    ArgTrieNodeID get_atn_with_type_prepended(
        ArgTrieNodeID root, 
        mtype::TID appended_type_id
    ) {
        return help_get_atn_with_id_appended(
            root,
            appended_type_id,
            false
        );
    }

    size_t atn_last_inserted_id(
        ArgTrieNodeID node
    ) {
        return s_atn_table[node].m_incoming_edge_appended_id;
    }

}

//
// Interface: ArgListID
//

namespace monomorphizer::arg_list {

    ArgListID const EMPTY_ARG_LIST = NULL_ATN_ID;

    ArgListID cons_tid(
        ArgListID list,
        mtype::TID type_id
    ) {
        return static_cast<ArgListID>(
            get_atn_with_type_prepended(
                static_cast<ArgTrieNodeID>(list), 
                type_id
            )
        );
    }

    ArgListID cons_val(
        ArgListID list,
        mval::ValueID value_id
    ) {
        return static_cast<ArgListID>(
            get_atn_with_value_prepended(
                static_cast<ArgTrieNodeID>(list),
                value_id
            )
        );
    }

    size_t head(ArgListID arg_list_id) {
        return atn_last_inserted_id(arg_list_id);
    }

    ArgListID tail(ArgListID arg_list_id) {
        auto parent_node_id = s_atn_table[arg_list_id].m_parent_node_id;
        return static_cast<ArgListID>(parent_node_id);
    }

    ArgListID empty_arg_list_id() {
        return EMPTY_ARG_LIST;
    }

}
