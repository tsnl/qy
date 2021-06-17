import dataclasses
from typing import *

from qcl import frontend
from qcl import ast
from qcl import type
from qcl import excepts

from . import seeding
from . import context
from . import definition
from . import unifier
from . import substitution
from . import names


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


def infer_project_types(
        project: frontend.Project,
        all_file_module_list: List[ast.node.FileModExp]
):
    """
    this pass uses `unify` to generate substitutions that, once all applied, eliminate all free type variables from the
    system.
    :param project: the project whose modules to perform type inference on
    :param all_file_module_list: a list of all discovered FileModuleExp nodes.
    """

    # each imported file module is looked up in the global context and stored.
    # Later, it is mapped to a file-module-scope-native symbol.
    for file_module_exp in all_file_module_list:
        infer_file_mod_exp_tid(file_module_exp)


def infer_file_mod_exp_tid(
        file_mod_exp: ast.node.FileModExp
) -> Tuple[substitution.Substitution, type.identity.TID]:
    # we use `seeding.mod_tid[...]` to resolve module imports out-of-order
    cached_mod_inference = file_mod_inferences.get(file_mod_exp, None)
    if cached_mod_inference is not None:
        return cached_mod_inference.sub, cached_mod_inference.tid
    else:
        seeded_file_mod_exp_tid = seeding.mod_exp_tid_map[file_mod_exp]
        file_mod_ctx = seeding.mod_context_map[file_mod_exp]
        out_sub = substitution.empty

        # storing the seeded values in the inference cache so that cyclic imports will work:
        file_mod_inferences[file_mod_exp] = FileModTypeInferenceInfo(seeded_file_mod_exp_tid, out_sub)

        #
        # now, our goal is to construct a module type.
        # we need to add all 'import' and 'mod' elements to the elem info list, unifying along the way.
        # remember that all globally-accessible symbols are already defined.
        #

        elem_info_list = []

        # adding elem_info for each import:
        for import_mod_name, import_mod_source in file_mod_exp.imports_source_map_from_frontend.items():
            # inferring the latest type of the imported module:
            #   - if it is still being inferred, we will get the seeded TID as a fallback.
            #   - when the original module finishes resolution, the seeded TID will be eliminated.
            assert isinstance(import_mod_source, frontend.FileModuleSource)
            imported_file_mod_exp = import_mod_source.ast_file_mod_exp_from_frontend
            import_sub, imported_mod_tid = infer_file_mod_exp_tid(imported_file_mod_exp)

            # composing substitutions:
            # NOTE: all previous elements are now invalidated.
            out_sub = out_sub.compose(import_sub)

            # adding the new elem_info_list:
            new_elem_info = type.elem.ElemInfo(import_mod_name, imported_mod_tid)
            elem_info_list.append(new_elem_info)

        # adding elem_info for each sub-mod:
        for sub_mod_name, sub_mod_exp in file_mod_exp.sub_module_map.items():
            sub_mod_substitution, sub_mod_tid = infer_sub_mod_exp_tid(sub_mod_exp)

            # composing substitutions:
            # NOTE: all previous elements are now invalidated.
            out_sub = out_sub.compose(sub_mod_substitution)

            new_elem_info = type.elem.ElemInfo(sub_mod_name, sub_mod_tid)
            elem_info_list.append(new_elem_info)

        # before creation, all but the last elem_info needs to be updated with `out_sub`:
        for i in range(len(elem_info_list) - 1):
            old_tid = elem_info_list[i].tid
            new_tid = out_sub.rewrite_type(old_tid)
            elem_info_list[i].tid = new_tid

        # creating a new module type:
        new_mod_tid = type.new_module_type(tuple(elem_info_list))
        out_sub = out_sub.compose(substitution.Substitution({seeded_file_mod_exp_tid: new_mod_tid}))

        # updating caches (including seeded values, called re-seeding):
        # NOTE: re-seeding is 'unsafe', but much more efficient than creating a copy map.
        # THUS, both the original and new TIDs correctly map to the correct file-mod-exp.
        file_mod_inferences[file_mod_exp] = FileModTypeInferenceInfo(new_mod_tid, out_sub)
        seeding.mod_tid_exp_map[new_mod_tid] = file_mod_exp

        return out_sub, new_mod_tid


