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

import typing as t
from collections import namedtuple

from libc.stdlib cimport malloc, free
from libc.string cimport memcpy

from qcl import frontend
from qcl import ast
from qcl import typer
from qcl import type

cimport qcl.monomorphizer.wrapper as wrapper


cpdef void monomorphize_project(object proj: frontend.project.Project):
    print("--- Monomorphizer ---")

    # ensuring init:
    wrapper.w_ensure_init()

    # sourcing entry point:
    entry_point_source_module: frontend.FileModuleSource = proj.entry_point_source_module
    entry_point_file_mod_exp: ast.node.FileModExp = entry_point_source_module.ast_file_mod_exp_from_frontend

    # Running phase 1:
    # generating PolyModIDs for each sub-mod in this project
    # forward-declaring each module field (i.e., each global symbol)
    forward_declare_proj(proj)

    # Debug:
    print_all_poly_mods(proj)

    # Running phase 2:
    define_declared_def_ids_in_proj(proj)


#
#
# Shared:
#
#

cdef char* mk_c_str_from_py_str(object py_str: str):
    py_str_len = len(py_str)

    p = <char*> malloc(1 + py_str_len)
    for i, c in enumerate(py_str):
        p[i] = <char>ord(c)
    p[py_str_len] = <char>0
    
    return p


cdef void free_c_str_from_py_str(char* s):
    free(s)


#
# PHASE1: Forward declaration pass:
# - creates `DefIDs` and `PolyModIDs`
# - stores in a `def_mfk` map:
#    - key: definition.BaseRecord
#    - val: ModuleFieldKey (MFK)
#

class ModuleFieldKey(object):
    pass


class BuiltinMFK(ModuleFieldKey):
    def __init__(self, def_id):
        super().__init__()
        self.def_id = def_id


class FormalArgMFK(ModuleFieldKey):
    def __init__(self, poly_mod_id, formal_arg_index):
        super().__init__()
        self.poly_mod_id = poly_mod_id
        self.formal_arg_index = formal_arg_index


class FieldMFK(ModuleFieldKey):
    def __init__(self, poly_mod_id, field_index):
        super().__init__()
        self.poly_mod_id = poly_mod_id
        self.field_index = field_index


# Static variables:
def_mfk_map = {}
poly_mod_id_map = {}


cdef wrapper.GDefID get_def_id_from_def_rec(object found_def_rec: typer.definition.BaseRecord):
    opt_mfk = def_mfk_map.get(found_def_rec, None)
    if opt_mfk is None:
        print(f"ERROR: MFK lookup error: def name = {found_def_rec.name}")
        return -1

    mfk = opt_mfk

    if isinstance(mfk, FieldMFK):
        return wrapper.w_get_poly_mod_field_at(mfk.poly_mod_id, mfk.field_index)
    elif isinstance(mfk, FormalArgMFK):
        return wrapper.w_get_poly_mod_formal_arg_at(mfk.poly_mod_id, mfk.formal_arg_index)
    elif isinstance(mfk, BuiltinMFK):
        return mfk.def_id
    else:
        raise NotImplementedError(f"Unknown MFK: type {mfk.__class__.__name__}")


cdef void forward_declare_proj(object proj: frontend.project.Project):
    # declaring each global builtin:
    builtin_def_name_list = [
        "U1", "U8", "U16", "U32", "U64",
        "I8", "I16", "I32", "I64",
        "F32", "F64",
        "Str"
    ]
    for builtin_def_name in builtin_def_name_list:
        def_rec = proj.final_root_ctx.lookup(builtin_def_name)
        if def_rec is None:
            print(f"ERROR: builtin named '{builtin_def_name}' not found")
            return

        if isinstance(def_rec, typer.definition.TypeRecord):
            def_id = wrapper.w_declare_t_const_mast_node(mk_c_str_from_py_str(builtin_def_name))
        elif isinstance(def_rec, typer.definition.ValueRecord):
            def_id = wrapper.w_declare_v_const_mast_node(mk_c_str_from_py_str(builtin_def_name))
        else:
            raise NotImplementedError(f"Unknown def_rec type: {def_rec.__class__.__name__}")

        # mapping:
        mfk = BuiltinMFK(def_id)
        def_mfk_map[def_rec] = mfk

    # forward-declaring each sub-module:
    for file_mod_exp in proj.file_module_exp_list:
        assert isinstance(file_mod_exp, ast.node.FileModExp)
        for sub_mod_name, sub_mod_exp in file_mod_exp.sub_module_map.items():
            print(f"... Generating PolyModID for {sub_mod_name}")

            # copying the sub-mod name into a fresh buffer with a '\0' terminator:
            sub_mod_name_c_str = mk_c_str_from_py_str(sub_mod_name)
            
            # saving the generated poly mod ID to the output map:
            poly_mod_id_map[sub_mod_exp] = gen_poly_mod_id_and_declare_fields(
                sub_mod_name_c_str,
                sub_mod_exp
            )


