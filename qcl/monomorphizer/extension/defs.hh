// All definitions are globally managed, and un-scoped.

#pragma once

#include <cstddef>

#include "id-defs.hh"
#include "id-mast.hh"

namespace defs {

    enum DefKind {
        BV_EXP,
        BV_TS,
        CONST_EXP,
        CONST_TS
    };

    void init(size_t init_def_capacity);

    //
    // Definitions:
    //

    DefID define_const_exp(
        char const* mod_name,
        char const* def_name,
        NodeID node_id,
        bool is_global
    );
    DefID define_const_ts(
        char const* mod_name,
        char const* def_name,
        NodeID node_id,
        bool is_global
    );
    DefID define_bound_var(
        char const* mod_name,
        char const* formal_var_name,
        bool is_exp_not_ts
    );

    DefKind get_def_kind(DefID def_id);

    // TODO: cache substitutions for bound vars (for use in `eval.cc`)
}