def infer_sub_mod_exp_tid(
        sub_mod_exp: ast.node.SubModExp
) -> Tuple[substitution.Substitution, type.identity.TID]:
    # acquiring the seeded context, updating our caches:
    seeded_sub_mod_exp_tid = seeding.mod_exp_tid_map[sub_mod_exp]
    seeded_sub_mod_exp_ctx = seeding.mod_context_map[sub_mod_exp]

    out_sub = substitution.empty

    elem_info_list: List[type.elem.ElemInfo] = []

    for elem in sub_mod_exp.table.ordered_value_imp_bind_elems:
        assert isinstance(elem, ast.node.BaseBindElem)
        infer_binding_elem_types(seeded_sub_mod_exp_ctx, elem)

    for elem in sub_mod_exp.table.ordered_typing_elems:
        infer_typing_elem_types(seeded_sub_mod_exp_ctx, elem)

    sub_mod_exp_tid = type.new_module_type(tuple(elem_info_list))
    out_sub = out_sub.compose(substitution.Substitution({seeded_sub_mod_exp_tid: sub_mod_exp_tid}))

    # re-seeding the new sub_mod's TID:
    seeding.mod_tid_exp_map[sub_mod_exp_tid] = sub_mod_exp

    return out_sub, sub_mod_exp_tid


def infer_binding_elem_types(ctx: context.Context, elem: ast.node.BaseBindElem):
    if isinstance(elem, ast.node.Bind1VElem):
        s1, rhs_tid = infer_exp_tid(ctx, elem.bound_exp)
        lhs_v_def_obj = ctx.lookup(elem.id_name, shallow=True)
        if lhs_v_def_obj is not None:
            # pre-seeded:
            s2, lhs_v_tid = s1.rewrite_scheme(lhs_v_def_obj.scheme).instantiate()
        else:
            # un-seeded: bound inside a chain
            raise NotImplementedError("binding elem in chains")

        s3 = unifier.unify(lhs_v_tid, rhs_tid)
        sub = s2.compose(s3)

        sub.rewrite_contexts_everywhere(ctx)

    elif isinstance(elem, ast.node.Bind1TElem):
        s1, rhs_tid = infer_type_spec_tid(ctx, elem.bound_type_spec)
        lhs_ts_def_obj = ctx.lookup(elem.id_name, shallow=True)
        if lhs_ts_def_obj is not None:
            # pre-seeded:
            s2, lhs_ts_tid = s1.rewrite_scheme(lhs_ts_def_obj.scheme).instantiate()
        else:
            # un-seeded: bound inside a chain
            raise NotImplementedError("binding elem in chains")

        s3 = unifier.unify(lhs_ts_tid, rhs_tid)
        sub = s2.compose(s3)

        sub.rewrite_contexts_everywhere(ctx)

    else:
        raise NotImplementedError(f"Unknown elem type: {elem.__class__.__name__}")


def infer_typing_elem_types(ctx: context.Context, elem: ast.node.BaseTypingElem):
    raise NotImplementedError("Typing any BaseTypingElem")


