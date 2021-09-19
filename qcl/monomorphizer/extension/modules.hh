// This module accepts polymorphic and monomorphic templates.
// It then monomorphizes all loaded templates at once
//  - begin with a monomorphic root template
//  - if any expression or type-spec references a polymorphic template,
//    we replace the reference with a reference to a fresh monomorphic template.
//  - any unreachable code is ignored
//  - the same TemplateID 

#pragma once

#include <vector>

#include "id-modules.hh"
#include "id-gdef.hh"
#include "id-mast.hh"
#include "id-mval.hh"
#include "id-mtype.hh"
#include "id-arg-list.hh"

namespace monomorphizer::modules {

    // constants:
    extern MonoModID const NULL_MONO_MOD_ID;
    extern PolyModID const NULL_POLY_MOD_ID;

    // Monomorphic template construction:
    MonoModID new_monomorphic_module(
        char* mv_template_name,
        PolyModID parent_template_id,
        size_t source_node_index
    );
    // add_field pushes a field and returns its unique index.
    size_t add_mono_module_field(
        MonoModID template_id,
        GDefID field_def_id
    );

    // Polymorphic template construction:
    PolyModID new_polymorphic_module(
        char* mv_template_name,
        size_t bv_def_id_count,
        GDefID* mv_bv_def_id_array,
        size_t source_node_index
    );
    // add_field pushes a field and returns the field's unique index.
    size_t add_poly_module_field(
        PolyModID template_id,
        GDefID field_def_id
    );
    
    // Module fields are accessed by an index that is determined by the order
    // in which symbols are added.
    // By convention, this should be the order in which source nodes are written 
    // in source code.
    // TODO: consider replacing names with IntStr
    char const* get_mono_mod_name(MonoModID mono_mod_id);
    char const* get_poly_mod_name(PolyModID poly_mod_id);
    size_t get_mono_mod_field_count(PolyModID poly_mod_id);
    GDefID get_mono_mod_field_at(MonoModID mono_mod_id, size_t field_index);
    size_t get_poly_mod_field_count(MonoModID mono_mod_id);
    GDefID get_poly_mod_field_at(PolyModID poly_mod_id, size_t field_index);
    size_t get_poly_mod_formal_arg_count(PolyModID poly_mod_id);
    GDefID get_poly_mod_formal_arg_at(PolyModID poly_mod_id, size_t arg_index);
    PolyModID get_mono_mod_origin_poly_mod(MonoModID mono_mod_id);

    // instantiation: 
    // turn a PolyModID into a MonoModID using some template arguments.
    MonoModID instantiate_poly_mod(
        PolyModID poly_mod_id,
        arg_list::ArgListID arg_list_id
    );

    // in monomorphization, we want to store all lambda function expressions.
    void register_lambda(
        MonoModID mono_mod_id, 
        mast::ExpID mono_lambda_exp
    );

    size_t count_registered_lambdas(MonoModID mono_mod_id);
    mast::ExpID get_registered_lambda_at(
        MonoModID mono_mod_id,
        size_t lambda_index
    );
    size_t get_mono_mod_source_node_index(
        MonoModID mono_mod_id
    );

    // system info:
    size_t count_all_mono_modules();

}
