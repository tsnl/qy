#include "modules.hh"

#include <vector>
#include <deque>
#include <map>
#include <string>
#include <cstdint>
#include <cassert>

#include "mast.hh"
#include "gdef.hh"
#include "mtype.hh"
#include "panic.hh"
#include "mval.hh"
#include "arg-list.hh"
#include "shared-enums.hh"

//
// Implementation: Compile-time constants
//

namespace monomorphizer::modules {
    extern MonoModID const NULL_MONO_MOD_ID = UNIVERSAL_NULL_ID;
    extern PolyModID const NULL_POLY_MOD_ID = UNIVERSAL_NULL_ID;
}

//
// Implementation: module data storage
//

namespace monomorphizer::modules {

    struct CommonModInfo {
        std::vector<GDefID> fields;
        char* name;
    };

    struct MonoModInfo {
        PolyModID opt_parent_mod_id;
    };

    struct PolyModInfo {
        size_t bv_count;
        GDefID* bv_def_id_array;
        std::map<arg_list::ArgListID, MonoModID> instantiated_mono_mods_cache;
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
    size_t add_mono_module_field(
        MonoModID template_id,
        GDefID field_def_id
    ) {
        auto const def_kind = gdef::get_def_kind(field_def_id);
        assert((
            def_kind == gdef::DefKind::CONST_TOT_TID ||
            def_kind == gdef::DefKind::CONST_TOT_VAL
        ) && "Cannot bind fields in mono-modules without first evaluating.");
        
        auto& fields = s_mono_common_info_table[template_id].fields;
        size_t index = fields.size();
        fields.push_back(field_def_id);
        return index;
    }

    // Polymorphic template construction:
    PolyModID new_polymorphic_module(
        char* mv_template_name,
        size_t bv_def_id_count,
        GDefID* mv_bv_def_id_array
    ) {
        PolyModID id = s_poly_custom_info_table.size();
        s_poly_common_info_table.push_back({{}, mv_template_name});
        s_poly_custom_info_table.push_back(
            {bv_def_id_count, mv_bv_def_id_array}
        );
        return id;
    }
    size_t add_poly_module_field(
        PolyModID template_id,
        GDefID field_def_id
    ) {
        auto& fields = s_poly_common_info_table[template_id].fields;
        size_t index = fields.size();
        fields.push_back(field_def_id);
        return index;
    }

}

//
// Interface: getting fields at an index
//

namespace monomorphizer::modules {

    size_t get_poly_mod_field_count(PolyModID poly_mod_id) {
        return s_poly_common_info_table[poly_mod_id].fields.size();
    }
    size_t get_mono_mod_field_count(MonoModID mono_mod_id) {
        return s_mono_common_info_table[mono_mod_id].fields.size();
    }

    char const* get_mono_mod_name(MonoModID mono_mod_id) {
        return s_mono_common_info_table[mono_mod_id].name;
    }
    char const* get_poly_mod_name(PolyModID poly_mod_id) {
        return s_poly_common_info_table[poly_mod_id].name;
    }

    GDefID get_mono_mod_field_at(
        MonoModID mono_mod_id,
        size_t field_index
    ) {
        return s_mono_common_info_table[mono_mod_id].fields[field_index];
    }

    GDefID get_poly_mod_field_at(
        PolyModID poly_mod_id,
        size_t field_index
    ) {
        return s_poly_common_info_table[poly_mod_id].fields[field_index];
    }

    size_t get_poly_mod_formal_arg_count(PolyModID poly_mod_id) {
        return s_poly_custom_info_table[poly_mod_id].bv_count;
    }
    GDefID get_poly_mod_formal_arg_at(PolyModID poly_mod_id, size_t arg_index) {
        auto poly_mod_info = &s_poly_custom_info_table[poly_mod_id];
        return poly_mod_info->bv_def_id_array[arg_index];
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
    GDefID def_new_total_const_val_for_bv_sub(
        char const* mod_name,
        GDefID bv_def_id,
        size_t bound_id
    ) {
        gdef::DefKind bv_def_kind = gdef::get_def_kind(bv_def_id);
        char* mv_def_name = strdup(gdef::get_def_name(bv_def_id));
        switch (bv_def_kind) {
            case gdef::DefKind::BV_EXP: {
                mval::ValueID val_id = bound_id;
                return gdef::declare_global_def(gdef::DefKind::CONST_TOT_VAL, mv_def_name);
            } break;
            case gdef::DefKind::BV_TS: {
                mtype::TID type_id = bound_id;
                return gdef::declare_global_def(gdef::DefKind::CONST_TOT_TID, mv_def_name);
            } break;
            default: {
                throw new Panic("Invalid Def Kind in bv_def_id_array");
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
        arg_list::ArgListID arg_list_id
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
        arg_list::ArgListID arg_list_it = arg_list_id;
        for (size_t i = 0; i < info->bv_count; i++) {
            // iterating in reverse order to efficiently traverse the ArgList
            int arg_index = (info->bv_count - 1) - i;
            assert(
                (arg_list_it != arg_list::EMPTY) && 
                "ERROR: ArgList too short"
            );
            
            // todo: generate a substitution
            //  - replace `bv_def_id` with `replacement_def_id`
            GDefID bv_def_id = info->bv_def_id_array[arg_index];
            size_t bound_id = arg_list::head(arg_list_it);
            GDefID replacement_def_id = def_new_total_const_val_for_bv_sub(
                mod_name,
                bv_def_id, bound_id
            );
            
            // updating for the next iteration:
            // - `i` will update second, after this loop body is run.
            // - updating `arg_list_it`:
            arg_list_it = arg_list::tail(arg_list_it);
        }
        assert(arg_list_it == arg_list::EMPTY && "ERROR: ArgList too long");

        // copy this module's contents with substitutions applied
        

        // todo: REMEMBER TO CACHE THE FRESH MONO ID
        // todo: return the fresh mono ID
        return NULL_MONO_MOD_ID;
    }

}