cdef wrapper.PolyModID gen_poly_mod_id_and_declare_fields(
    char* mv_sub_mod_name,
    object sub_mod_exp: ast.node.SubModExp
):
    # allocating an array for the bound-var DefIDs:
    bv_def_id_count = len(sub_mod_exp.template_arg_names)
    bv_def_id_array = <wrapper.GDefID*> malloc(sizeof(wrapper.GDefID) * bv_def_id_count)

    # unlike the typer before, this time we create BVs for type and value variables.
    bv_def_id_count = len(sub_mod_exp.template_arg_names)
    name_def_obj_pairs_iterable = zip(sub_mod_exp.template_arg_names, sub_mod_exp.template_def_list_from_typer)
    for i, (bv_arg_name, bv_arg_def_obj) in enumerate(name_def_obj_pairs_iterable):
        # TODO: define to get GDefID, then push to mv_bv_def_id_array for w_new_polymorphic_module
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
            wrapper.w_declare_t_const_mast_node(mk_c_str_from_py_str(bind1v_def_obj.name))
        )
        for bind1v_ast_node, bind1v_def_obj in zip(
            sub_mod_exp.table.ordered_value_imp_bind_elems,
            sub_mod_exp.bind1v_def_obj_list_from_typer
        )
    ]
    mast_bind1t_field_index_mapping = [
        wrapper.w_add_poly_module_field(
            new_poly_mod_id,
            wrapper.w_declare_v_const_mast_node(mk_c_str_from_py_str(bind1t_def_obj.name))
        )
        for bind1t_ast_node, bind1t_def_obj in zip(
            sub_mod_exp.table.ordered_type_bind_elems,
            sub_mod_exp.bind1t_def_obj_list_from_typer
        )
    ]

    # saving template formal args' GDefIDs for later in `def_mfk_map`
    for i, bv_arg_def_obj in enumerate(sub_mod_exp.template_def_list_from_typer):
        def_mfk_map[bv_arg_def_obj] = FormalArgMFK(new_poly_mod_id, i)

    # save submodule fields' GDefIDs for later in 'def_mfk_map'
    #   - we must define declared GDefIDs in a subsequent pass
    #   - this pass is tantamount to forward declaration
    for v_def_rec, mod_field_index in zip(
            sub_mod_exp.bind1v_def_obj_list_from_typer,
            mast_bind1v_field_index_mapping
    ):
        def_mfk_map[v_def_rec] = FieldMFK(new_poly_mod_id, mod_field_index)

    for t_def_rec, mod_field_index in zip(
        sub_mod_exp.bind1t_def_obj_list_from_typer,
        mast_bind1t_field_index_mapping
    ):
        def_mfk_map[t_def_rec] = FieldMFK(new_poly_mod_id, mod_field_index)

    # returning the completed module:
    return new_poly_mod_id

#
# PHASE2
# Definitions for declared definitions, 
# generating MAST from AST
#

cdef wrapper.TypeSpecID ast_to_mast_ts(object t: ast.node.BaseTypeSpec):
    # Unit:
    if isinstance(t, ast.node.UnitTypeSpec):
        return wrapper.w_get_unit_ts()

    # IDs:
    elif isinstance(t, ast.node.IdTypeSpec):
        # DONE: finalize how IDs work in extension
        #   - need to separate global IDs from local IDs
        #   - need to store MAST module+index on each global def-rec
        #   - need to get extension-interned ID for local variable name
        # DONE: store container sub-module for all definitions.
        #   - guaranteed to be non-None
        #   - allows us to look up a cache to see if the module has been
        #     monomorphized yet
        # DONE
        #   - first, determine if this definition is global or not
        #   - accordingly, create an LID or GID TS node
        #   - for GID nodes, can look up exact GDefID (cf pre-pass above)
        #       - def object now has container sub-module
        #       - thus, we can lazily generate GID mappings
        #       - and finally collect them together to define each module
        #   - for LID nodes, straightforward interning of definition name

        id_ts = t
        found_def_rec = id_ts.found_def_rec
        is_local = found_def_rec.opt_container_func is not None

        if is_local:
            # return an LID:
            s = mk_c_str_from_py_str(id_ts.name)
            int_str_id = wrapper.w_intern_string_2(s)
            free_c_str_from_py_str(s)
            return wrapper.w_new_lid_ts(int_str_id)
        else:
            # return a GID:
            return get_def_id_from_def_rec(found_def_rec)

    else:
        raise NotImplementedError(f"ast_to_mast_ts for t={t} of kind {t.__class__.__name__}")


