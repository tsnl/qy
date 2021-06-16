from typing import *

from qcl import ast
from qcl import frontend
from qcl import type

from . import scheme
from . import context
from . import definition


mod_tid_map = {}
mod_exp_map = {}

bind1_elem_tid_map = {}
type1_elem_tid_map = {}

context_map = {}


def seed_project_types(
        project: frontend.Project,
        all_file_module_list: List[ast.node.FileModExp]
):
    """
    this pass creates `FreeVar` types for each module definition.
    For sub-modules, `BoundVar` is used for each template arg and must be substituted out by a scheme before use.
    :param project: the project whose definitions to seed
    :param all_file_module_list: a list of all discovered FileModuleExp nodes.
    """

    for file_module_exp in all_file_module_list:
        seed_file_mod_exp(file_module_exp)


def seed_file_mod_exp(file_mod_exp: ast.node.FileModExp):
    # creating a FreeVar for this file-mod-exp:
    file_mod_tid = type.new_free_var(f"file-mod:{file_mod_exp.source.file_path_rel_cwd}")
    mod_tid_map[file_mod_exp] = file_mod_tid
    mod_exp_map[file_mod_tid] = file_mod_exp

    # creating an appropriate FreeVar for each sub-mod-exp:
    for sub_mod_name, sub_mod_exp in file_mod_exp.sub_module_map.items():
        seed_sub_mod_exp(sub_mod_name, sub_mod_exp)

    # NOTE: even if this sub-mod accepts template args, we can substitute for a `Module` type with monomorphic fields
    #       whose types depend on Bound Vars.
    #       These can then be substituted out by template instantiations. Otherwise, they generate errors.


def seed_sub_mod_exp(sub_mod_name: str, sub_mod_exp: ast.node.SubModExp):
    sub_mod_tid = type.new_free_var(f"sub-mod:{sub_mod_name}")
    mod_tid_map[sub_mod_exp] = sub_mod_tid
    mod_exp_map[sub_mod_tid] = sub_mod_exp

    # NOTE: by spec, modules cannot be defined in sub-modules, so we need recurse no further to find modules.

    # TODO: push contexts and write definitions that can be associated for inference
    # TODO: store defined TID in `bind1_elem_tid_map` and `type1_elem_tid_map`
    # TODO: store active context in `context_map`
