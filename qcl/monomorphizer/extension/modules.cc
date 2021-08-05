#include "modules.hh"

#include <vector>
#include <deque>
#include <map>
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
    extern MonoModID const NULL_MONO_MOD_ID = -1;
    extern PolyModID const NULL_POLY_MOD_ID = -1;
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
        mtype::MTypeID appended_type_id
    );

    ArgTrieNode::ArgTrieNode(
        ArgTrieNodeID parent_node_id,
        size_t incoming_edge_appended_id
    )
    :   m_parent_node_id(parent_node_id),
        m_forward_type_edges(),
        m_forward_value_edges(),
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
        mtype::MTypeID appended_type_id
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

namespace monomorphizer::modules {

    extern ArgListID const EMPTY_ARG_LIST_ID = NULL_ATN_ID;

    ArgListID get_arg_list_with_type_id_prepended(
        ArgListID list,
        mtype::MTypeID type_id
    ) {
        return static_cast<ArgListID>(
            get_atn_with_type_prepended(
                static_cast<ArgTrieNodeID>(list), 
                type_id
            )
        );
    }

    ArgListID get_arg_list_with_value_id_prepended(
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

}

//
// Implementation: module data storage
//

namespace monomorphizer::modules {

    struct CommonModInfo {
        std::vector<DefID> fields;
        char* name;
    };

    struct MonoModInfo {
        PolyModID opt_parent_mod_id;
    };

    struct PolyModInfo {
        size_t bv_count;
        DefID* bv_def_id_array;
        std::map<ArgListID, MonoModID> instantiated_mono_mods_cache;
    };

    static std::vector<CommonModInfo> s_mono_common_info_table;
    static std::vector<MonoModInfo> s_mono_mod_info_table;

    static std::vector<CommonModInfo> s_poly_common_info_table;
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
    MonoModID new_monomorphic_module(
        char* mv_name,
        PolyModID opt_parent_mod_id
    ) {
        MonoModID id = s_mono_mod_info_table.size();
        s_mono_common_info_table.push_back({{}, mv_name});
        s_mono_mod_info_table.push_back({opt_parent_mod_id});
        return id;
    }
    void add_mono_module_ts_field(
        MonoModID template_id,
        DefID field_def_id
    ) {
        auto const def_kind = defs::get_def_kind(field_def_id);
        assert((
            def_kind == defs::DefKind::CONST_TOT_TID ||
            def_kind == defs::DefKind::CONST_TOT_VAL
        ) && "Cannot bind fields in mono-modules without first evaluating.");
        s_mono_common_info_table[template_id].fields.push_back(field_def_id);
    }
    void add_mono_module_exp_field(
        MonoModID template_id,
        DefID field_def_id
    ) {
        s_mono_common_info_table[template_id].fields.push_back(field_def_id);
    }

    // Polymorphic template construction:
    PolyModID new_polymorphic_module(
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
    void add_poly_module_ts_field(
        PolyModID template_id,
        DefID field_def_id
    ) {
        s_poly_common_info_table[template_id].fields.push_back(field_def_id);
    }
    void add_poly_module_exp_field(
        PolyModID template_id,
        DefID subbed_polymorphic_field_const_def_id,
        ExpID bound_exp_id
    ) {
        s_poly_common_info_table[template_id].fields.push_back(
            subbed_polymorphic_field_const_def_id
        );
    }

}

//
// Implementation: monomorphize sub-graph
//

namespace monomorphizer::modules {

    // This function is the first key to monomorphization:
    // it defines a new CONST with a total value/type that be used as a 
    // replacement during sub&copy.
    // WHY TOTAL? If we pass an AST node that uses a subbed ID, we have 
    // problems. Furthermore, AST node would need to be re-evaluated.
    // Instead, storing computed value helps us cache.
    // We can't use this everywhere because non-total constants may be bound,
    // e.g. a = b where b is a parameter.
    DefID def_new_total_const_val_for_bv_sub(
        char const* mod_name,
        DefID bv_def_id,
        size_t bound_id
    ) {
        defs::DefKind bv_def_kind = defs::get_def_kind(bv_def_id);
        char const* def_name = defs::get_def_name(bv_def_id);
        switch (bv_def_kind) {
            case defs::DefKind::BV_EXP: {
                mval::ValueID val_id = bound_id;
                return defs::define_total_const_value(
                    mod_name, def_name,
                    val_id, true
                );
            } break;
            case defs::DefKind::BV_TS: {
                mtype::MTypeID type_id = bound_id;
                return defs::define_total_const_type(
                    mod_name, def_name,
                    type_id, true
                );
            } break;
            default: {
                assert(0 && "Invalid Def Kind in bv_def_id_array");
                return defs::NULL_DEF_ID;
            } break;
        };
    }

    // sub&copy is the second key to monomorphization.
    // - TODO: when subbing, always replace with TOTAL_CONST definitions after
    //   evaluation--
    //   THUS, monomorphic

}

//
// Interface: monomorphize sub-graph
//

namespace monomorphizer::modules {

    MonoModID instantiate_poly_mod(
        PolyModID poly_mod_id,
        ArgListID arg_list_id
    ) {
        CommonModInfo const* base = &s_poly_common_info_table[poly_mod_id];
        PolyModInfo const* info = &s_poly_custom_info_table[poly_mod_id];
        char const* mod_name = base->name; 

        // checking if we have instantiated this module with these args before:
        auto it = info->instantiated_mono_mods_cache.find(arg_list_id);
        if (it == info->instantiated_mono_mods_cache.end()) {
            return it->second;
        }

        // instantiating this module with these args by creating a fresh
        // MonoModID
        ArgTrieNodeID atn_head_id = arg_list_id;
        for (int i = 0; i < info->bv_count; i++) {
            // iterating in reverse order to efficiently traverse the ArgList
            int arg_index = (info->bv_count - 1) - i;
            assert(atn_head_id != NULL_ATN_ID && "ERROR: ArgList too short");
            ArgTrieNode const* atn_info = &s_atn_table[atn_head_id];

            // todo: generate a substitution
            //  - replace `bv_def_id` with `replacement_def_id`
            DefID bv_def_id = info->bv_def_id_array[arg_index];
            size_t bound_id = atn_last_inserted_id(atn_head_id);
            DefID replacement_def_id = def_new_total_const_val_for_bv_sub(
                mod_name,
                bv_def_id, bound_id
            );
            
            // updating for the next iteration:
            // - `i` will update second, after this loop body is run.
            // - updating `atn_head_id`:
            atn_head_id = atn_info->m_parent_node_id;
        }
        assert(atn_head_id == NULL_ATN_ID && "ERROR: ArgList too long");

        // todo: copy this module's contents with substitutions applied
        
        // todo: REMEMBER TO CACHE THE FRESH MONO ID
        // todo: return the fresh mono ID
        return NULL_MONO_MOD_ID;
    }

    void monomorphize_subgraph(MonoModID first_mono_module_id) {
        // todo: scan for GetFieldInPolyMod, get monomorph, and execute
        // todo: use the ArgTrieNode data-structure to make each actual arg list
        //       a unique ID, resilient to value equality.
    }

}
