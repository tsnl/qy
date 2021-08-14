#pragma once

#include "core.h"
#include "table.h"
#include "consts.h"
#include "rtti.h"

typedef struct Func Func;
typedef struct FormalTemplateValArg FormalTemplateValArg;
typedef struct FormalTemplateTypeArg FormalTemplateTypeArg;
typedef struct Instantiation Instantiation;

struct Func {
    GDefID opt_def_id;
    ExprID base_body_expr_id;

    // template info:
    struct {
        size_t formal_template_val_arg_count;
        FormalTemplateValArg* formal_template_val_args;

        size_t formal_template_type_arg_count;
        FormalTemplateTypeArg* formal_template_type_args;

        RtTypeID fn_tid;

        TABLE(Instantiation)* instantiations;
    } templated;

    // nonlocal info:
    struct {
        RtTypeID non_local_struct_rttid;
    } non_local;
};

struct FormalTemplateValArg {
    GDefID arg_name;
};

struct FormalTemplateTypeArg {
    GDefID arg_name;
    RtTypeID arg_rttid;
};

struct Instantiation {
    Const* passed_const_array;
    RtTypeID* passed_rttids;
    ExprID subbed_body;
};