def infer_exp_tid(
        ctx: context.Context, exp: ast.node.BaseExp
) -> Tuple[substitution.Substitution, type.identity.TID]:
    #
    # context-dependent branches: ID, ModAddressID
    #

    if isinstance(exp, ast.node.IdExp):
        found_def = ctx.lookup(exp.name)
        if found_def is not None:
            sub, def_tid = found_def.scheme.instantiate()
            return sub, def_tid
        else:
            raise excepts.TyperCompilationError(f"Symbol {exp.name} used but not defined.")

    elif isinstance(exp, ast.node.GetModElementExp):
        if exp.opt_container is None:
            # look up an imported mod-def:
            assert not exp.elem_args
            file_mod_name = exp.elem_name
            found_def = ctx.lookup(file_mod_name, shallow=False)

            if found_def is None:
                msg_suffix = f"symbol {file_mod_name} not found"
                raise excepts.TyperCompilationError(msg_suffix)
            elif not isinstance(found_def, definition.ModRecord):
                msg_suffix = f"expected {file_mod_name} to refer to a file-mod, not other"
                raise excepts.TyperCompilationError(msg_suffix)
            else:
                sub, file_mod_tid = found_def.scheme.instantiate()
                # TODO: why not retrieve and also return the GetModElementExp from Defn?
                return sub, file_mod_tid
        else:
            assert exp.opt_container is not None

            # getting a mod-exp for the container:
            container_sub, container_tid = infer_exp_tid(ctx, exp.opt_container)
            container_mod_exp = seeding.mod_tid_exp_map[container_tid]
            container_ctx = seeding.mod_context_map[container_mod_exp]

            # looking up the element in the container:
            found_def_obj = container_ctx.lookup(exp.elem_name, shallow=True)
            if found_def_obj is None:
                msg_suffix = f"element {exp.elem_name} not found in existing module"
                raise excepts.TyperCompilationError(msg_suffix)

            # instantiating the found definition's scheme, using actual arguments if provided:
            found_scheme = found_def_obj.scheme
            if not exp.elem_args:
                sub, found_tid = found_scheme.instantiate()
                return sub, found_tid
            else:
                #
                # actual arg validation + processing:
                #

                expected_arg_count = len(container_mod_exp.template_arg_names)
                actual_arg_count = len(exp.elem_args)
                if actual_arg_count != expected_arg_count:
                    msg_suffix = f"expected {expected_arg_count} template args, but received {actual_arg_count}"
                    raise excepts.TyperCompilationError(msg_suffix)

                # sifting type args from value args:
                actual_v_args = []
                actual_t_args = []
                for elem_arg_ast_node in exp.elem_args:
                    if isinstance(elem_arg_ast_node, ast.node.BaseExp):
                        actual_v_args.append(actual_v_args)
                    else:
                        assert isinstance(elem_arg_ast_node, ast.node.BaseTypeSpec)
                        actual_t_args.append(actual_t_args)

                #
                # inferring types of type & value actual args:
                #

                sub = substitution.empty

                # inferring TIDs of value args
                actual_v_arg_tid_list = []
                for actual_v_arg in actual_v_args:
                    e_sub, e_tid = infer_exp_tid(ctx, actual_v_arg)
                    sub = sub.compose(e_sub)
                    actual_v_arg_tid_list.append(e_tid)

                # inferring TIDs of type args from context:
                actual_t_arg_tid_list = []
                for actual_t_arg in actual_t_args:
                    ts_sub, ts_tid = infer_type_spec_tid(ctx, actual_t_arg)
                    sub = sub.compose(ts_sub)

                #
                # unifying TIDs of value args
                # - only perform this when value args are actually passed (even if formally defined)
                #

                if actual_v_arg_tid_list:
                    # acquiring a list of value arg names in the container:
                    val_arg_names = names.filter_vals(container_mod_exp.template_arg_names)

                    # looking up their defined types:
                    # - note template args should always be pre-seeded and monomorphic in the scheme context.
                    formal_v_arg_tid_list = []
                    for val_arg_name in val_arg_names:
                        val_arg_def_obj = ctx.lookup(val_arg_name, shallow=True)
                        assert val_arg_def_obj is not None
                        assert not val_arg_def_obj.scheme.bound_vars
                        val_arg_tid = val_arg_def_obj.scheme.instantiate()
                        formal_v_arg_tid_list.append(val_arg_tid)

                    # unifying formal and actual value arg types:
                    assert len(formal_v_arg_tid_list) == len(actual_v_arg_tid_list)
                    for formal_tid, actual_tid in zip(formal_v_arg_tid_list, actual_v_arg_tid_list):
                        sub = sub.compose(unifier.unify(formal_tid, actual_tid))
                else:
                    pass

                #
                # unifying TIDs of type args using `Scheme.instantiate`:
                #

                instantiate_sub, final_tid = found_scheme.instantiate(actual_t_arg_tid_list)
                sub = sub.compose(instantiate_sub)

                return sub, final_tid

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

        s1, formal_fn_tid = infer_exp_tid(ctx, exp.called_exp)

        s2, arg_tid = infer_exp_tid(ctx, exp.arg_exp)
        arg_tid = s1.rewrite_type(arg_tid)

        s12 = s1.compose(s2)

        ses = type.side_effects.SES.Elim_AnyNonTot if exp.has_se else type.side_effects.SES.Tot
        actual_fn_tid = type.get_fn_type(arg_tid, ret_tid, ses)
        actual_fn_tid = s12.rewrite_type(actual_fn_tid)

        s3 = unifier.unify(actual_fn_tid, formal_fn_tid)

        s123 = s12.compose(s3)

        return s123, ret_tid

    # TODO: type a chain expression
    elif isinstance(exp, ast.node.ChainExp):
        raise NotImplementedError("Type inference for chain expressions")

    else:
        raise NotImplementedError(f"Type inference for {exp.__class__.__name__}")


def infer_type_spec_tid(
        ctx: context.Context, ts: ast.node.BaseTypeSpec
) -> Tuple[substitution.Substitution, type.identity.TID]:
    raise NotImplementedError(f"Type inference for {ts.__class__.__name__}")
