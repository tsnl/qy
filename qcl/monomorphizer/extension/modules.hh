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

namespace monomorphizer::modules {

    // constants:
    extern MonoModID const NULL_MONO_TEMPLATE_ID;
    extern PolyModID const NULL_POLY_TEMPLATE_ID;

    // module management:
    void ensure_init();
    void drop();

    // Monomorphic template construction:
    MonoModID new_monomorphic_template(
        char* mv_template_name,
        PolyModID opt_parent_template_id
    );
    void add_mono_template_ts_field(
        MonoModID template_id,
        DefID subbed_polymorphic_field_const_def_id,
        TypeSpecID bound_ts_id
    );
    void add_mono_template_exp_field(
        MonoModID template_id,
        DefID subbed_polymorphic_field_const_def_id,
        ExpID bound_exp_id
    );

    // Polymorphic template construction:
    PolyModID new_polymorphic_template(
        char* mv_template_name,
        size_t bv_def_id_count,
        DefID* mv_bv_def_id_array
    );
    void add_poly_template_ts_field(
        PolyModID template_id,
        DefID subbed_polymorphic_field_const_def_id,
        TypeSpecID bound_ts_id
    );
    void add_poly_template_exp_field(
        PolyModID template_id,
        DefID subbed_polymorphic_field_const_def_id,
        ExpID bound_exp_id
    );

    // Monomorphize = replace all poly template refs with mono template refs:
    // todo: WHY NOT expose a different endpoint, so 'eval' is the driver
    //  - upon eval, we automatically monomorphize and substitute references
    //    to monomorphic IDs
    //  - means only traverse AST once.
    void monomorphize_subgraph(MonoModID first_mono_template_id);
    // TODO: replace this^ with 'eval_and_sub'

}
