#include "modules.hh"

#include <vector>
#include <deque>
#include <string>
#include <cstdint>
#include <cassert>

#include "mast.hh"
#include "defs.hh"
#include "mtype.hh"
#include "panic.hh"
#include "mval.hh"

//
// Implementation: Compile-time constants
//

namespace monomorphizer::modules {
    extern MonoModID const NULL_MONO_TEMPLATE_ID = -1;
    extern PolyModID const NULL_POLY_TEMPLATE_ID = -1;
}

//
// Implementation: arg-list tries:
//

namespace monomorphizer::modules {

    using ArgTrieNodeID = size_t;
    
    ArgTrieNodeID const NULL_ATN_ID = -1;
    
    struct ArgTrieNode;
    struct ArgTrieEdge;

    struct ArgTrieNode {
        std::vector<ArgTrieEdge> m_forward_type_edges;
        std::vector<ArgTrieEdge> m_forward_value_edges;
        ArgTrieNodeID m_parent_node_id;

        ArgTrieNode(
            ArgTrieNodeID parent_node_id
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

    ArgTrieNodeID new_atn(ArgTrieNodeID parent_node_id) {
        ArgTrieNodeID new_id = s_atn_table.size();
        s_atn_table.emplace_back(parent_node_id);
        return new_id;
    }

    ArgTrieNodeID get_atn_with_value_appended(
        ArgTrieNodeID root, 
        mval::ValueID appended_value_id
    );
    ArgTrieNodeID get_atn_with_type_appended(
        ArgTrieNodeID root, 
        mtype::MTypeID appended_type_id
    );

    // need a way to ID values uniquely/hash them into keys (cf above)
    //   - can use `val_equals`
    // need to pass TID to MAST type-specifiers
    //   - guaranteed to be unique by typer
    //   - can use these TIDs as keys

    // ONCE we have a serializable `Value` format and a `TID`, we can use a 
    // hash-map to build a trie.

    // Then, each Trie node represents a unique, non-negative list of args.

    ArgTrieNode::ArgTrieNode(
        ArgTrieNodeID parent_node_id
    )
    :   m_parent_node_id(parent_node_id),
        m_forward_type_edges(),
        m_forward_value_edges()
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
            ArgTrieNodeID fresh_dst_id = new_atn(root);
            edges_vec_p->emplace_back(
                appended_id,
                fresh_dst_id
            );
            return fresh_dst_id;
        }
    }
    ArgTrieNodeID get_atn_with_value_appended(
        ArgTrieNodeID root, 
        mval::ValueID appended_value_id
    ) {
        return help_get_atn_with_id_appended(
            root,
            appended_value_id,
            true
        );
    }
    ArgTrieNodeID get_atn_with_type_appended(
        ArgTrieNodeID root, 
        mtype::MTypeID appended_type_id
    ) {
        return help_get_atn_with_id_appended(
            root,
            appended_type_id,
            false
        );
    }

}

//
// Implementation: module data storage
//

namespace monomorphizer::modules {

    struct CommonModInfo32 {
        std::vector<mast::NameNodeRelation> fields;
        char* name;
    };

    struct MonoModInfo {
        PolyModID opt_parent_mod_id;
    };

    struct PolyModInfo {
        size_t bv_count;
        DefID* bv_def_id_array;
    };

    static std::vector<CommonModInfo32> s_mono_common_info_table;
    static std::vector<MonoModInfo> s_mono_mod_info_table;

    static std::vector<CommonModInfo32> s_poly_common_info_table;
    static std::vector<PolyModInfo> s_poly_custom_info_table;
}

//
// Implementation: lazily getting MonoModID from PolyModID
//

//
// Interface: Construction
//

namespace monomorphizer::modules {

    void ensure_init() {
        mast::ensure_init();
        defs::ensure_init();
    }
    void drop() {
        mast::drop();
        defs::drop();
    }

    // Monomorphic template construction:
    MonoModID new_monomorphic_template(
        char* mv_name,
        PolyModID opt_parent_mod_id
    ) {
        MonoModID id = s_mono_mod_info_table.size();
        s_mono_common_info_table.push_back({{}, mv_name});
        s_mono_mod_info_table.push_back({opt_parent_mod_id});
        return id;
    }
    void add_mono_template_ts_field(
        MonoModID template_id,
        DefID subbed_polymorphic_field_const_def_id,
        TypeSpecID bound_ts_id
    ) {
        s_mono_common_info_table[template_id].fields.push_back({
            subbed_polymorphic_field_const_def_id,
            bound_ts_id
        });
    }
    void add_mono_template_exp_field(
        MonoModID template_id,
        DefID subbed_polymorphic_field_const_def_id,
        ExpID bound_exp_id
    ) {
        s_mono_common_info_table[template_id].fields.push_back({
            subbed_polymorphic_field_const_def_id,
            bound_exp_id
        });
    }

    // Polymorphic template construction:
    PolyModID new_polymorphic_template(
        char* mv_template_name,
        size_t bv_def_id_count,
        DefID* mv_bv_def_id_array
    ) {
        PolyModID id = s_poly_custom_info_table.size();
        s_poly_common_info_table.push_back({{}, mv_template_name});
        s_poly_custom_info_table.push_back(
            {bv_def_id_count, mv_bv_def_id_array}
        );
        return id;
    }
    void add_poly_template_ts_field(
        PolyModID template_id,
        DefID subbed_polymorphic_field_const_def_id,
        TypeSpecID bound_ts_id
    ) {
        s_poly_common_info_table[template_id].fields.push_back({
            subbed_polymorphic_field_const_def_id,
            bound_ts_id
        });
    }
    void add_poly_template_exp_field(
        PolyModID template_id,
        DefID subbed_polymorphic_field_const_def_id,
        ExpID bound_exp_id
    ) {
        s_poly_common_info_table[template_id].fields.push_back({
            subbed_polymorphic_field_const_def_id,
            bound_exp_id
        });
    }

}

//
// Interface: monomorphize sub-graph
//

namespace monomorphizer::modules {

    void monomorphize_subgraph(MonoModID first_mono_template_id) {
        // todo: scan for GetFieldInPolyMod, get monomorph, and execute
        // todo: use the ArgTrieNode data-structure to make each actual arg list
        //       a unique ID, resilient to value equality. 
    }

}
