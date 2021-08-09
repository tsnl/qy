#pragma once

#include "id-arg-list.hh"
#include "id-mtype.hh"
#include "id-mval.hh"

namespace monomorphizer::arg_list {
    
    // ArgListID: unique IDs for actual argument tuples.
    // ID equality <=> tuple equality (val_equals for value IDs, 
    // type_equals for type IDs)
    // Note these are immutable references (cf. functional linked lists) and
    // must be constructed in reverse-order.
    extern ArgListID const EMPTY;

    ArgListID cons_tid(
        ArgListID list,
        mtype::MTypeID type_id
    );
    ArgListID cons_val(
        ArgListID list,
        mval::ValueID value_id
    );

    size_t head(
        ArgListID arg_list_id
    );
    ArgListID tail(
        ArgListID arg_list_id
    );

}