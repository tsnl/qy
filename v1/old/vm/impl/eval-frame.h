#pragma once

#include "core.h"
#include "consts.h"

typedef struct EvalFrame EvalFrame;

EvalFrame* ef_new(EvalFrame* parent_ef, int sym_count, GDefID* mv_sym_names);
void ef_del(EvalFrame* ef);

void ef_init_symbol(EvalFrame* ef, GDefID sym_name, Const constant);
Const const* ef_try_lookup_symbol(EvalFrame* ef, GDefID sym_name);
