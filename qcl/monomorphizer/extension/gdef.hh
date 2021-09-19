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

    GDefID declare_global_def(DefKind def_kind, char* mv_bound_name);
    void set_def_target(GDefID def_id, size_t target_id);

    // query definition info:
    bool get_def_is_bv(GDefID def_id);
    DefKind get_def_kind(GDefID def_id);
    char const* get_def_name(GDefID def_id);
    size_t get_def_target(GDefID def_id);

}
