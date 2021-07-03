#pragma once

#include "core.h"
#include "table.h"
#include "consts.h"

typedef struct Func Func;
typedef struct TemplateValArg TemplateValArg;
typedef struct TemplateTypeArg TemplateTypeArg;

struct Func {
    DefID opt_def_id;
    ExprID body_expr_id;

    size_t template_val_arg_count;
    TemplateValArg* template_val_args;
    size_t template_type_arg_count;
    TemplateTypeArg* template_type_args;

    RtTypeID fn_tid;
};

struct TemplateValArg {
    DefID arg_name;
    TABLE(Const)* passed_consts;
};

struct TemplateTypeArg {
    DefID arg_name;
    TABLE(RtTypeID)* passed_rttids;
};

// todo: allow declare to accept template arguments.
// todo: figure out closures
