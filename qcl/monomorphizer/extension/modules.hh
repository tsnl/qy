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
    void add_mono_module_ts_field(
        MonoModID template_id,
        DefID field_def_id
    );
    void add_mono_module_exp_field(
        MonoModID template_id,
        DefID field_def_id
    );

    // ArgListID: unique IDs for actual argument tuples.
    // ID equality <=> tuple equality (val_equals for value IDs, 
    // type_equals for type IDs)
    extern ArgListID const EMPTY_ARG_LIST_ID;
    ArgListID get_arg_list_with_type_id_prepended(
        ArgListID list,
        mtype::MTypeID type_id
    );
    ArgListID get_arg_list_with_value_id_prepended(
        ArgListID list,
        mval::ValueID value_id
    );

    // Polymorphic template construction:
    PolyModID new_polymorphic_module(
        char* mv_template_name,
        size_t bv_def_id_count,
        DefID* mv_bv_def_id_array
    );
    void add_poly_module_ts_field(
        PolyModID template_id,
        DefID field_def_id
    );
    void add_poly_module_exp_field(
        PolyModID template_id,
        DefID field_def_id
    );

    // instantiation:
    MonoModID instantiate_poly_mod(
        PolyModID poly_mod_id,
        ArgListID arg_list_id
    );

    // TODO evaluation:
    // accept a non-TOT def + an optional substitution map for all BV_DEF_ID
    // output a TOT def, suitable for mono mod fields
    

}
