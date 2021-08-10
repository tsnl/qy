// This module allows the user to create `Substitution` objects that 
// map DefIDs to DefIDs


#pragma once

#include <cstddef>

#include "id-defs.hh"
#include "id-mval.hh"
#include "id-mtype.hh"
#include "id-mast.hh"

namespace monomorphizer::sub {

    class Substitution;

    Substitution* create();
    void destroy(Substitution* s);

    void add_monomorphizing_replacement(
        Substitution* s, 
        DefID original_def_id, DefID replacement_def_id
    );
    DefID rw_def_id(
        Substitution* s, 
        DefID def_id
    );

}
