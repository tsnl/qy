// All definitions are globally managed, and un-scoped.

#pragma once

#include <cstddef>

#include "id-defs.hh"
#include "id-mast.hh"

namespace monomorphizer::defs {

    extern DefID const NULL_DEF_ID;

    enum DefKind {
        BV_EXP,
        BV_TS,
        CONST_EXP,
        CONST_TS
    };

    void ensure_init();
    void drop();

    //
    // Definitions:
    //

    // constant definitions: 
    DefID define_const(
        char const* mod_name,
        char const* def_name,
        NodeID bound_node_id,
        bool is_global
    );

    // bound var definitions:
    // - monomorphization is just subbing these with `const-def`s in a new copy
    DefID define_bound_var_ts(
        char const* mod_name,
        char const* formal_var_name
    );
    DefID define_bound_var_exp(
        char const* mod_name,
        char const* formal_var_name
    );

    // query definition info:
    bool get_def_is_bv(DefID def_id);
    DefKind get_def_kind(DefID def_id);

}