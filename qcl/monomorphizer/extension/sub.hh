// This module allows the user to create `Substitution` objects that 
// map GDefIDs to GDefIDs


#pragma once

#include <cstddef>

#include "id-gdef.hh"
#include "id-mval.hh"
#include "id-mtype.hh"
#include "id-mast.hh"

namespace monomorphizer::sub {

    class Substitution;

    Substitution* create();
    void destroy(Substitution* s);

    void add_monomorphizing_replacement(
        Substitution* s, 
        GDefID original_def_id, GDefID replacement_def_id
    );
    GDefID rw_def_id(
        Substitution* s, 
        GDefID def_id
    );

}
