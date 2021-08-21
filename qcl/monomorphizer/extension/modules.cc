#include "modules.hh"

#include <vector>
#include <deque>
#include <map>
#include <string>
#include <iostream>
#include <cstdint>
#include <cassert>

#include "mast.hh"
#include "gdef.hh"
#include "mtype.hh"
#include "panic.hh"
#include "mval.hh"
#include "arg-list.hh"
#include "shared-enums.hh"
#include "sub.hh"
#include "panic.hh"
#include "eval.hh"

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
        PolyModID parent_mod_id
    ) {
        MonoModID id = s_mono_mod_info_table.size();
        s_mono_common_info_table.push_back({{}, mv_name});
        s_mono_mod_info_table.push_back({parent_mod_id});
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
// Interface: monomorphize sub-graph
//

namespace monomorphizer::modules {

    MonoModID instantiate_poly_mod(
        PolyModID poly_mod_id,
        arg_list::ArgListID arg_list_id
    ) {
        CommonModInfo const* base = &s_poly_common_info_table[poly_mod_id];
        char const* mod_name = base->name; 

        // debug:
        std::cout << "DEBUG: instantiating poly-mod " << poly_mod_id << " with args " << arg_list_id << std::endl;
        arg_list::print_arg_list(arg_list_id);

        // checking if we have instantiated this module with these args before:
        // NOTE: `info` is a `const` reference if only cache read:
        {
            PolyModInfo const* info = &s_poly_custom_info_table[poly_mod_id];
            auto it = info->instantiated_mono_mods_cache.find(arg_list_id);
            if (it != info->instantiated_mono_mods_cache.end()) {
                return it->second;
            }
        }

        // In order to handle cyclic references, we must first declare the monomorphic module fields and cache the
        // module BEFORE evaluating field expressions/typespecs to find values.
        // This way, a reference to the mono field can be taken before the value is known.
        // We create and cache the mono module here:

        // generating a substitution to instantiate using provided args, 
        // generating the `mono_mod_id`:
        sub::Substitution* instantiating_sub = sub::create();;
        MonoModID mono_mod_id;
        GDefID* replacement_gdef_array = nullptr;
        {
            // creating target mono mod:
            PolyModInfo* info = &s_poly_custom_info_table[poly_mod_id];
            auto cp_name = strdup(base->name);
            mono_mod_id = modules::new_monomorphic_module(cp_name, poly_mod_id);
            
            // adding fields for (1) poly mod fields and (2) formal args
            //  - NOTE: must add poly mod fields first so indices can be blindly copied
            {
                // This segment is the first key to monomorphization:
                // it defines a new CONST with a total value/type that be used as a 
                // replacement during sub&copy.
                // WHY TOTAL? If we pass an AST node that uses a subbed ID, we have 
                // problems. Furthermore, AST node would need to be re-evaluated.
                // Instead, storing computed value helps us cache.
                // We can't use this everywhere because non-total constants may be bound,
                // e.g. a = b where b is a parameter.

                // FIRST, adding poly mod fields:
                for (GDefID poly_field_def_id: base->fields) {
                    auto poly_field_def_kind = gdef::get_def_kind(poly_field_def_id);
                    bool is_poly_field_def_tid_not_vid = (poly_field_def_kind == gdef::DefKind::CONST_TS);
                    if (!is_poly_field_def_tid_not_vid) {
                        assert(poly_field_def_kind == gdef::DefKind::CONST_EXP);
                    }
                    char* cp_bound_name = strdup(gdef::get_def_name(poly_field_def_id));

                    gdef::DefKind mono_field_def_kind = (
                        (is_poly_field_def_tid_not_vid) ?
                        gdef::DefKind::CONST_TOT_TID :
                        gdef::DefKind::CONST_TOT_VAL
                    );
                    GDefID mono_field_def_id = gdef::declare_global_def(mono_field_def_kind, cp_bound_name);
                    modules::add_mono_module_field(mono_mod_id, mono_field_def_id);
                }

                // SECOND, adding template arg fields, that just map to constants once monomorphized:
                // FIXME: these are separate definitions than used in the substitution.
                // Simultaneously updating 'sub' object:
                if (info->bv_count) {
                    replacement_gdef_array = static_cast<GDefID*>(malloc(sizeof(GDefID) * info->bv_count));
                    arg_list::ArgListID remaining_arg_list_id = arg_list_id;
                    for (size_t i = 0; i < info->bv_count; i++) {
                        size_t poly_formal_arg_index = info->bv_count - (i+1);
                        GDefID poly_formal_bv_def_id = info->bv_def_id_array[poly_formal_arg_index];

                        char* cp_bound_name = strdup(gdef::get_def_name(poly_formal_bv_def_id));

                        assert(remaining_arg_list_id != arg_list::EMPTY_ARG_LIST);
                        size_t mono_actual_arg_id = arg_list::head(remaining_arg_list_id);
                        remaining_arg_list_id = arg_list::tail(remaining_arg_list_id);

                        gdef::DefKind mono_def_kind;
                        switch (gdef::get_def_kind(poly_formal_bv_def_id)) {
                            case gdef::DefKind::BV_EXP: {
                                mono_def_kind = gdef::DefKind::CONST_TOT_VAL;
                            } break;
                            case gdef::DefKind::BV_TS: {
                                mono_def_kind = gdef::DefKind::CONST_TOT_TID;
                            } break;
                            default: {
                                throw new Panic("Unknown template arg def kind");
                            }
                        }
                        GDefID mono_field_def_id = gdef::declare_global_def(mono_def_kind, cp_bound_name);
                        modules::add_mono_module_field(mono_mod_id, mono_field_def_id);
                        replacement_gdef_array[poly_formal_arg_index] = mono_field_def_id;

                        // since we have the value of the template arg already, we define it here too:
                        gdef::set_def_target(mono_field_def_id, mono_actual_arg_id);

                        // updating the `substitution` object:
                        sub::add_monomorphizing_replacement(
                            instantiating_sub, 
                            poly_formal_bv_def_id, 
                            mono_field_def_id
                        );
                    }
                    assert(remaining_arg_list_id == arg_list::EMPTY_ARG_LIST);
                }
            }

            // caching:
            info->instantiated_mono_mods_cache.insert({arg_list_id, mono_mod_id});
        }

        // evaluating and setting target for monomorphic fields:
        {
            size_t field_count = base->fields.size();
            for (size_t i = 0; i < field_count; i++) {
                // acquiring the poly field:
                GDefID poly_field_def_id = base->fields[i];
                gdef::DefKind poly_field_def_kind = gdef::get_def_kind(poly_field_def_id);
                size_t raw_poly_field_target = gdef::get_def_target(poly_field_def_id);
                
                // acquiring the mono field:
                GDefID mono_field_def_id = get_mono_mod_field_at(mono_mod_id, i);

                std::cout
                    << "DEBUG: Computing evaluated target for field " << i
                    << " with name '" << gdef::get_def_name(mono_field_def_id) << "'"
                    << "..." << std::endl;

                // evaluating the poly field:
                size_t raw_mono_field_target;
                switch (poly_field_def_kind) {
                    case gdef::DefKind::CONST_EXP: {
                        mast::ExpID poly_field_target = raw_poly_field_target;
                        mval::ValueID mono_field_target = eval::eval_exp(poly_field_target, instantiating_sub);
                        raw_mono_field_target = mono_field_target;
                    } break;
                    case gdef::DefKind::CONST_TS: {
                        mast::TypeSpecID poly_field_target = raw_poly_field_target;
                        mtype::TID mono_field_target = eval::eval_type(poly_field_target, instantiating_sub);
                        raw_mono_field_target = mono_field_target;
                    } break;
                    default: {
                        throw new Panic("Invalid DefKind in PolyMod field");
                    }
                }

                std::cout 
                    << "DEBUG: Setting evaluated target for field " << i
                    << " with name '" << gdef::get_def_name(mono_field_def_id) << "'"
                    << " to target value " << raw_mono_field_target
                    << std::endl;

                // setting the target of the mono field to be the evaluated poly field:
                if (raw_mono_field_target != NULL_MONO_MOD_ID) {
                    gdef::set_def_target(mono_field_def_id, raw_mono_field_target);
                } else {
                    // debug: ignore for now...
                }
            }
        }

        // cleaning up:
        {
            sub::destroy(instantiating_sub);
        }
        
        // finally, returning the fresh MonoModID:
        {
            return mono_mod_id;
        }
    }

    size_t count_all_mono_modules() {
        return s_mono_common_info_table.size();
    }

}
