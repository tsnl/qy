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
from qcl import typer

cimport qcl.monomorphizer.wrapper as wrapper


cpdef void monomorphize_project(object proj: frontend.project.Project):
    print("--- Monomorphizer ---")

    # sourcing entry point:
    entry_point_source_module: frontend.FileModuleSource = proj.entry_point_source_module
    entry_point_file_mod_exp: ast.node.FileModExp = entry_point_source_module.ast_file_mod_exp_from_frontend

    # generating PolyModIDs for each sub-mod in this project
    # forward-declaring each module field (i.e., each global symbol)
    poly_mod_id_map = {}
    for file_mod_exp in proj.file_module_exp_list:
        assert isinstance(file_mod_exp, ast.node.FileModExp)
        for sub_mod_name, sub_mod_exp in file_mod_exp.sub_module_map.items():
            print(f"... Generating PolyModID for {sub_mod_name}")

            # copying the sub-mod name into a fresh buffer with a '\0' terminator:
            sub_mod_name_c_str = mk_c_str_from_py_str(sub_mod_name)
            
            # saving the generated poly mod ID to the output map:
            poly_mod_id = gen_poly_mod_id_and_declare_fields(
                sub_mod_name_c_str,
                sub_mod_exp
            )


cdef wrapper.PolyModID gen_poly_mod_id_and_declare_fields(
    char* mv_sub_mod_name,
    object sub_mod_exp: ast.node.SubModExp
):
    # TODO: use these two functions to construct a PolyModID
    # PolyModID w_new_polymorphic_module(char* mv_template_name, size_t bv_def_id_count, DefID* mv_bv_def_id_array);
    # size_t w_add_poly_module_field(PolyModID template_id, DefID field_def_id);

    bv_def_id_count = len(sub_mod_exp.template_arg_names)
    bv_def_id_array = <wrapper.DefID*> malloc(sizeof(wrapper.DefID) * bv_def_id_count)

    # unlike the typer before, this time we create BVs for type and value variables.
    bv_def_id_count = len(sub_mod_exp.template_arg_names)
    name_def_obj_pairs_iterable = zip(sub_mod_exp.template_arg_names, sub_mod_exp.template_def_list_from_typer)
    for i, (bv_arg_name, bv_arg_def_obj) in enumerate(name_def_obj_pairs_iterable):
        # TODO: define to get DefID, then push to mv_bv_def_id_array for w_new_polymorphic_module
        bv_arg_name_c_str = mk_c_str_from_py_str(bv_arg_name)
        if isinstance(bv_arg_def_obj, typer.definition.ValueRecord):
            def_id = wrapper.w_define_bound_var_exp(bv_arg_name_c_str)
        elif isinstance(bv_arg_def_obj, typer.definition.TypeRecord):
            def_id = wrapper.w_define_bound_var_ts(bv_arg_name_c_str)
        else:
            raise NotImplementedError("Unknown BV arg def-record type")
        
        bv_def_id_array[i] = def_id

    # constructing the module using BVs:
    new_poly_mod_id = wrapper.w_new_polymorphic_module(
        mv_sub_mod_name,
        bv_def_id_count,
        bv_def_id_array
    )

    # declaring fields for this module given bind1v and bind1t lists
    # (in this order)
    mast_bind1v_field_index_mapping = [
        wrapper.w_add_poly_module_field(
            new_poly_mod_id,
            wrapper.w_declare_t_const_mast_node(
                mk_c_str_from_py_str(bind1v_def_obj.name)
            )
        )
        for bind1v_ast_node, bind1v_def_obj in zip(
            sub_mod_exp.table.ordered_value_imp_bind_elems,
            sub_mod_exp.bind1v_def_obj_list_from_typer
        )
    ]
    mast_bind1t_field_index_mapping = [
        wrapper.w_add_poly_module_field(
            new_poly_mod_id,
            wrapper.w_declare_v_const_mast_node(
                mk_c_str_from_py_str(bind1t_def_obj.name)
            )
        )
        for bind1t_ast_node, bind1t_def_obj in zip(
            sub_mod_exp.table.ordered_type_bind_elems,
            sub_mod_exp.bind1t_def_obj_list_from_typer
        )
    ]

    # TODO: save these maps for later
    #   - we must define declared DefIDs in a subsequent pass
    #   - this pass is tantamount to forward declaration
    zip(
        sub_mod_exp.bind1v_def_obj_list_from_typer,
        mast_bind1v_field_index_mapping
    )
    zip(
        sub_mod_exp.bind1t_def_obj_list_from_typer,
        mast_bind1t_field_index_mapping
    )

    # DEBUG: printing the generated PolyModID:
    print("... BEG of generated PolyModID Dump: ---")
    wrapper.w_print_poly_mod(new_poly_mod_id)
    print("... END of generated PolyModID dump")

    # returning the completed module:
    return new_poly_mod_id


cdef wrapper.TypeSpecID ast_to_mast_ts(object t: ast.node.BaseTypeSpec):
    if isinstance(t, ast.node.UnitTypeSpec):
        return wrapper.w_get_unit_ts()
    elif isinstance(t, ast.node.IdTypeSpec):
        # DONE: finalize how IDs work in extension
        #   - need to separate global IDs from local IDs
        #   - need to store MAST module+index on each global def-rec
        #   - need to get extension-interned ID for local variable name
        # DONE: store container sub-module for all definitions.
        #   - guaranteed to be non-None
        #   - allows us to look up a cache to see if the module has been
        #     monomorphized yet
        # NOW:
        #   - first, determine if this definition is global or not
        #   - accordingly, create an LID or GID TS node
        #   - for GID nodes, can look up exact DefID (cf pre-pass above)
        #       - def object now has container sub-module
        #       - thus, we can lazily generate GID mappings
        #       - and finally collect them together to define each module
        #   - for LID nodes, straightforward interning of definition name
        raise NotImplementedError("Mapping IDs in MAST")
    else:
        raise NotImplementedError(f"ast_to_mast_ts for t={t} of kind {t.__class__.__name__}")


cdef wrapper.ExpID ast_to_mast_exp(object e: ast.node.BaseExp):
    raise NotImplementedError(f"ast_to_mast_exp for e={e}")


cdef wrapper.ElemID ast_to_mast_elem(object e: ast.node.BaseElem):
    raise NotImplementedError(f"ast_to_mast_elem for e={e}")


cdef char* mk_c_str_from_py_str(object py_str: str):
    py_str_len = len(py_str)

    p = <char*> malloc(1 + py_str_len)
    for i, c in enumerate(py_str):
        p[i] = <char>ord(c)
    p[py_str_len] = <char>0
    
    return p
