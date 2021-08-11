"""
This module copies `qcl.ast.node.*` instances into `qcl.monomorphizer.mast`, then evaluates a critical part of it.
We pretend polymorphic definitions accept monomorphic definitions with IDs that can be substituted upon rewrite.
This rewriting while substituting out formal args for actual ones is called monomorphization.
Since substituting value formal args requires knowing the value of each actual argument, monomorphization requires and
provides constant evaluation. The two are intertwined.
"""

from qcl import frontend
from qcl import ast

cimport qcl.monomorphizer.wrapper as wrapper


cpdef monomorphize_project(proj: frontend.project.Project):
    # sourcing entry point:
    entry_point_source_module: frontend.FileModuleSource = proj.entry_point_source_module
    entry_point_file_mod_exp: ast.node.FileModExp = entry_point_source_module.ast_file_mod_exp_from_frontend

    # first, generating MAST code for all file-mods in this project

    # next, evaluating the entry point constant:

    # TODO: all constants that were evaluated for the entry point must be bundled for future passes.
    #       aka UNSHAKEN MONOMORPHIC SET (UMS)

    # TODO: delete this 'test' call that is used to debug.
    test_extension()


cdef test_extension():
    print("--- Begin Extension Test ---")

    wrapper.w_init()
    print("... Init successful")

    unit_ts_id = wrapper.w_mk_unit_ts()
    print(f"... UnitTypeSpecID = {unit_ts_id}")

    unit_exp_id = wrapper.w_mk_unit_exp()
    print(f"... UnitExpID = {unit_exp_id}")

    wrapper.w_drop()
    print("... Drop successful")

    print("--- Extension test complete ---")
