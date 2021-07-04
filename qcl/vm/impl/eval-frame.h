#pragma once

#include "core.h"
#include "consts.h"

typedef struct EvalFrame EvalFrame;

EvalFrame* ef_new(EvalFrame* parent_ef, size_t sym_count, DefID* mv_sym_names);
void ef_del(EvalFrame* ef);

void ef_init_symbol(DefID sym_name, Const constant);
Const const* ef_try_lookup_symbol(DefID sym_name);
