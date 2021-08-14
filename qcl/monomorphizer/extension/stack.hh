#pragma once

// todo: implement a 'stack' that can track [IntStr -> ValueID/MTypeID]
//  - each Frame maps IntStr IDs to a mval::ValueID or mtype::MTypeID
//  - each Stack instance can be used to evaluate a total expression
//  - appropriate errors need to be generated if a symbol is not defined
// definitions only occur from `bind1X` elements in ChainExps.
//  - this includes evaluations in the global scope

#include "id-intern.hh"
#include "id-mtype.hh"
#include "id-mval.hh"

namespace monomorphizer::stack {

    struct Stack;

    Stack* create_stack();
    void destroy_stack(Stack* stack);

    void push_stack_frame(Stack* stack);
    void pop_stack_frame(Stack* stack);

    void def_t_in_stack(Stack* stack, intern::IntStr int_str_id, mtype::TID tid);
    void def_v_in_stack(Stack* stack, intern::IntStr int_str_id, mval::ValueID vid);

    mval::ValueID lookup_v_in_stack(Stack* stack, intern::IntStr int_str_id);
    mtype::TID lookup_t_in_stack(Stack* stack, intern::IntStr int_str_id);

}