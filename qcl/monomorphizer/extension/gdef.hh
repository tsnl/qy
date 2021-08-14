// All definitions are globally managed, and un-scoped.

#pragma once

#include <cstddef>

#include "id-gdef.hh"
#include "id-mast.hh"
#include "id-mval.hh"
#include "id-mtype.hh"

namespace monomorphizer::gdef {

    extern GDefID const NULL_GDEF_ID;

    enum DefKind {
        BV_EXP,
        BV_TS,
        CONST_EXP,
        CONST_TS,
        CONST_TOT_VAL,
        CONST_TOT_TID
    };

    void ensure_defs_init();
    void drop_defs();

    //
    // Definitions:
    //

    // constant definitions:
    GDefID declare_t_const_mast_node(char* mv_def_name);
    GDefID declare_v_const_mast_node(char* mv_def_name);
    
    // defining total constants: exclusively for MonoModID fields
    GDefID define_total_const_value(char* mv_def_name, mval::ValueID value_id);
    GDefID define_total_const_type(char* mv_def_name, mtype::TID type_id);

    // lazily binding const-mast-node defs to a MAST node:
    // doing this separately allows forward declarations in MAST.
    void define_declared_t_const(GDefID declared_def_id, mast::TypeSpecID ts_id);
    void define_declared_v_const(GDefID declared_def_id, mast::ExpID exp_id);

    // bound var definitions:
    // monomorphization is just replacing references to these in polymorphic 
    // modules with total const definitions, returning a monomorphic copy.
    GDefID define_bound_var_ts(char* mv_formal_var_name);
    GDefID define_bound_var_exp(char* mv_formal_var_name);

    // query definition info:
    bool get_def_is_bv(GDefID def_id);
    DefKind get_def_kind(GDefID def_id);
    char const* get_def_name(GDefID def_id);
    void store_id_at_def_id(GDefID def_id, size_t id);
    size_t load_id_from_def_id(GDefID def_id);

}
