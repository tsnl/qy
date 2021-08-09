// This module accepts polymorphic and monomorphic templates.
// It then monomorphizes all loaded templates at once
//  - begin with a monomorphic root template
//  - if any expression or type-spec references a polymorphic template,
//    we replace the reference with a reference to a fresh monomorphic template.
//  - any unreachable code is ignored
//  - the same TemplateID 

#pragma once

#include "id-modules.hh"
#include "id-defs.hh"
#include "id-mast.hh"
#include "id-mval.hh"
#include "id-mtype.hh"
#include "id-arg-list.hh"

namespace monomorphizer::modules {

    // constants:
    extern MonoModID const NULL_MONO_MOD_ID;
    extern PolyModID const NULL_POLY_MOD_ID;

    // module management:
    void ensure_init();
    void drop();

    // Monomorphic template construction:
    MonoModID new_monomorphic_module(
        char* mv_template_name,
        PolyModID opt_parent_template_id
    );
    // add_field pushes a field and returns its unique index.
    size_t add_mono_module_field(
        MonoModID template_id,
        DefID field_def_id
    );

    // Polymorphic template construction:
    PolyModID new_polymorphic_module(
        char* mv_template_name,
        size_t bv_def_id_count,
        DefID* mv_bv_def_id_array
    );
    // add_field pushes a field and returns the field's unique index.
    size_t add_poly_module_field(
        PolyModID template_id,
        DefID field_def_id
    );
    
    // Module fields are accessed by an index that is determined by the order
    // in which symbols are added.
    // By convention, this should be the order in which source nodes are written 
    // in source code.
    DefID get_mono_mod_field_at(
        MonoModID mono_mod_id,
        size_t field_index
    );
    DefID get_poly_mod_field_at(
        PolyModID poly_mod_id,
        size_t field_index
    );

    // instantiation: 
    // turn a PolyModID into a MonoModID using some template arguments.
    MonoModID instantiate_poly_mod(
        PolyModID poly_mod_id,
        arg_list::ArgListID arg_list_id
    );

}
