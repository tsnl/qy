"""
This module copies `qcl.ast.node.*` instances into `qcl.monomorphizer.mast`, then evaluates a critical part of it.
We pretend polymorphic definitions accept monomorphic definitions with IDs that can be substituted upon rewrite.
This rewriting while substituting out formal args for actual ones is called monomorphization.
Since substituting value formal args requires knowing the value of each actual argument, monomorphization requires and
provides constant evaluation. The two are intertwined.

EXTENSION INPUT SPEC
Initially, we assume that every module is polymorphic.
If a module is monomorphic, it is encoded as polymorphic with 0 args.
Instantiating the entry point PolyMod produces a MonoMod, and only generates the minimal set of MonoMods referenced by
the returned MonoMod.
Furthermore, the extension only allows evaluated values (total constants) to be stored in MonoMod fields.
Thus, we also obtain the value of each field.
"""

from libc.stdlib cimport malloc
from libc.string cimport memcpy

from qcl import frontend
from qcl import ast

cimport qcl.monomorphizer.wrapper as wrapper


cpdef void monomorphize_project(object proj: frontend.project.Project):
    print("--- Monomorphizer ---")

    # sourcing entry point:
    entry_point_source_module: frontend.FileModuleSource = proj.entry_point_source_module
    entry_point_file_mod_exp: ast.node.FileModExp = entry_point_source_module.ast_file_mod_exp_from_frontend

    # generating PolyModIDs for each sub-mod in this project
    poly_mod_id_map = {}
    for file_mod_exp in proj.file_module_exp_list:
        assert isinstance(file_mod_exp, ast.node.FileModExp)
        for sub_mod_name, sub_mod_exp in file_mod_exp.sub_module_map.items():
            print(f"... Generating PolyModID for {sub_mod_name}")

            # copying the sub-mod name into a fresh buffer with a '\0' terminator:
            sub_mod_name_len = len(sub_mod_name)
            mv_sub_mod_name_bytes = <char*> malloc(1 + sub_mod_name_len)
            for i, c in enumerate(sub_mod_name):
                mv_sub_mod_name_bytes[i] = ord(c)
            mv_sub_mod_name_bytes[sub_mod_name_len] = 0

            poly_mod_id_map[sub_mod_exp] = gen_poly_mod_id(
                sub_mod_name_len,
                mv_sub_mod_name_bytes,
                sub_mod_exp
            )


cdef wrapper.PolyModID gen_poly_mod_id(
        size_t template_name_len,
        char* mv_template_name_bytes,
        object sub_mod_exp: ast.node.SubModExp
):
    # TODO: use these two functions to construct a PolyModID
    # PolyModID w_new_polymorphic_module(char* mv_template_name, size_t bv_def_id_count, DefID* mv_bv_def_id_array);
    # size_t w_add_poly_module_field(PolyModID template_id, DefID field_def_id);

    bv_def_id_count = len(sub_mod_exp.template_arg_names)
    bv_def_id_array = malloc(sizeof(wrapper.DefID) * bv_def_id_count)

    name_def_obj_pairs_iterable = zip(sub_mod_exp.template_arg_names, sub_mod_exp.template_def_list_from_typer)
    for i, (bv_arg_name, bv_arg_def_obj) in enumerate(name_def_obj_pairs_iterable):
        print(f"Defining BV {bv_arg_name} with def-obj {bv_arg_def_obj}")
        # TODO: define to get DefID, then push to mv_bv_def_id_array for w_new_polymorphic_module

    # TODO: define fields for this module given bind1v and bind1t lists

    # new_id = wrapper.w_new_polymorphic_module(sub)