cdef wrapper.ExpID ast_to_mast_exp(object e: ast.node.BaseExp):
    if isinstance(e, ast.node.UnitExp):
        return wrapper.w_get_unit_exp()
    elif isinstance(e, ast.node.NumberExp):
        # ExpID w_new_int_exp(size_t mantissa, IntegerSuffix int_suffix, bint is_neg)
        # ExpID w_new_float_exp(double value, FloatSuffix float_suffix)
        width_in_bits = type.scalar_width_in_bits.of(e.x_tid)
        if e.is_float:
            if width_in_bits == 64:
                float_suffix = wrapper.FloatSuffix.F64
            else:
                # default to F32 for static computation unless higher precision is explicitly demanded
                float_suffix = wrapper.FloatSuffix.F32
            value = float(e.text)
            return wrapper.w_new_float_exp(value, float_suffix)

        elif e.is_unsigned_int:
            if width_in_bits == 64:
                int_suffix = wrapper.IntegerSuffix.U64
            elif width_in_bits == 32:
                int_suffix = wrapper.IntegerSuffix.U32
            elif width_in_bits == 16:
                int_suffix = wrapper.IntegerSuffix.U16
            elif width_in_bits == 8:
                int_suffix = wrapper.IntegerSuffix.U8
            elif width_in_bits == 1:
                int_suffix = wrapper.IntegerSuffix.U1
            else:
                raise NotImplementedError("Unknown UInt size")
            mantissa: size_t = int(e.text)
            return wrapper.w_new_int_exp(mantissa, int_suffix, 0)

        elif e.is_signed_int:
            if width_in_bits == 64:
                int_suffix = wrapper.IntegerSuffix.S64
            elif width_in_bits == 32:
                int_suffix = wrapper.IntegerSuffix.S32
            elif width_in_bits == 16:
                int_suffix = wrapper.IntegerSuffix.S16
            elif width_in_bits == 8:
                int_suffix = wrapper.IntegerSuffix.S8
            else:
                raise NotImplementedError("Unknown SInt size")

            mantissa = int(e.text)
            return wrapper.w_new_int_exp(mantissa, int_suffix, 0)

    raise NotImplementedError(f"ast_to_mast_exp for e={e}")


cdef wrapper.ElemID ast_to_mast_elem(object e: ast.node.BaseElem):
    raise NotImplementedError(f"ast_to_mast_elem for e={e}")


cdef void define_declared_def_ids_in_proj(object proj: frontend.project.Project):
    for file_mod_exp in proj.file_module_exp_list:
        for sub_mod_name, sub_mod_exp in file_mod_exp.sub_module_map.items():
            define_declared_def_ids_in_sub_mod(sub_mod_name, sub_mod_exp)


cdef define_declared_def_ids_in_sub_mod(object sub_mod_name: str, object sub_mod_exp: ast.node.SubModExp):
    # NOTE: templates (BvDefs) are already defined.
    # for bv_def_obj in sub_mod_exp.template_def_list_from_typer:
    #
    #     void w_define_declared_t_const(GDefID declared_def_id, TypeSpecID ts_id)
    #     void w_define_declared_v_const(GDefID declared_def_id, ExpID exp_id)

    # defining value bind elems in sub-modules:
    for bind1v_def_obj, bind1v_elem in zip(
            sub_mod_exp.bind1v_def_obj_list_from_typer,
            sub_mod_exp.table.ordered_value_imp_bind_elems
    ):
        wrapper.w_define_declared_v_const(
            get_def_id_from_def_rec(bind1v_def_obj),
            ast_to_mast_exp(bind1v_elem.bound_exp)
        )

    for bind1t_def_obj, bind1t_elem in zip(
            sub_mod_exp.bind1t_def_obj_list_from_typer,
            sub_mod_exp.table.ordered_type_bind_elems
    ):
        wrapper.w_define_declared_t_const(
            get_def_id_from_def_rec(bind1t_def_obj),
            ast_to_mast_ts(bind1t_elem.bound_type_spec)
        )


#
# Debug:
#

cdef void print_all_poly_mods(object proj: frontend.Project):
    # DEBUG: printing the generated PolyModID:
    print("... BEG of generated PolyModID Dump: ...")
    for file_mod_exp in proj.file_module_exp_list:
        assert isinstance(file_mod_exp, ast.node.FileModExp)
        for sub_mod_name, sub_mod_exp in file_mod_exp.sub_module_map.items():
            wrapper.w_print_poly_mod(poly_mod_id_map[sub_mod_exp])
    print("... END of generated PolyModID dump ...")
