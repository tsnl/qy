import dataclasses
from typing import *

from qcl import frontend
from qcl import ast
from qcl import type
from qcl import excepts

from . import scheme
from . import seeding
from . import context
from . import definition
from . import unifier
from . import substitution


class SubModTypeInferenceInfo(object):
    type_template_arg_free_var_map: Dict[int, type.identity.TID]

    def __init__(self):
        super().__init__()
        self.type_template_arg_free_var_map = {}


@dataclasses.dataclass
class FileModTypeInferenceInfo(object):
    tid: type.identity.TID
    sub: substitution.Substitution


file_mod_inferences: Dict[ast.node.FileModExp, FileModTypeInferenceInfo] = {}
sub_mod_inferences: Dict[ast.node.SubModExp, SubModTypeInferenceInfo]
mod_exp_map: Dict[type.identity.TID, ast.node.BaseModExp] = {}


def infer_project_types(project: frontend.Project, all_file_module_list: List[ast.node.FileModExp]):
    """
    this pass uses `unify` to generate substitutions that, once all applied, eliminate all free type variables from the
    system.
    :param project: the project whose modules to perform type inference on
    :param all_file_module_list: a list of all discovered FileModuleExp nodes.
    """

    cm = context.ContextManager()

    # each imported file module is looked up in the global context and stored.
    # Later, it is mapped to a file-module-scope-native symbol.
    for file_module_exp in all_file_module_list:
        infer_file_mod_exp_tid(cm, file_module_exp)


def infer_file_mod_exp_tid(
        cm: context.ContextManager, file_mod_exp: ast.node.FileModExp
) -> Tuple[substitution.Substitution, type.identity.TID]:
    # we use `seeding.mod_tid[...]` to resolve module imports out-of-order
    cached_mod_inference = file_mod_inferences.get(file_mod_exp, None)
    if cached_mod_inference is not None:
        return cached_mod_inference.sub, cached_mod_inference.tid
    else:
        seeded_file_mod_exp_tid = seeding.mod_tid_map[file_mod_exp]
        mod_exp_map[seeded_file_mod_exp_tid] = file_mod_exp
        out_sub = substitution.empty

        # storing the seeded values in the inference cache so that cyclic imports will work:
        file_mod_inferences[file_mod_exp] = FileModTypeInferenceInfo(seeded_file_mod_exp_tid, out_sub)

        #
        # now, our goal is to add all import and 'mod' elements to the elem info list:
        #

        # cm.push_context()

        elem_info_list = []

        for import_mod_name, import_mod_source in file_mod_exp.imports_source_map_from_frontend.items():
            assert isinstance(import_mod_source, frontend.FileModuleSource)
            imported_file_mod_exp = import_mod_source.ast_file_mod_exp_from_frontend
            import_sub, imported_mod_tid = infer_file_mod_exp_tid(cm, imported_file_mod_exp)
            out_sub = out_sub.compose(import_sub)

            # updating elem_info_list:
            for elem_info in elem_info_list:
                assert isinstance(elem_info, type.elem.ElemInfo)
                elem_info.tid = out_sub.rewrite_type(elem_info.tid)
            new_elem_info = type.elem.ElemInfo(import_mod_name, imported_mod_tid)
            elem_info_list.append(new_elem_info)

            # defining the symbol:
            def_name = import_mod_name
            def_obj = definition.ModDef(imported_file_mod_exp.loc, scheme.Scheme(imported_mod_tid))
            cm.try_define(def_name, def_obj)

        for sub_mod_name, sub_mod_exp in file_mod_exp.sub_module_map.items():
            sub_mod_substitution, sub_mod_tid = infer_sub_mod_exp_tid(cm, sub_mod_exp)

            # todo: update elem_info_list

            # todo: fetch defined symbol from the active context
            #   - first, fetch active context using `seeding.context_map`
            #   - then, perform lookup for a definition to get a scheme
            #   - then, instantiate and unify with `sub_mod_tid`
            #   - finally, apply sub to `cm`

        new_mod_tid = type.new_module_type(tuple(elem_info_list))
        out_sub = out_sub.compose(substitution.Substitution({seeded_file_mod_exp_tid: new_mod_tid}))

        # cm.pop_context()

        file_mod_inferences[file_mod_exp] = FileModTypeInferenceInfo(new_mod_tid, out_sub)
        mod_exp_map[new_mod_tid] = file_mod_exp

        return out_sub, new_mod_tid


def infer_sub_mod_exp_tid(
        cm: context.ContextManager, sub_mod_exp: ast.node.SubModExp
) -> Tuple[substitution.Substitution, type.identity.TID]:
    seeded_sub_mod_exp_tid = seeding.mod_tid_map[sub_mod_exp]

    out_sub = substitution.empty

    elem_info_list: List[type.elem.ElemInfo] = []

    for index, template_arg_name in enumerate(sub_mod_exp.template_arg_names):
        # TODO: check if type arg or value
        # - if type arg, create a BoundVar and store in `sub_mod_inferences_map`
        # - if value arg, create a FreeVar, subject to further inference.
        # - regardless, need to ALSO DEFINE in the top context.

        def_universe = infer_template_arg_def_universe(template_arg_name)
        if def_universe == definition.DefinitionUniverse.Type:
            arg_var_tid = type.new_free_var(f"template-t-arg:{template_arg_name}")
            def_ok = cm.try_define(
                template_arg_name,
                definition.TypeDef(sub_mod_exp.loc, arg_var_tid)
            )
        else:
            assert def_universe == definition.DefinitionUniverse.Value
            arg_var_tid = type.new_free_var(f"template-v-arg:{template_arg_name}")
            def_ok = cm.try_define(
                template_arg_name,
                definition.ValueDef(sub_mod_exp.loc, arg_var_tid)
            )

        if not def_ok:
            raise excepts.TyperCompilationError(
                f"template arg name {template_arg_name} conflicts with another definition."
            )

    for elem in sub_mod_exp.table.ordered_value_imp_bind_elems:
        assert isinstance(elem, ast.node.BaseBindElem)
        infer_binding_elem_types(cm, elem)

    for elem in sub_mod_exp.table.ordered_typing_elems:
        infer_typing_elem_types(cm, elem)

    sub_mod_exp_tid = type.new_module_type(tuple(elem_info_list))

    out_sub = out_sub.compose(substitution.Substitution({seeded_sub_mod_exp_tid: sub_mod_exp_tid}))

    return out_sub, sub_mod_exp_tid


