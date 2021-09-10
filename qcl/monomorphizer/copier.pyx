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

PHASES
This pass is broken into multiple phases:
- P1: declarations: generating forward declarations for all global variables in polymorphic extension-space
- P2: definitions: binding initial AST values for all global variables in polymorphic extension-space
- P3: monomorphization: simply instantiate the entry-point module, 
"""

import sys
import time
import typing as t
from collections import namedtuple

from libc.stdlib cimport malloc, free
from libc.string cimport memcpy
from libc.stdint cimport uint32_t

from qcl import excepts
from qcl import frontend
from qcl import ast
from qcl import typer
from qcl import type

cimport qcl.monomorphizer.wrapper as wrapper

PySES = type.side_effects.SES
PyUnaryOp = ast.node.UnaryOp
PyBinaryOp = ast.node.BinaryOp


cpdef void monomorphize_project(object proj: frontend.project.Project):
    print("--- BEG Monomorphizer ---")

    # ensuring init:
    wrapper.w_ensure_init()

    # Running phase 1:
    # generating PolyModIDs for each sub-mod in this project
    # forward-declaring each module field (i.e., each global symbol)
    forward_declare_proj(proj)

    # Running phase 2:
    define_declared_def_ids_in_proj(proj)

    # Debug print 1:
    # print()
    # print_all_poly_mods("POST-P2", proj)
    # print()

    # Running phase 3:
    instantiate_entry_point(proj)

    # TODO: dump the extension state, write ways to access it.

    # Debug print 2: printing the extension state to export + debug state (PolyMods)
    print()
    print_all_poly_mods("FINALLY", proj)
    print()
    print_all_mono_mods("FINALLY", proj)
    print()
    
    print("--- END Monomorphizer: OK ---")


#
#
# Shared among all phases:
#
#

cdef void panic(object msg: str):
    flush_wait_time_in_sec = 0.05           # 50ms should be plenty
    time.sleep(flush_wait_time_in_sec)      # allow stdout to flush everything printed so far
    
    print(f"FATAL_ERROR: {msg}", flush=True, file=sys.stderr)
    
    time.sleep(flush_wait_time_in_sec)      # allow stderr to flush this message
    exit(-1)                                # exit


cdef extern from "extension/gdef.hh" namespace "monomorphizer::gdef":
    extern const wrapper.GDefID NULL_GDEF_ID;


cdef char* mk_c_str_from_py_str(object py_str: str):
    py_str_len = len(py_str)

    p = <char*> malloc(1 + py_str_len)
    for i, c in enumerate(py_str):
        p[i] = <char>ord(c)
    p[py_str_len] = <char>0
    
    return p


cdef wrapper.IntStr mk_int_str_from_py_str(object py_str: str, bint is_tid_not_vid):
    c_str = mk_c_str_from_py_str(py_str)
    int_str_id = wrapper.w_intern_string_2(c_str, is_tid_not_vid)
    free(c_str)
    return int_str_id


cdef void free_c_str_from_py_str(char* s):
    free(s)


#
# PHASE1: Forward declaration pass:
# - creates `DefIDs` and `PolyModIDs`
# - stores in a `gdef_map`:
#    - key: definition.BaseRecord
#    - val: GDefID
#

# Static variables:
def_to_gdef_map = {}
poly_mod_id_map = {}


cdef wrapper.GDefID get_def_id_from_def_rec(object found_def_rec: typer.definition.BaseRecord):
    found_gdef_id = def_to_gdef_map.get(found_def_rec, None)
    if found_gdef_id is None:
        print(f"ERROR: MFK lookup error: def name = {found_def_rec.name}")
        return -1
    else:
        return found_gdef_id


cdef void forward_declare_proj(object proj: frontend.project.Project):
    # defining each global builtin:
    builtin_def_name_list = {
        "U1": wrapper.w_get_u1_tid(), 
        "U8": wrapper.w_get_u8_tid(), 
        "U16": wrapper.w_get_u16_tid(), 
        "U32": wrapper.w_get_u32_tid(), 
        "U64": wrapper.w_get_u64_tid(),

        "I8": wrapper.w_get_s8_tid(), 
        "I16": wrapper.w_get_s16_tid(), 
        "I32": wrapper.w_get_s32_tid(), 
        "I64": wrapper.w_get_s64_tid(),
        "F32": wrapper.w_get_f32_tid(), 
        "F64": wrapper.w_get_f64_tid(),

        "Str": wrapper.w_get_string_tid()
    }
    for builtin_def_name, builtin_def_target in builtin_def_name_list.items():
        def_rec = proj.final_root_ctx.lookup(builtin_def_name)
        if def_rec is None:
            print(f"ERROR: builtin named '{builtin_def_name}' not found")
            return

        # declaring:
        if isinstance(def_rec, typer.definition.TypeRecord):
            def_id = wrapper.w_declare_global_def(
                wrapper.CONST_TOT_TID,
                mk_c_str_from_py_str(builtin_def_name)
            )
        elif isinstance(def_rec, typer.definition.ValueRecord):
            def_id = wrapper.w_declare_global_def(
                wrapper.CONST_TOT_VAL,
                mk_c_str_from_py_str(builtin_def_name)
            )
        else:
            raise NotImplementedError(f"Unknown def_rec type: {def_rec.__class__.__name__}")

        # defining:
        wrapper.w_set_def_target(def_id, builtin_def_target)

        # mapping:
        def_to_gdef_map[def_rec] = def_id

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
    cp_bv_def_id_list = []
    for i, (bv_arg_name, bv_arg_def_obj) in enumerate(name_def_obj_pairs_iterable):
        # TODO: define to get GDefID, then push to mv_bv_def_id_array for w_new_polymorphic_module
        bv_arg_name_c_str = mk_c_str_from_py_str(bv_arg_name)
        if isinstance(bv_arg_def_obj, typer.definition.ValueRecord):
            def_id = wrapper.w_declare_global_def(wrapper.BV_EXP, bv_arg_name_c_str)
        elif isinstance(bv_arg_def_obj, typer.definition.TypeRecord):
            def_id = wrapper.w_declare_global_def(wrapper.BV_TS, bv_arg_name_c_str)
        else:
            raise NotImplementedError("Unknown BV arg def-record type")
        
        bv_def_id_array[i] = def_id
        cp_bv_def_id_list.append(def_id)

    # constructing the module using BVs:
    new_poly_mod_id = wrapper.w_new_polymorphic_module(
        mv_sub_mod_name,
        bv_def_id_count,
        bv_def_id_array
    )

    # declaring fields for this module given bind1v and bind1t lists
    # (in this order)
    sub_mod_exp.mast_bind1v_field_index_mapping_from_monomorphizer = [
        wrapper.w_add_poly_module_field(
            new_poly_mod_id,
            wrapper.w_declare_global_def(wrapper.CONST_EXP, mk_c_str_from_py_str(bind1v_def_obj.name))
        )
        for bind1v_ast_node, bind1v_def_obj in zip(
            sub_mod_exp.table.ordered_value_imp_bind_elems,
            sub_mod_exp.bind1v_def_obj_list_from_typer
        )
    ]
    sub_mod_exp.mast_bind1t_field_index_mapping_from_monomorphizer = [
        wrapper.w_add_poly_module_field(
            new_poly_mod_id,
            wrapper.w_declare_global_def(wrapper.CONST_TS, mk_c_str_from_py_str(bind1t_def_obj.name))
        )
        for bind1t_ast_node, bind1t_def_obj in zip(
            sub_mod_exp.table.ordered_type_bind_elems,
            sub_mod_exp.bind1t_def_obj_list_from_typer
        )
    ]

    # saving template formal args' GDefIDs for later in `gdef_map`
    for i, bv_arg_def_obj in enumerate(sub_mod_exp.template_def_list_from_typer):
        bv_def_id = bv_def_id_array[i]
        def_to_gdef_map[bv_arg_def_obj] = bv_def_id

    # save submodule fields' GDefIDs for later in 'gdef_map'
    #   - we must define declared GDefIDs in a subsequent pass
    #   - this pass is tantamount to forward declaration
    for v_def_rec, mod_field_index in zip(
            sub_mod_exp.bind1v_def_obj_list_from_typer,
            sub_mod_exp.mast_bind1v_field_index_mapping_from_monomorphizer
    ):
        def_to_gdef_map[v_def_rec] = wrapper.w_get_poly_mod_field_at(new_poly_mod_id, mod_field_index)

    for t_def_rec, mod_field_index in zip(
        sub_mod_exp.bind1t_def_obj_list_from_typer,
        sub_mod_exp.mast_bind1t_field_index_mapping_from_monomorphizer
    ):
        def_to_gdef_map[t_def_rec] = wrapper.w_get_poly_mod_field_at(new_poly_mod_id, mod_field_index)

    # returning the completed module:
    return new_poly_mod_id


#
# PHASE2
# Definitions for declared definitions, 
# generating MAST from AST
#

cdef wrapper.TypeSpecID ast_to_mast_ts(object ts: ast.node.BaseTypeSpec):
    # Unit:
    if isinstance(ts, ast.node.UnitTypeSpec):
        return wrapper.w_get_unit_ts()

    # IDs -> LIDs, GIDs:
    elif isinstance(ts, ast.node.IdTypeSpec):
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

        id_ts = ts
        found_def_rec = id_ts.found_def_rec

        if not id_ts.found_def_rec.is_bound_globally_visible:
            # return an LID:
            s = mk_c_str_from_py_str(id_ts.name)
            int_str_id = wrapper.w_intern_string_2(s, 1)
            free_c_str_from_py_str(s)
            return wrapper.w_new_lid_ts(int_str_id)
        else:
            # return a GID:
            def_id = get_def_id_from_def_rec(found_def_rec)
            return wrapper.w_new_gid_ts(def_id)

    # IdTypeSpecInModule
    elif isinstance(ts, ast.node.IdTypeSpecInModule):
        assert len(ts.data.elem_args) == 0
        assert ts.data.opt_container is not None

        found_sub_mod_exp = ts.data.opt_container.found_def_rec.mod_exp
        assert isinstance(found_sub_mod_exp, ast.node.SubModExp)

        poly_mod_id = poly_mod_id_map[found_sub_mod_exp]

        original_bind1t_index = None
        for i, d in enumerate(found_sub_mod_exp.bind1t_def_obj_list_from_typer):
            if d.name == ts.data.elem_name:
                original_bind1t_index = i
                break
        else:
            for template_arg_index, template_arg_name in enumerate(found_sub_mod_exp.template_arg_names):
                if ts.data.elem_name == template_arg_name:
                    panic("NotImplemented: finding an index for template args")
            else:
                panic("Could not find def object for field, though typing ok.")

        mast_field_index_map = found_sub_mod_exp.mast_bind1t_field_index_mapping_from_monomorphizer
        ts_field_ix = <size_t> mast_field_index_map[original_bind1t_index]

        actual_arg_count = len(ts.data.opt_container.elem_args)
        actual_arg_array = <wrapper.NodeID*> malloc(actual_arg_count * sizeof(wrapper.NodeID))
        for arg_index, arg_node in enumerate(ts.data.opt_container.elem_args):
            if isinstance(arg_node, ast.node.BaseExp):
                target = ast_to_mast_exp(arg_node)
            else:
                assert isinstance(arg_node, ast.node.BaseTypeSpec)
                target = ast_to_mast_ts(arg_node)

            actual_arg_array[arg_index] = target

        return wrapper.w_new_get_poly_module_field_ts(
            poly_mod_id,
            ts_field_ix,
            actual_arg_count,
            actual_arg_array
        )

    # TupleTypeSpec
    elif isinstance(ts, ast.node.TupleTypeSpec):
        elem_ts_count = <size_t> len(ts.items)
        elem_ts_array = <wrapper.TypeSpecID*> malloc(sizeof(wrapper.TypeSpecID) * elem_ts_count)
        for i, elem_ts in enumerate(ts.items):
            elem_ts_array[i] = ast_to_mast_ts(elem_ts)
        
        return wrapper.w_new_tuple_ts(
            elem_ts_count,
            elem_ts_array
        )

    # FnSignatureTypeSpec
    elif isinstance(ts, ast.node.FnSignatureTypeSpec):
        arg_ts = ast_to_mast_ts(ts.arg_type_spec)
        ret_ts = ast_to_mast_ts(ts.return_type_spec)
        ret_ses = {
            None: None,
            PySES.Tot: wrapper.SES_TOT,
            PySES.Dv: wrapper.SES_DV,
            PySES.Exn: wrapper.SES_EXN,
            PySES.ST: wrapper.SES_ST,
            PySES.ML: wrapper.SES_ML
        }
        return wrapper.w_new_func_sgn_ts(arg_ts, ret_ts, ret_ses)

    # PtrTypeSpec
    elif isinstance(ts, ast.node.PtrTypeSpec):
        ptd_ts = ast_to_mast_ts(ts.ptd_ts)
        contents_is_mut = <bint> ts.is_mut
        return wrapper.w_new_ptr_ts(ptd_ts, contents_is_mut)

    # ArrayTypeSpec
    elif isinstance(ts, ast.node.ArrayTypeSpec):
        ptd_ts = ast_to_mast_ts(ts.elem_ts)
        count_exp = ast_to_mast_exp(ts.array_count)
        contents_is_mut = <bint> ts.is_mut
        return wrapper.w_new_array_ts(ptd_ts, count_exp, contents_is_mut)

    # SliceTypeSpec
    elif isinstance(ts, ast.node.SliceTypeSpec):
        ptd_ts = ast_to_mast_ts(ts.elem_ts)
        contents_is_mut = <bint> ts.is_mut
        return wrapper.w_new_slice_ts(ptd_ts, contents_is_mut)

    # AdtTypeSpec
    elif isinstance(ts, ast.node.AdtTypeSpec):
        adt_kind = ts.adt_kind
        if adt_kind == ast.node.AdtKind.Union:
            panic("NotImplemented: ast_to_mast_ts for AdtKind.Union")
        elif adt_kind == ast.node.AdtKind.Structure:
            item_count = len(ts.table.ordered_typing_elems)
            item_array = <wrapper.TypeSpecID*> malloc(item_count * sizeof(wrapper.TypeSpecID))
            for elem_index, elem in enumerate(ts.table.ordered_typing_elems):
                assert isinstance(elem, ast.node.Type1VElem)
                mast_elem_ts_id = ast_to_mast_ts(elem.type_spec)
                item_array[elem_index] = mast_elem_ts_id
            return wrapper.w_new_tuple_ts(item_count, item_array)
        else:
            panic("NotImplemented: ast_to_mast_ts for AdtTypeSpec with unknown ADT kind")

    # error:
    else:
        panic(f"NotImplemented: ast_to_mast_ts for t={ts} of kind {ts.__class__.__name__}")


cdef wrapper.ExpID ast_to_mast_exp(object e: ast.node.BaseExp):
    if isinstance(e, ast.node.UnitExp):
        return wrapper.w_get_unit_exp()

    elif isinstance(e, ast.node.NumberExp):
        # ExpID w_new_int_exp(size_t mantissa, IntegerSuffix int_suffix, bint is_neg)
        # ExpID w_new_float_exp(double value, FloatSuffix float_suffix)
        width_in_bits = type.scalar_width_in_bits.of(e.x_tid)
        if e.is_float:
            if width_in_bits == 64:
                float_suffix = wrapper.FS_F64
            else:
                # default to F32 for static computation unless higher precision is explicitly demanded
                float_suffix = wrapper.FS_F32
            value = float(e.value_text)
            return wrapper.w_new_float_exp(value, float_suffix)

        elif e.is_unsigned_int:
            if width_in_bits == 64:
                int_suffix = wrapper.IS_U64
            elif width_in_bits == 32:
                int_suffix = wrapper.IS_U32
            elif width_in_bits == 16:
                int_suffix = wrapper.IS_U16
            elif width_in_bits == 8:
                int_suffix = wrapper.IS_U8
            elif width_in_bits == 1:
                int_suffix = wrapper.IS_U1
            else:
                panic("Unknown UInt size in `qcl.monomorphizer.copier.ast_to_mast_exp`")

            mantissa: size_t = int(e.value_text)
            return wrapper.w_new_int_exp(mantissa, int_suffix, 0)

        elif e.is_signed_int:
            if width_in_bits == 64:
                int_suffix = wrapper.IS_S64
            elif width_in_bits == 32:
                int_suffix = wrapper.IS_S32
            elif width_in_bits == 16:
                int_suffix = wrapper.IS_S16
            elif width_in_bits == 8:
                int_suffix = wrapper.IS_S8
            else:
                panic("Unknown SInt size in `qcl.monomorphizer.copier.ast_to_mast_exp`")

            mantissa = int(e.value_text)
            return wrapper.w_new_int_exp(mantissa, int_suffix, 0)

    # TODO: implement these expression handlers
    elif isinstance(e, ast.node.StringExp):
        # ExpID w_new_string_exp(size_t code_point_count, int* code_point_array)
        code_point_count = <size_t> len(e.runes)
        code_point_array = <int*> malloc(sizeof(int) * code_point_count)
        for i in range(code_point_count):
            code_point_array[i] = e.runes[i]
        return wrapper.w_new_string_exp(code_point_count, code_point_array)

    elif isinstance(e, ast.node.IdExp):
        if not e.found_def_rec.is_bound_globally_visible:
            int_str_id = mk_int_str_from_py_str(e.name, 0)
            return wrapper.w_new_lid_exp(int_str_id)
        else:
            def_id = get_def_id_from_def_rec(e.found_def_rec)
            return wrapper.w_new_gid_exp(def_id)

    elif isinstance(e, ast.node.IdExpInModule):
        assert len(e.data.elem_args) == 0
        assert e.data.opt_container is not None

        found_sub_mod_exp = e.data.opt_container.found_def_rec.mod_exp
        assert isinstance(found_sub_mod_exp, ast.node.SubModExp)

        poly_mod_id = poly_mod_id_map[found_sub_mod_exp]

        original_bind1v_index = None
        for i, d in enumerate(found_sub_mod_exp.bind1v_def_obj_list_from_typer):
            if d.name == e.data.elem_name:
                original_bind1v_index = i
                break
        else:
            raise excepts.CompilerError("Could not find def object for field, though typing ok.")

        mast_field_index_map = found_sub_mod_exp.mast_bind1v_field_index_mapping_from_monomorphizer
        exp_field_ix = <size_t> mast_field_index_map[original_bind1v_index]

        actual_arg_count = len(e.data.opt_container.elem_args)
        actual_arg_array = <wrapper.NodeID*> malloc(actual_arg_count * sizeof(wrapper.NodeID))
        for arg_index, arg_node in enumerate(e.data.opt_container.elem_args):
            if isinstance(arg_node, ast.node.BaseExp):
                target = ast_to_mast_exp(arg_node)
            else:
                assert isinstance(arg_node, ast.node.BaseTypeSpec)
                target = ast_to_mast_ts(arg_node)

            actual_arg_array[arg_index] = target

        return wrapper.w_new_get_poly_module_field_exp(
            poly_mod_id,
            exp_field_ix,
            actual_arg_count,
            actual_arg_array
        )

    elif isinstance(e, ast.node.PostfixVCallExp):
        called_exp_id = ast_to_mast_exp(e.called_exp)
        arg_exp_id = ast_to_mast_exp(e.arg_exp)
        has_se = <bint> e.has_se
        return wrapper.w_new_func_call_exp(called_exp_id, arg_exp_id, has_se)

    elif isinstance(e, ast.node.UnaryExp):
        unary_operator = {
            PyUnaryOp.LogicalNot: wrapper.UNARY_LOGICAL_NOT,
            PyUnaryOp.Neg: wrapper.UNARY_NEG,
            PyUnaryOp.Pos: wrapper.UNARY_POS,
            PyUnaryOp.DeRef: wrapper.UNARY_DE_REF
        }[e.unary_op]
        unary_operand = ast_to_mast_exp(e.arg_exp)
        return wrapper.w_new_unary_op_exp(unary_operator, unary_operand)

    elif isinstance(e, ast.node.BinaryExp):
        binary_operator = {
            PyBinaryOp.Pow: wrapper.BINARY_POW,
            PyBinaryOp.Mul: wrapper.BINARY_MUL,
            PyBinaryOp.Div: wrapper.BINARY_DIV,
            PyBinaryOp.Rem: wrapper.BINARY_REM,
            PyBinaryOp.Add: wrapper.BINARY_ADD,
            PyBinaryOp.Sub: wrapper.BINARY_SUB,
            PyBinaryOp.LT: wrapper.BINARY_LT,
            PyBinaryOp.LEq: wrapper.BINARY_LE,
            PyBinaryOp.GT: wrapper.BINARY_GT,
            PyBinaryOp.GEq: wrapper.BINARY_GE,
            PyBinaryOp.Eq: wrapper.BINARY_EQ,
            PyBinaryOp.NE: wrapper.BINARY_NE,
            PyBinaryOp.LogicalAnd: wrapper.BINARY_LOGICAL_AND,
            PyBinaryOp.LogicalOr: wrapper.BINARY_LOGICAL_OR
        }[e.binary_op]
        lt_operand = ast_to_mast_exp(e.lt_arg_exp)
        rt_operand = ast_to_mast_exp(e.rt_arg_exp)
        return wrapper.w_new_binary_op_exp(binary_operator, lt_operand, rt_operand)

    elif isinstance(e, ast.node.IfExp):
        cond_exp = ast_to_mast_exp(e.cond_exp)
        then_exp = ast_to_mast_exp(e.then_exp)
        if e.opt_else_exp is not None:
            else_exp = ast_to_mast_exp(e.opt_else_exp)
        else:
            else_exp = wrapper.w_get_unit_exp()

        return wrapper.w_new_if_then_else_exp(cond_exp, then_exp, else_exp)

    elif isinstance(e, ast.node.LambdaExp):
        # copying arg names:
        arg_name_count = <uint32_t> len(e.arg_names)
        arg_name_array = <wrapper.IntStr*> malloc(sizeof(wrapper.IntStr) * arg_name_count)
        for i, arg_name in enumerate(e.arg_names):
            arg_name_array[i] = mk_int_str_from_py_str(arg_name, 0)

        # copying non-local names:
        non_local_name_count = <uint32_t> len(e.non_local_name_map)
        non_local_name_array = <wrapper.IntStr*> malloc(sizeof(wrapper.IntStr) * non_local_name_count)
        for i, (non_local_name, non_local_def_obj) in enumerate(e.non_local_name_map.items()):
            du = typer.names.infer_def_universe_of(non_local_name)
            if du == typer.definition.Universe.Value:
                non_local_name_array[i] = mk_int_str_from_py_str(non_local_name, 1)
            elif du == typer.definition.Universe.Type:
                non_local_name_array[i] = mk_int_str_from_py_str(non_local_name, 0)
            else:
                raise excepts.CompilerError("Unknown DU for non-local in LambdaExp")

        # translating body:
        body_exp = ast_to_mast_exp(e.body)

        # creating and returning the lambda:
        return wrapper.w_new_lambda_exp(
            arg_name_count,
            arg_name_array,
            non_local_name_count,
            non_local_name_array,
            body_exp
        )

    elif isinstance(e, ast.node.ChainExp):
        # ast-to-mast for the prefix element list

        # first, we gather all non-ignored elements:
        ignored_elem_class_tuple = (ast.node.Type1VElem,)
        non_ignored_elem_list = [
            element
            for element in e.table.elements
            if not isinstance(element, ignored_elem_class_tuple)
        ]

        elem_id_count = <size_t> len(non_ignored_elem_list)
        if elem_id_count:
            elem_id_array = <wrapper.ElemID*> malloc(sizeof(wrapper.ElemID) * elem_id_count)
            for i, elem in enumerate(non_ignored_elem_list):
                elem_id_array[i] = ast_to_mast_elem(elem)
        else:
            elem_id_array = <wrapper.ElemID*> 0

        # ast-to-mast for the final returned expression:
        if e.opt_tail is not None:
            chain_ret_exp_id = ast_to_mast_exp(e.opt_tail)
        else:
            chain_ret_exp_id = wrapper.w_get_unit_exp()

        return wrapper.w_new_chain_exp(
            elem_id_count,
            elem_id_array,
            chain_ret_exp_id
        )

    elif isinstance(e, ast.node.TupleExp):
        item_count = <size_t> len(e.items)
        item_array = <wrapper.ExpID*> malloc(sizeof(wrapper.ExpID) * item_count)
        for i, it_exp in enumerate(e.items):
            item_array[i] = ast_to_mast_exp(it_exp) 

        return wrapper.w_new_tuple_exp(item_count, item_array)

    elif isinstance(e, ast.node.GetElementByDotIndexExp):
        tuple_exp_id = ast_to_mast_exp(e.container)
        index_exp = e.index
        assert isinstance(index_exp, ast.node.NumberExp)
        index_int = <size_t> int(index_exp.value_text)

        return wrapper.w_new_get_tuple_field_by_index_exp(tuple_exp_id, index_int)

    elif isinstance(e, ast.node.GetElementByDotNameExp):
        tuple_exp_id = ast_to_mast_exp(e.container)
        tuple_py_tid = e.container.x_tid
        field_name_py_str = e.key_name
        field_index = type.elem.field_ix_of_name(tuple_py_tid, field_name_py_str)
        assert tuple_py_tid is not None
        assert field_name_py_str is not None
        assert field_index is not None

        return wrapper.w_new_get_tuple_field_by_index_exp(tuple_exp_id, field_index)

    elif isinstance(e, ast.node.CastExp):
        ts_id = ast_to_mast_ts(e.constructor_ts)
        exp_id = ast_to_mast_exp(e.initializer_data)
        return wrapper.w_new_cast_exp(ts_id, exp_id)

    else:
        # TODO: translate AST to MAST using the following functions:
        # ExpID w_new_allocate_one_exp(ExpID stored_val_exp_id, AllocationTarget allocation_target, bint allocation_is_mut)
        # ExpID w_new_allocate_many_exp(
        #     ExpID initializer_stored_val_exp_id,
        #     ExpID alloc_count_exp,
        #     AllocationTarget allocation_target,
        #     bint allocation_is_mut
        # )
        # ExpID w_new_get_mono_module_field_exp(MonoModID mono_mod_id, size_t exp_field_ix)
        # ExpID w_new_get_poly_module_field_exp(
        #     PolyModID poly_mod_id, size_t exp_field_ix,
        #     size_t arg_count, NodeID* arg_array
        # )

        panic(f"NotImplemented: ast_to_mast_exp for e={e}")


cdef wrapper.ElemID ast_to_mast_elem(object e: ast.node.BaseElem):
    if isinstance(e, ast.node.Bind1VElem):
        return wrapper.w_new_bind1v_elem(
            mk_int_str_from_py_str(e.id_name, 0),
            ast_to_mast_exp(e.bound_exp)
        )
    elif isinstance(e, ast.node.Bind1TElem):
        return wrapper.w_new_bind1t_elem(
            mk_int_str_from_py_str(e.id_name, 1),
            ast_to_mast_ts(e.bound_type_spec)
        )
    elif isinstance(e, ast.node.ForceEvalElem):
        return wrapper.w_new_do_elem(
            ast_to_mast_exp(e.discarded_exp)
        )
    else:
        panic(f"Unknown element instance: {e}")


cdef void define_declared_def_ids_in_proj(object proj: frontend.project.Project):
    for file_mod_exp in proj.file_module_exp_list:
        for sub_mod_name, sub_mod_exp in file_mod_exp.sub_module_map.items():
            define_declared_def_ids_in_sub_mod(sub_mod_name, sub_mod_exp)


cdef define_declared_def_ids_in_sub_mod(object sub_mod_name: str, object sub_mod_exp: ast.node.SubModExp):
    # NOTE: templates (BvDefs) are already trivially defined to map to nothing.

    # defining value bind elems in sub-modules:
    for bind1v_def_obj, bind1v_elem in zip(
            sub_mod_exp.bind1v_def_obj_list_from_typer,
            sub_mod_exp.table.ordered_value_imp_bind_elems
    ):
        def_id = get_def_id_from_def_rec(bind1v_def_obj)
        mast_id = ast_to_mast_exp(bind1v_elem.bound_exp)
        kind = <size_t> wrapper.w_get_node_kind(mast_id)
        wrapper.w_set_def_target(def_id, mast_id)

    for bind1t_def_obj, bind1t_elem in zip(
            sub_mod_exp.bind1t_def_obj_list_from_typer,
            sub_mod_exp.table.ordered_type_bind_elems
    ):
        def_id = get_def_id_from_def_rec(bind1t_def_obj)
        ts_id = ast_to_mast_ts(bind1t_elem.bound_type_spec)
        kind = <size_t> wrapper.w_get_node_kind(ts_id)
        wrapper.w_set_def_target(def_id, ts_id)


#
# Debug:
#

cdef void print_all_poly_mods(object title: str, object proj: frontend.Project):
    print(f">- BEG of generated PolyModID dump: {title} -<")

    for file_mod_exp in proj.file_module_exp_list:
        assert isinstance(file_mod_exp, ast.node.FileModExp)
        for sub_mod_name, sub_mod_exp in file_mod_exp.sub_module_map.items():
            wrapper.w_print_poly_mod(poly_mod_id_map[sub_mod_exp])

    print(f">- END of generated PolyModID dump: {title} -<")


cdef void print_all_mono_mods(object title: str, object proj: frontend.Project):
    print(f">- BEG of generated MonoModID dump: {title} -<")

    mono_mod_count = wrapper.w_count_all_mono_modules()
    for mono_mod_id in range(mono_mod_count):
        wrapper.w_print_mono_mod(mono_mod_id)

    print(f">- END of generated MonoModID dump: {title} -<")

#
#
# Phase 3: instantiating the entry point module
#
#

cdef instantiate_entry_point(object proj: frontend.Project):
    entry_point_source_module: frontend.FileModuleSource = proj.entry_point_source_module
    entry_point_file_mod_exp: ast.node.FileModExp = entry_point_source_module.ast_file_mod_exp_from_frontend
    
    # searching for a sub-module by a specific name to use as an entry point:
    entry_point_sub_mod_name = "entry_point_for_v1_default_loader"
    if entry_point_sub_mod_name not in entry_point_file_mod_exp.sub_module_map:
        raise excepts.CheckerCompilationError(
            f"Expected a sub-module named `{entry_point_sub_mod_name}` in the first file module."
        )
        panic("see `CheckerCompilationError` above.")
    
    # retrieving the found sub-module for later...
    entry_point_sub_mod_exp = entry_point_file_mod_exp.sub_module_map[entry_point_sub_mod_name]

    # ensuring this module admits 0 template arguments (i.e. is monomorphic):
    if entry_point_sub_mod_exp.template_arg_names:
        raise excepts.CheckerCompilationError(
            f"Entry-point sub-module with name `{entry_point_sub_mod_name}` in the first file module"
            "cannot admit any template arguments."
        )
        panic("see `CheckerCompilationError` above.")

    # searching for a function that can be used as an entry point:
    #   - cf `main` in C/C++/Java
    entry_point_function_name = "main_for_v1_default_loader"
    entry_point_rec = None
    for rec in entry_point_sub_mod_exp.bind1v_def_obj_list_from_typer:
        # checking this symbol's name:
        rec_name_correct = (rec.name == entry_point_function_name)
        if rec_name_correct:
            entry_point_rec = rec
            break
    else:
        msg_suffix = f"Could not find a suitable entry point function named `{entry_point_function_name}`"
        raise excepts.CheckerCompilationError(msg_suffix)

    # checking the found symbol's type:
    _, rec_tid = rec.scheme.shallow_instantiate()
    expected_tid = type.get_fn_type(
        type.get_unit_type(),
        type.get_int_type(32, is_unsigned=False),
        type.side_effects.SES.ML,
        type.closure_spec.CS.Maybe      # i.e. does not need a ctx pointer, but can be invoked with one (layout)
    )
    rec_type_correct = (rec_tid == expected_tid)
    if not rec_type_correct:
        msg_suffix = (
            f"Supplied entry-point named `{entry_point_function_name}` does not have the correct type: "
            f"expected `{entry_point_function_name} ~ {type.spelling.of(expected_tid)}`, but "
            f"received `{entry_point_function_name} ~ {type.spelling.of(rec_tid)}`"
        )
        # raise excepts.CheckerCompilationError(msg_suffix)
        panic(msg_suffix)

    # instantiating this entry-point sub-module:
    #   - it acts as the root of all monomorphic global discovery
    entry_point_poly_mod_id = poly_mod_id_map[entry_point_sub_mod_exp]
    wrapper.w_instantiate_poly_mod(entry_point_poly_mod_id, wrapper.w_empty_arg_list_id())

