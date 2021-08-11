// All definitions are globally managed, and un-scoped.

#pragma once

#include <cstddef>

#include "id-defs.hh"
#include "id-mast.hh"
#include "id-mval.hh"
#include "id-mtype.hh"

namespace monomorphizer::defs {

    extern DefID const NULL_DEF_ID;

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
    DefID define_const_mast_node(
        char* mv_def_name,
        mast::NodeID bound_node_id,
        bool is_global
    );
    DefID define_total_const_value(
        char* mv_def_name,
        mval::ValueID value_id,
        bool is_global
    );
    DefID define_total_const_type(
        char* mv_def_name,
        mtype::TID type_id,
        bool is_global
    );

    // bound var definitions:
    // monomorphization is just replacing references to these in polymorphic 
    // modules with total const definitions, returning a monomorphic copy.
    DefID define_bound_var_ts(
        char* mv_formal_var_name
    );
    DefID define_bound_var_exp(
        char* mv_formal_var_name
    );

    // query definition info:
    bool get_def_is_bv(DefID def_id);
    DefKind get_def_kind(DefID def_id);
    char const* get_mod_name(DefID def_id);
    char const* get_def_name(DefID def_id);
    void store_id_at_def_id(DefID def_id, size_t id);
    size_t load_id_from_def_id(DefID def_id);

}