def infer_binding_elem_types(cm: context.ContextManager, elem: ast.node.BaseElem):
    if isinstance(elem, ast.node.Bind1VElem):
        s1, rhs_tid = infer_exp_tid(cm, elem.bound_exp)
        # TODO: need a way to get the defined symbol's type so we can unify with RHS
        s2 = s1
        s2.overwrite_context_manager(cm)
    elif isinstance(elem, ast.node.Bind1TElem):
        s1, rhs_tid = infer_type_spec_tid(cm, elem.bound_type_spec)
        # TODO: need a way to get the defined symbol's types so we can unify with RHS
        s2 = s1
        s2.overwrite_context_manager(cm)
    else:
        raise NotImplementedError(f"Unknown elem type: {elem.__class__.__name__}")


def infer_typing_elem_types(cm: context.ContextManager, elem: ast.node.BaseElem):
    pass


def infer_exp_tid(
        cm: context.ContextManager, exp: ast.node.BaseExp
) -> Tuple[substitution.Substitution, type.identity.TID]:
    #
    # context-dependent branches: ID, ModAddressID
    #

    if isinstance(exp, ast.node.IdExp):
        found_def = cm.lookup(exp.name)
        if found_def is not None:
            sub, def_tid = found_def.scheme.instantiate()
            return sub, def_tid
        else:
            raise excepts.TyperCompilationError(f"Symbol {exp.name} used but not defined.")

    elif isinstance(exp, ast.node.GetModElementExp):
        if exp.opt_container is None:
            # look up a file mod def in the active scope:
            assert not exp.elem_args
            file_mod_name = exp.elem_name
            found_def = cm.lookup(file_mod_name)
            if not isinstance(found_def, definition.ModDef):
                raise excepts.TyperCompilationError(f"Expected {exp.elem_name} to refer to a file-mod, not other.")
            else:
                sub, file_mod_tid = found_def.scheme.instantiate()
                return sub, file_mod_tid
        else:
            assert exp.opt_container is not None

            # getting a mod-exp for the container:
            container_sub, contained_tid = infer_exp_tid(cm, exp.opt_container)
            container_mod_exp = mod_exp_map[contained_tid]

            # looking up an element in the container:
            pass

            raise NotImplementedError("Looking up a submodule in a file-module")

    #
    # context-independent branches:
    #

    elif isinstance(exp, ast.node.UnitExp):
        return substitution.empty, type.get_unit_type()

    elif isinstance(exp, ast.node.StringExp):
        return substitution.empty, type.get_str_type()

    elif isinstance(exp, ast.node.NumberExp):
        default_number_width_in_bits = 32

        if exp.width_in_bits is None:
            width_in_bits = default_number_width_in_bits
        else:
            width_in_bits = exp.width_in_bits

        if exp.is_explicitly_float:
            return substitution.empty, type.get_float_type(width_in_bits//8)

        elif exp.is_explicitly_unsigned_int:
            return substitution.empty, type.get_int_type(width_in_bits//8, is_unsigned=True)

        else:
            assert exp.is_explicitly_signed_int
            return substitution.empty, type.get_int_type(width_in_bits//8, is_unsigned=False)

    elif isinstance(exp, ast.node.PostfixVCallExp):
        ret_tid = type.new_free_var(f"fn-call")

        s1, formal_fn_tid = infer_exp_tid(cm, exp.called_exp)

        s2, arg_tid = infer_exp_tid(cm, exp.arg_exp)
        arg_tid = s1.rewrite_type(arg_tid)

        s12 = s1.compose(s2)

        ses = type.side_effects.SES.Elim_AnyNonTot if exp.has_se else type.side_effects.SES.Tot
        actual_fn_tid = type.get_fn_type(arg_tid, ret_tid, ses)
        actual_fn_tid = s12.rewrite_type(actual_fn_tid)

        s3 = unifier.unify(actual_fn_tid, formal_fn_tid)

        s123 = s12.compose(s3)

        return s123, ret_tid

    # TODO: type a chain expression

    else:
        raise NotImplementedError(f"Type inference for {exp.__class__.__name__}")


def infer_type_spec_tid(
        cm: context.ContextManager, ts: ast.node.BaseTypeSpec
) -> Tuple[substitution.Substitution, type.identity.TID]:
    raise NotImplementedError(f"Type inference for {ts.__class__.__name__}")


def infer_template_arg_def_universe(name: str) -> definition.DefinitionUniverse:
    for ch in name:
        if ch.isalpha():
            if ch.isupper():
                return definition.DefinitionUniverse.Type
            else:
                assert ch.islower()
                return definition.DefinitionUniverse.Value
    else:
        raise excepts.TyperCompilationError("Invalid template arg name")
