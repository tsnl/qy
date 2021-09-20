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
    extern ArgListID const EMPTY_ARG_LIST;

    ArgListID cons_tid(
        ArgListID list,
        mtype::TID type_id
    );
    ArgListID cons_val(
        ArgListID list,
        mval::VID value_id
    );

    size_t head(
        ArgListID arg_list_id
    );
    ArgListID tail(
        ArgListID arg_list_id
    );
    inline size_t arg_list_head_compatibility(ArgListID arg_list_id) { return head(arg_list_id); }
    inline ArgListID arg_list_tail_compatibility(ArgListID arg_list_id) { return tail(arg_list_id); }

    ArgListID empty_arg_list_id();
    size_t count_arg_list_items(ArgListID arg_list_id);

    void print_arg_list(ArgListID arg_list_id);

}