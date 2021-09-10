import dataclasses
import typing as t
from collections import namedtuple

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
from . import deferred


SES = type.side_effects.SES
CS = type.closure_spec.CS
MWI = namedtuple("MemoryWindowInference", [
    "contents_may_be_local",        # : bool
    "contents_may_be_non_local"     # : bool
])


class SubModTypeInferenceInfo(object):
    type_template_arg_free_var_map: t.Dict[int, type.identity.TID]

    def __init__(self):
        super().__init__()
        self.type_template_arg_free_var_map = {}


@dataclasses.dataclass
class FileModTypeInferenceInfo(object):
    tid: type.identity.TID
    sub: substitution.Substitution


file_mod_inferences: t.Dict["ast.node.FileModExp", FileModTypeInferenceInfo] = {}
sub_mod_inferences: t.Dict["ast.node.SubModExp", SubModTypeInferenceInfo]


def infer_project_types(
        project: frontend.Project,
        root_ctx: context.Context,
        all_file_module_list: t.List["ast.node.FileModExp"]
):
    """
    this pass uses `unify` to generate substitutions that, once all applied, eliminate all free type variables from the
    system.
    :param project: the project whose modules to perform type inference on
    :param root_ctx: the root context used by this project
    :param all_file_module_list: a list of all discovered FileModuleExp nodes.
    """

    # TODO: make a list of `BaseDeferredOrder` instances and pass it (by reference) to `infer` calls.
    deferred_list = deferred.DeferredList()

    # each imported file module is looked up in the global context and stored.
    # Later, it is mapped to a file-module-scope-native symbol.
    for file_module_exp in all_file_module_list:
        sub, file_mod_tid = infer_file_mod_exp_tid(project, file_module_exp, deferred_list)

    # iteratively and repeatedly attempt to resolve each DeferredOrder:
    #   - DeferredOrder `solve` calls resolve overloaded type operations
    #   - can begin by simply printing each item in the DeferredList
    #   - simply call `solve`, and manage a list of stuff that is stalled.
    #       - boolean ret field True if further iterations requested (since new info was obtained)
    #       - iterate until fixed-point is reached, when system is stable

    any_solved = True
    while any_solved:
        any_solved = deferred_list.solve_step(
            lambda rw_sub: rewrite_system_with_sub(project, root_ctx, deferred_list, rw_sub)
        )

    if not deferred_list.check_all_solved():
        unsolved = deferred_list.unsolved_str()
        msg_suffix = f"could not resolve all type overloads:\n{unsolved}"
        raise excepts.TyperCompilationError(msg_suffix)


def infer_file_mod_exp_tid(
        project: "frontend.Project",
        file_mod_exp: "ast.node.FileModExp",
        deferred_list: "deferred.DeferredList"
) -> t.Tuple[substitution.Substitution, type.identity.TID]:
    # we use `seeding.mod_tid[...]` to resolve module imports out-of-order
    cached_mod_inference = file_mod_inferences.get(file_mod_exp, None)
    if cached_mod_inference is not None:
        return substitution.empty, cached_mod_inference.tid
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

        # FROM IMPORTS:
        # adding elem_info for each import:
        for import_mod_name, import_mod_source in file_mod_exp.imports_source_map_from_frontend.items():
            # inferring the latest type of the imported module:
            #   - if it is still being inferred, we will get the seeded TID as a fallback.
            #   - when the original module finishes resolution, the seeded TID will be eliminated.
            assert isinstance(import_mod_source, frontend.FileModuleSource)
            imported_file_mod_exp = import_mod_source.ast_file_mod_exp_from_frontend
            import_sub, imported_mod_tid = infer_file_mod_exp_tid(project, imported_file_mod_exp, deferred_list)

            # composing substitutions:
            # NOTE: all previous elements are now invalidated.
            out_sub = out_sub.compose(import_sub)

            # adding the new elem_info_list:
            new_elem_info = type.elem.ElemInfo(import_mod_name, imported_mod_tid, False)
            elem_info_list.append(new_elem_info)

        # FROM SUB-MODS:
        # adding elem_info for each sub-mod:
        for sub_mod_name, sub_mod_exp in file_mod_exp.sub_module_map.items():
            sub_mod_substitution, sub_mod_tid = infer_sub_mod_exp_tid(project, sub_mod_exp, deferred_list)

            # composing substitutions:
            # NOTE: all previous elements are now invalidated.
            out_sub = out_sub.compose(sub_mod_substitution)

            new_elem_info = type.elem.ElemInfo(sub_mod_name, sub_mod_tid, False)
            elem_info_list.append(new_elem_info)

        # re-applying the latest substitution to all elements but the last:
        # - NOTE: this involves replacing the `elem_info_list` list
        elem_info_list = update_elem_info_list(out_sub, elem_info_list)

        # creating a new module type:
        file_mod_tid = type.new_module_type(tuple(elem_info_list))
        out_sub = out_sub.compose(substitution.Substitution({seeded_file_mod_exp_tid: file_mod_tid}))

        # applying the substitution:
        file_mod_tid = out_sub.rewrite_type(file_mod_tid)
        rewrite_system_with_sub(
            project,
            any_ctx=file_mod_ctx,
            deferred_list=deferred_list,
            rw_sub=out_sub
        )

        # finalizing type data:
        file_mod_ses = SES.Tot
        file_mod_cs = CS.No
        file_mod_exp.finalize_type_info(file_mod_tid, file_mod_ses, file_mod_cs, file_mod_ctx)

        # updating caches (including seeded values, called re-seeding):
        # NOTE: re-seeding is 'unsafe', but much more efficient than creating a copy map.
        # THUS, both the original and new TIDs correctly map to the correct file-mod-exp.
        file_mod_inferences[file_mod_exp] = FileModTypeInferenceInfo(file_mod_tid, out_sub)
        seeding.mod_tid_exp_map[file_mod_tid] = file_mod_exp

        return out_sub, file_mod_tid


def infer_sub_mod_exp_tid(
        project: "frontend.Project",
        sub_mod_exp: "ast.node.SubModExp",
        deferred_list: "deferred.DeferredList"
) -> t.Tuple[substitution.Substitution, type.identity.TID]:
    # acquiring the seeded context, updating our caches:
    seeded_sub_mod_exp_tid = seeding.mod_exp_tid_map[sub_mod_exp]
    sub_mod_ctx = seeding.mod_context_map[sub_mod_exp]

    out_sub = substitution.empty

    elem_info_list: t.List[type.elem.ElemInfo] = []

    for elem in sub_mod_exp.table.ordered_value_imp_bind_elems:
        assert isinstance(elem, ast.node.BaseBindElem)
        opt_ses, cs, elem_sub = infer_binding_elem_types(
            project, sub_mod_ctx, deferred_list,
            elem, True, elem_info_list
        )
        out_sub = elem_sub.compose(out_sub)
        # ignoring CS:
        # if not NO, must be a function that requires closures.
        # if a function requires closures, it must be for a nested function, since as a sub-module element,
        #   it is global and cannot have any closed elements.

    for elem in sub_mod_exp.table.ordered_type_bind_elems:
        opt_ses, cs, elem_sub = infer_binding_elem_types(
            project, sub_mod_ctx, deferred_list,
            elem, True, elem_info_list
        )
        out_sub = elem_sub.compose(out_sub)

    for elem in sub_mod_exp.table.ordered_typing_elems:
        elem_sub = infer_typing_elem_types(project, sub_mod_ctx, deferred_list, elem)
        out_sub = elem_sub.compose(out_sub)

    # re-applying the latest substitution to all elements but the last:
    # - NOTE: this involves replacing the `elem_info_list` list
    elem_info_list = update_elem_info_list(out_sub, elem_info_list)

    sub_mod_exp_tid = type.new_module_type(tuple(elem_info_list))
    out_sub = out_sub.compose(substitution.Substitution({seeded_sub_mod_exp_tid: sub_mod_exp_tid}))
    # sub_mod_exp_tid = out_sub.rewrite_type(sub_mod_exp_tid)

    # finalizing type data:
    sub_mod_exp_ses = SES.Tot
    sub_mod_exp_cs = CS.No
    sub_mod_exp.finalize_type_info(sub_mod_exp_tid, sub_mod_exp_ses, sub_mod_exp_cs, sub_mod_ctx)

    # re-seeding the new sub_mod's TID:
    seeding.mod_tid_exp_map[sub_mod_exp_tid] = sub_mod_exp

    return out_sub, sub_mod_exp_tid


def update_elem_info_list(out_sub, elem_info_list):
    # re-applying the latest substitution to all elements but the last:
    # - NOTE: this involves replacing the `elem_info_list` list
    if elem_info_list:
        old_elem_info_list = elem_info_list
        elem_info_list = []

        for i in range(len(old_elem_info_list) - 1):
            old_elem_info = old_elem_info_list[i]
            rw_tid = out_sub.rewrite_type(old_elem_info.tid)
            elem_info_list.append(
                type.elem.ElemInfo(
                    old_elem_info.name,
                    rw_tid,
                    old_elem_info.is_type_field
                )
            )

        elem_info_list.append(old_elem_info_list[-1])

    return elem_info_list


def infer_binding_elem_types(
        project: "frontend.Project",
        ctx: "context.Context",
        deferred_list: "deferred.DeferredList",
        elem: "ast.node.BaseBindElem",
        is_bound_globally_visible: bool,
        opt_elem_info_list: t.Optional[t.List[type.elem.ElemInfo]]
) -> t.Tuple[t.Optional[SES], CS, substitution.Substitution]:

    if isinstance(elem, (ast.node.Bind1VElem, ast.node.Bind1TElem)):
        if isinstance(elem, ast.node.Bind1VElem):
            sub, rhs_tid, opt_rhs_ses, rhs_cs = infer_exp_tid(
                project, ctx, deferred_list,
                elem.bound_exp
            )
            du = definition.Universe.Value
            is_type_field = False
        else:
            assert isinstance(elem, ast.node.Bind1TElem)
            assert elem.bound_type_spec is not None
            sub, rhs_tid = infer_type_spec_tid(
                project, ctx, deferred_list,
                elem.bound_type_spec
            )
            opt_rhs_ses = None
            rhs_cs = CS.No
            du = definition.Universe.Type
            is_type_field = True

        lhs_def_obj = ctx.lookup(elem.id_name, shallow=True)
        if lhs_def_obj is not None:
            def_sub = unify_existing_def(project, ctx, deferred_list, lhs_def_obj, rhs_tid, sub)
            sub = def_sub.compose(sub)
        else:
            # un-seeded: bound inside a chain.
            # we must define a new symbol

            id_name = elem.id_name
            def_tid = rhs_tid

            # defining the bound symbol using `set_tid`
            if du == definition.Universe.Value:
                def_rec = definition.ValueRecord(
                    project,
                    id_name, elem.loc, def_tid,
                    opt_func=ctx.opt_func,
                    is_bound_globally_visible=is_bound_globally_visible,
                    def_is_bound_var=False
                )
            elif du == definition.Universe.Type:
                def_rec = definition.TypeRecord(
                    project,
                    id_name, elem.loc, def_tid,
                    opt_func=ctx.opt_func,
                    is_bound_globally_visible=is_bound_globally_visible,
                    def_is_bound_var=False
                )
            else:
                raise NotImplementedError("Unknown universe in binding")

            def_ok = ctx.try_define(id_name, def_rec)
            if not def_ok:
                msg_suffix = f"definition `{id_name}` clashes with another definition in this scope."
                raise excepts.TyperCompilationError(msg_suffix)

            # no substitutions generated-- we're all done.

        # sub.rewrite_contexts_everywhere(ctx)
        # rhs_tid = sub.rewrite_type(rhs_tid)

        # appending to the `ElemInfo` list to construct fields:
        if opt_elem_info_list is not None:
            elem_info = type.elem.ElemInfo(elem.id_name, rhs_tid, is_type_field)
            opt_elem_info_list.append(elem_info)

        # return bound TID, closure-spec, and optionally SES
        return opt_rhs_ses, rhs_cs, sub

    else:
        raise NotImplementedError(f"Unknown elem type: {elem.__class__.__name__}")


def infer_imp_elem_types(
        project: "frontend.Project",
        ctx: "context.Context",
        deferred_list: "deferred.DeferredList",
        elem: "ast.node.BaseImperativeElem"
) -> t.Tuple[type.identity.TID, SES, CS, substitution.Substitution]:
    if isinstance(elem, ast.node.ForceEvalElem):
        sub, exp_tid, exp_ses, exp_cs = infer_exp_tid(
            project, ctx, deferred_list,
            elem.discarded_exp
        )
        # sub.rewrite_contexts_everywhere(ctx)
        return exp_tid, exp_ses, exp_cs, sub
    else:
        raise NotImplementedError(f"Unknown elem type: {elem.__class__.__name__}")


def infer_typing_elem_types(
        project: "frontend.Project",
        ctx: "context.Context",
        deferred_list: "deferred.DeferredList",
        elem: "ast.node.BaseTypingElem"
) -> substitution.Substitution:
    if isinstance(elem, ast.node.Type1VElem):
        sub, rhs_tid = infer_type_spec_tid(
            project, ctx, deferred_list,
            elem.type_spec
        )

        # since binding elements are always processed before typing elements, we can
        # assume any used symbols are in this context.
        # NOTE: in order to type formal args, we need to allow searching in a non-shallow way.
        #       we should generate a warning if query depth > 1, with an exception for formal args
        #       at depth 2 (since formal args are defined in their own shell-context)
        lhs_def_obj = ctx.lookup(elem.id_name)
        if lhs_def_obj is not None:
            def_sub = unify_existing_def(project, ctx, deferred_list, lhs_def_obj, rhs_tid, sub)
            sub = def_sub.compose(sub)
        else:
            msg_suffix = f"cannot type undefined symbol {elem.id_name}"
            raise excepts.TyperCompilationError(msg_suffix)

        instantiate_sub, lhs_tid = lhs_def_obj.scheme.shallow_instantiate()
        sub = instantiate_sub.compose(sub)

        unify_sub = unifier.unify_tid(lhs_tid, rhs_tid)
        sub = unify_sub.compose(sub)

        # sub.rewrite_contexts_everywhere(ctx)
        return sub

    else:
        raise NotImplementedError("Typing any BaseTypingElem")


def unify_existing_def(project, ctx, deferred_list, lhs_def_obj, new_def_tid, sub) -> substitution.Substitution:
    # NOTE: since this ID is pre-seeded, we do not need to instantiate the scheme, rather unify body directly.
    assert not lhs_def_obj.scheme.bound_vars
    sub = sub.get_scheme_body_sub_without_bound_vars(lhs_def_obj.scheme)

    # NOTE: the existing def can be immutable: internally promoted to mutable by unifier
    # NOTE: directly access body_tid to avoid instantiating free vars
    old_def_tid = lhs_def_obj.scheme.body_tid
    unify_sub = unifier.unify_tid(old_def_tid, new_def_tid, allow_u_mut_ptr=True)
    sub = sub.compose(unify_sub)

    # NOTE: we need to rewrite contexts as soon as unifying definitions to avoid multiple subs of an old seed
    #   - sub composition cannot handle such divergent mappings
    #   - this may rewrite `old_def_tid`
    rewrite_system_with_sub(project, ctx, deferred_list, sub)

    # replacing existing def with better version if relevant:
    #   - functions with `AnyNonTot` SES should be eliminated if possible in favor of a non-TOT side-effects specifier.
    #   - functions with `MaybeClosure` should be eliminated if possible in favor of `Yes` or `No`
    # FIXME: this needs to work recursively on compounds of functions, e.g. Modules
    new_def_tid = sub.rewrite_type(new_def_tid)
    new_def_tk = type.kind.of(new_def_tid)
    old_def_tid = lhs_def_obj.scheme.body_tid
    old_def_tk = type.kind.of(old_def_tid)

    if old_def_tk == new_def_tk == type.kind.TK.Fn:
        #
        # Comparing SES:
        #

        new_def_ses = type.side_effects.of(new_def_tid)
        old_def_ses = type.side_effects.of(old_def_tid)

        new_def_ses_is_better = (
            new_def_ses not in (SES.Elim_AnyNonTot, SES.Elim_Any) and
            old_def_ses in (SES.Elim_AnyNonTot, SES.Elim_Any)
        )
        #
        # Comparing CS (ClosureSpec):
        #

        new_def_cs = type.closure_spec.of(new_def_tid)
        old_def_cs = type.closure_spec.of(old_def_tid)

        new_def_cs_is_better = (
            old_def_cs == CS.Maybe and
            new_def_cs != CS.Maybe
        )

        #
        # Collating, maybe replacing context def:
        #

        if new_def_ses_is_better or new_def_cs_is_better:
            lhs_def_obj.scheme.body_tid = new_def_tid

        # TODO: update the `Module` type as well

    return sub


def infer_exp_tid(
        project: "frontend.Project",
        ctx: "context.Context",
        deferred_list: "deferred.DeferredList",
        exp: "ast.node.BaseExp"
) -> t.Tuple[substitution.Substitution, type.identity.TID, SES, CS]:

    sub, tid, ses, cs = help_infer_exp_tid(project, ctx, deferred_list, exp)
    exp.finalize_type_info(tid, ses, cs, ctx)
    return sub, tid, ses, cs


def help_infer_exp_tid(
        project: "frontend.Project",
        ctx: "context.Context",
        deferred_list: "deferred.DeferredList",
        exp: "ast.node.BaseExp"
) -> t.Tuple[substitution.Substitution, type.identity.TID, SES, CS]:
    # context-dependent branches: ID, ModAddressID
    if isinstance(exp, ast.node.IdExp):
        found_def_obj = ctx.lookup(exp.name)

        # ensuring the definition exists:
        if found_def_obj is None:
            raise excepts.TyperCompilationError(f"Symbol `{exp.name}` used but not defined.")

        # ensuring the definition is in the right universe (not a module)
        du = names.infer_def_universe_of(exp.name)
        if du != definition.Universe.Value:
            raise excepts.TyperCompilationError(
                f"Symbol {exp.name} is not defined in the 'Value' universe. Are you missing a `:` suffix?"
            )
        assert isinstance(found_def_obj, definition.ValueRecord)

        # storing the found definition on the ID:
        exp.found_def_rec = found_def_obj

        # SES is always `Tot` for a `load` operation:
        call_ses = SES.Tot

        if found_def_obj.is_bound_globally_visible:
            # found def is a global ID. No closure required.
            closure_spec = CS.No

            # adding this ID to the function's global enclosed set
            if ctx.opt_func is not None:
                ctx.opt_func.add_global_id_ref(exp.name, found_def_obj)
        else:
            # found def is defined inside a function or a global IIFE.

            # checking if the accessed ID is in the same function as us, or a higher one (in which case, this is a
            # non-local ID)
            id_is_closure = ctx.opt_func != found_def_obj.opt_container_func
            if not id_is_closure:
                closure_spec = CS.No
            else:
                closure_spec = CS.Yes

                # adding this ID to the function's nonlocal enclosed set
                if ctx.opt_func is not None:
                    ctx.opt_func.add_non_local_id_ref(exp.name, found_def_obj)

        # returning:
        ret_sub, def_tid = found_def_obj.scheme.shallow_instantiate()
        return ret_sub, def_tid, call_ses, closure_spec

    elif isinstance(exp, ast.node.IdExpInModule):
        sub, tid, ses, cs = help_type_id_in_module_node(
            project, ctx, deferred_list,
            exp.data,
            definition.Universe.Value
        )
        return sub, tid, ses, cs

    #
    # context-independent branches:
    #

    elif isinstance(exp, ast.node.UnitExp):
        return (
            substitution.empty,
            type.get_unit_type(),
            SES.Tot,
            CS.No
        )

    elif isinstance(exp, ast.node.StringExp):
        return (
            substitution.empty,
            type.get_str_type(),
            SES.Tot,
            CS.No
        )

    elif isinstance(exp, ast.node.NumberExp):
        # FIXME: the type module truncates single-bit variables by only storing byte-count.

        default_number_width_in_bits = 32

        if exp.width_in_bits is None:
            width_in_bits = default_number_width_in_bits
        else:
            width_in_bits = exp.width_in_bits

        if exp.is_float:
            return (
                substitution.empty,
                type.get_float_type(width_in_bits),
                SES.Tot,
                CS.No
            )

        elif exp.is_unsigned_int:
            return (
                substitution.empty,
                type.get_int_type(width_in_bits, is_unsigned=True),
                SES.Tot,
                CS.No
            )
        else:
            assert exp.is_signed_int
            return (
                substitution.empty,
                type.get_int_type(width_in_bits, is_unsigned=False),
                SES.Tot,
                CS.No
            )

    elif isinstance(exp, ast.node.PostfixVCallExp):
        ret_tid = type.new_free_var(f"fn-call")

        s1, formal_fn_tid, fn_exp_ses, fn_cs = infer_exp_tid(
            project, ctx, deferred_list,
            exp.called_exp
        )

        s2, formal_arg_tid, arg_exp_ses, arg_cs = infer_exp_tid(
            project, ctx, deferred_list,
            exp.arg_exp
        )
        formal_arg_tid = s1.rewrite_type(formal_arg_tid)

        s12 = s2.compose(s1)

        call_ses = SES.Elim_AnyNonTot if exp.has_se else SES.Tot

        closure_spec = type.closure_spec.of(formal_fn_tid)

        actual_fn_tid = type.get_fn_type(formal_arg_tid, ret_tid, call_ses, closure_spec)
        actual_fn_tid = s12.rewrite_type(actual_fn_tid)

        s3 = unifier.unify_tid(actual_fn_tid, formal_fn_tid)

        s123 = s3.compose(s12)
        ret_tid = s123.rewrite_type(ret_tid)

        # checking that '!' used with formal definitions of the right side-effects specifier:
        formal_ses = type.side_effects.of(formal_fn_tid)
        elim_formal_ses = formal_ses in (
            type.side_effects.SES.Elim_Any,
            type.side_effects.SES.Elim_AnyNonTot
        )

        formal_ses_is_tot = (formal_ses == SES.Tot)
        call_ses_is_tot = (call_ses == SES.Tot)
        elim_call_ses = call_ses in (
            type.side_effects.SES.Elim_Any,
            type.side_effects.SES.Elim_AnyNonTot
        )
        if not elim_formal_ses and not elim_call_ses:
            if formal_ses_is_tot and not call_ses_is_tot:
                msg_suffix = "Total function called with '!' specifier"
                raise excepts.TyperCompilationError(msg_suffix)
            elif not formal_ses_is_tot and call_ses_is_tot:
                msg_suffix = "Non-total function must be called with a '!' specifier"
                raise excepts.TyperCompilationError(msg_suffix)
        elif elim_formal_ses and not elim_call_ses:
            fn_exp_ses = unifier.unify_ses(fn_exp_ses, call_ses)
        elif elim_call_ses and not elim_formal_ses:
            fn_exp_ses = unifier.unify_ses(fn_exp_ses, formal_ses)

        exp_ses = unifier.unify_ses(call_ses, fn_exp_ses, arg_exp_ses)

        exp_cs = unifier.unify_closure_spec(fn_cs, arg_cs)

        return s123, ret_tid, exp_ses, exp_cs

    elif isinstance(exp, ast.node.CastExp):
        s1, src_tid, exp_ses, exp_cs = infer_exp_tid(
            project, ctx, deferred_list,
            exp.initializer_data
        )
        s2, dst_tid = infer_type_spec_tid(
            project, ctx, deferred_list,
            exp.constructor_ts
        )
        dst_tid = s1.rewrite_type(dst_tid)
        ret_sub = s1.compose(s2)

        # use a DeferredOrder to check that the cast operation will succeed
        deferred_list.add(deferred.TypeCastDeferredOrder(exp.loc, dst_tid, src_tid))

        # all OK!
        return ret_sub, ret_sub.rewrite_type(dst_tid), exp_ses, exp_cs

    elif isinstance(exp, ast.node.LambdaExp):
        # each lambda gets its own scope (for formal args)
        lambda_ctx = ctx.push_context(f"lambda-{exp.loc}", exp.loc, opt_func=exp)

        # inferring the 'arg_tid':
        # NOTE: arg kind depends on arg count:
        # - if 0 args, arg kind is unit
        # - if 2 or more args, arg kind is tuple
        # - if 1 arg, arg type is just that arg's type.
        if not exp.arg_names:
            formal_arg_tid = type.get_unit_type()
        else:
            elem_arg_tid_list = []
            for i, arg_name in enumerate(exp.arg_names):
                # creating the formal arg TID:
                formal_arg_tid = type.new_free_var(f"lambda-formal-arg:{arg_name}")

                # defining the formal arg in the function context:
                arg_def_obj = definition.ValueRecord(
                    project,
                    arg_name, exp.loc, formal_arg_tid,
                    opt_func=exp,
                    is_bound_globally_visible=False,
                    def_is_bound_var=False
                )
                formal_arg_def_ok = lambda_ctx.try_define(arg_name, arg_def_obj)
                if not formal_arg_def_ok:
                    msg_suffix = f"lambda formal arg #{i}: `{arg_name}` clashes with a prior definition in this scope."
                    raise excepts.TyperCompilationError(msg_suffix)

                elem_arg_tid_list.append(formal_arg_tid)

            assert elem_arg_tid_list
            if len(elem_arg_tid_list) == 1:
                formal_arg_tid = elem_arg_tid_list[0]
            else:
                formal_arg_tid = type.get_tuple_type(tuple(elem_arg_tid_list))

        assert formal_arg_tid is not None

        # inferring the 'ret_tid', 'closure_spec', and return 'val_var' from the body expression:
        ret_sub, ret_tid, ret_ses, closure_spec = infer_exp_tid(
            project, lambda_ctx, deferred_list,
            exp.body
        )
        exp.finalize_fn_ses(ret_ses)

        # if `closure_spec` is `No`, changing to `Maybe` so we can unify with both kinds of functions.
        #   - `Maybe` indicates an empty set of non-locals
        if closure_spec == CS.No:
            fn_closure_spec = CS.Maybe
        else:
            fn_closure_spec = closure_spec

        # now, the type of the lambda is the type of the function that accepts the given args and returns the specified
        # return expression:
        fn_tid = type.get_fn_type(formal_arg_tid, ret_tid, ret_ses, fn_closure_spec)

        # we return `closure_spec` because...
        #   - if this func is `NoClosure`, but the returned body needs closures to work (e.g. in currying),
        #     this func cannot be called.
        #   - `NoClosure` functions must be safe to call in C, where we do not have closures.

        return ret_sub, fn_tid, SES.Tot, closure_spec

    # typing chain expressions:
    elif isinstance(exp, ast.node.ChainExp):
        chain_ctx = ctx.push_context("chain-ctx", exp.loc)
        sub = substitution.empty
        expected_ses = exp.opt_prefix_es if exp.opt_prefix_es is not None else SES.Tot
        output_cs = CS.No

        if exp.table.elements:
            # first, effecting binding and imperative elements in order:
            #   - this ensures that initialization orders are correct
            for elem_index, elem in enumerate(exp.table.ordered_value_imp_bind_elems):
                if isinstance(elem, ast.node.Bind1VElem):
                    exp_ses, exp_cs, exp_sub = infer_binding_elem_types(
                        project,
                        chain_ctx,
                        deferred_list,
                        elem,
                        is_bound_globally_visible=False,
                        opt_elem_info_list=None
                    )
                    assert exp_ses is not None
                    sub = exp_sub.compose(sub)
                    output_cs = unifier.unify_closure_spec(output_cs, exp_cs)
                else:
                    assert isinstance(elem, ast.node.BaseImperativeElem)
                    ret_tid, exp_ses, exp_cs, exp_sub = infer_imp_elem_types(
                        project, chain_ctx, deferred_list,
                        elem
                    )
                    sub = exp_sub.compose(sub)
                    output_cs = unifier.unify_closure_spec(output_cs, exp_cs)

                if exp_ses is not None:
                    if not unifier.compare_ses(expected_ses, exp_ses):
                        raise excepts.TyperCompilationError(f"element #{1+elem_index} violates SES for chain")
                    expected_ses = unifier.unify_ses(exp_ses, expected_ses)

            # then, defining each type binding element:
            for elem in exp.table.ordered_type_bind_elems:
                opt_ses, elem_cs, elem_sub = infer_binding_elem_types(
                    project,
                    chain_ctx,
                    deferred_list,
                    elem,
                    is_bound_globally_visible=False,
                    opt_elem_info_list=None
                )
                assert opt_ses is None
                assert elem_cs == CS.No
                sub = elem_sub.compose(sub)

            # then, effecting each 'typing' element:
            for elem in exp.table.ordered_typing_elems:
                infer_typing_elem_types(project, chain_ctx, deferred_list, elem)

        if exp.opt_tail is not None:
            tail_sub, tail_tid, tail_ses, tail_cs = infer_exp_tid(
                project, chain_ctx, deferred_list,
                exp.opt_tail
            )
            sub = tail_sub.compose(sub)

            # checking SES:
            if not unifier.compare_ses(expected_ses, tail_ses):
                raise excepts.TyperCompilationError(f"tail expression violates SES for chain")
            expected_ses = unifier.unify_ses(expected_ses, tail_ses)

            # checking CS:
            output_cs = unifier.unify_closure_spec(output_cs, tail_cs)

        else:
            tail_tid = type.get_unit_type()

        return sub, tail_tid, expected_ses, output_cs

    # typing unary, binary expressions:
    elif isinstance(exp, ast.node.UnaryExp):
        arg_exp_sub, arg_exp_tid, arg_exp_ses, arg_exp_cs = infer_exp_tid(
            project,
            ctx,
            deferred_list,
            exp.arg_exp
        )

        # NOTE: we cannot resolve this typing immediately since we need to overload/dispatch based on the type of
        #       the argument.
        # NOTE: instead, add a deferred order.
        ret_tid = type.new_free_var("unary_exp_ret")

        deferred_list.add(deferred.UnaryOpDeferredOrder(
            exp.loc,
            exp.unary_op,
            arg_exp_tid,
            ret_tid
        ))

        return arg_exp_sub, ret_tid, arg_exp_ses, arg_exp_cs

    elif isinstance(exp, ast.node.BinaryExp):
        sub = substitution.empty

        lt_arg_sub, lt_arg_tid, lt_arg_ses, lt_arg_cs = infer_exp_tid(
            project, ctx, deferred_list,
            exp.lt_arg_exp
        )
        sub = lt_arg_sub.compose(sub)

        rt_arg_sub, rt_arg_tid, rt_arg_ses, rt_arg_cs = infer_exp_tid(
            project, ctx, deferred_list,
            exp.rt_arg_exp
        )
        sub = rt_arg_sub.compose(sub)

        # NOTE: we can consider adding short-hands for immediate typing resolution
        #       (rather than using the DeferredOrder system)

        ret_tid = type.new_free_var(f"binary_exp_ret")
        binary_exp_ses = unifier.unify_ses(lt_arg_ses, rt_arg_ses)  # U SES.Tot (all bin ops)
        binary_exp_cs = unifier.unify_closure_spec(lt_arg_cs, rt_arg_cs)

        # since we cannot resolve type overloads immediately, we add a DeferredOrder to resolve it:
        deferred_list.add(deferred.BinaryOpDeferredOrder(
            exp.loc,
            exp.binary_op,
            lt_arg_tid, rt_arg_tid, ret_tid
        ))

        return sub, ret_tid, binary_exp_ses, binary_exp_cs

    # typing AssignExp:
    elif isinstance(exp, ast.node.AssignExp):
        ptd_tid = type.new_free_var("assign.ptd")
        ptr_tid = type.get_ptr_type(ptd_tid, True)

        sub = substitution.empty

        val_exp_sub, val_exp_tid, val_exp_ses, val_exp_cs = infer_exp_tid(
            project, ctx, deferred_list,
            exp.src_exp
        )
        sub = val_exp_sub.compose(sub)

        arg_exp_sub, arg_exp_tid, arg_exp_ses, ptr_exp_cs = infer_exp_tid(
            project, ctx, deferred_list,
            exp.dst_exp
        )
        sub = arg_exp_sub.compose(sub)

        unify_sub_1 = unifier.unify_tid(ptr_tid, arg_exp_tid)
        sub = unify_sub_1.compose(sub)
        unify_sub_2 = unifier.unify_tid(ptd_tid, val_exp_tid)
        sub = unify_sub_2.compose(sub)

        exp_cs = unifier.unify_closure_spec(val_exp_cs, ptr_exp_cs)

        spec_ses = SES.Tot if exp.is_tot else SES.ST
        assign_ses = unifier.unify_ses(
            spec_ses,
            val_exp_ses,
            arg_exp_ses
        )

        return sub, ptd_tid, assign_ses, exp_cs

    # typing memory windows:
    elif isinstance(exp, (ast.node.AllocatePtrExp, ast.node.AllocateArrayExp, ast.node.AllocateSliceExp)):
        alloc_ses = {
            ast.node.Allocator.Stack: SES.Tot,
            ast.node.Allocator.Heap: SES.ML
        }[exp.allocator]

        # TODO: verify that `push` only invoked in a function: check ctx.opt_func

        if isinstance(exp, ast.node.AllocatePtrExp):
            initializer_sub, ptd_tid, initializer_ses, initializer_cs = infer_exp_tid(
                project,
                ctx,
                deferred_list,
                exp.initializer_exp
            )
            ptr_tid = type.get_ptr_type(ptd_tid, exp.is_mut)
            ptr_ses = unifier.unify_ses(initializer_ses, alloc_ses)
            return initializer_sub, ptr_tid, ptr_ses, initializer_cs

        else:
            assert isinstance(exp, (ast.node.AllocateArrayExp, ast.node.AllocateSliceExp))

            sub = substitution.empty
            ses = SES.Tot
            cs = CS.No

            # analyzing the type-spec for each element:
            ts_sub, ptd_ts_tid = infer_type_spec_tid(
                project,
                ctx,
                deferred_list,
                exp.collection_ts
            )
            sub = ts_sub.compose(sub)

            # unifying initializer:
            if exp.opt_initializer_exp is not None:
                initializer_sub, ptd_tid, initializer_ses, initializer_cs = infer_exp_tid(
                    project,
                    ctx,
                    deferred_list,
                    exp.opt_initializer_exp
                )
                unify_sub = unifier.unify_tid(ptd_ts_tid, ptd_tid)
                sub = unify_sub.compose(sub)
                ses = unifier.unify_ses(ses, initializer_ses)
                cs = unifier.unify_closure_spec(cs, initializer_cs)

            # ensuring the 'count' component is an unsigned int:
            assert exp.array_size_exp is not None
            array_size_sub, array_size_tid, array_size_ses, array_size_cs = infer_exp_tid(
                project,
                ctx,
                deferred_list,
                exp.array_size_exp
            )

            # creating the array/slice TID from the pointed value:
            if isinstance(exp, ast.node.AllocateArrayExp):
                mem_window_tid = type.get_array_type(ptd_ts_tid, array_size_tid, exp.is_mut)
            else:
                assert isinstance(exp, ast.node.AllocateSliceExp)
                mem_window_tid = type.get_slice_type(ptd_ts_tid, array_size_tid, exp.is_mut)

            # TODO: verify that the index type is an unsigned int
            #   - use a 'deferred' comparison similar to type conversion

            return sub, mem_window_tid, ses, cs

    # typing IfExp:
    elif isinstance(exp, ast.node.IfExp):
        ret_tid = type.new_free_var("ite")

        sub = substitution.empty
        ses = type.side_effects.SES.Tot
        cs = type.closure_spec.CS.No

        def unify_branch_exp(branch_exp):
            nonlocal sub, ses, cs
            branch_exp_sub, branch_exp_tid, branch_exp_ses, branch_exp_cs = infer_exp_tid(
                project,
                ctx,
                deferred_list,
                branch_exp
            )
            sub = branch_exp_sub.compose(sub)
            ses = unifier.unify_ses(ses, branch_exp_ses)
            cs = unifier.unify_closure_spec(cs, branch_exp_cs)

            branch_unify_sub = unifier.unify_tid(branch_exp_tid, ret_tid)
            sub = branch_unify_sub.compose(sub)

        cond_exp_sub, cond_exp_tid, cond_exp_ses, cond_exp_cs = infer_exp_tid(
            project,
            ctx,
            deferred_list,
            exp.cond_exp
        )
        sub = cond_exp_sub.compose(sub)
        ses = unifier.unify_ses(ses, cond_exp_ses)
        cs = unifier.unify_closure_spec(cs, cond_exp_cs)

        cond_unify_sub = unifier.unify_tid(cond_exp_tid, type.get_int_type(1, is_unsigned=True))
        sub = cond_unify_sub.compose(sub)

        unify_branch_exp(exp.then_exp)

        if exp.opt_else_exp is not None:
            unify_branch_exp(exp.opt_else_exp)

        return sub, ret_tid, ses, cs

    # typing TupleExp
    elif isinstance(exp, ast.node.TupleExp):
        out_sub = substitution.empty
        out_ses = SES.Tot
        out_cs = CS.Maybe

        elem_tid_list = []

        for item_exp in exp.items:
            item_sub, item_tid, item_ses, item_cs = infer_exp_tid(project, ctx, deferred_list, item_exp)
            out_sub = item_sub.compose(out_sub)
            out_ses = unifier.unify_ses(item_ses, out_ses)
            out_cs = unifier.unify_closure_spec(item_cs, out_cs)
            elem_tid_list.append(item_tid)

        return out_sub, type.get_tuple_type(tuple(elem_tid_list)), out_ses, out_cs

    # typing GetElementByDot{Index|Name}Exp
    elif isinstance(exp, ast.node.GetElementByDotIndexExp):
        container_sub, container_tid, container_ses, container_cs = infer_exp_tid(
            project, ctx, deferred_list, exp.container
        )

        index_exp = exp.index
        assert isinstance(index_exp, ast.node.NumberExp)
        index_int = int(index_exp.value_text)

        proxy_ret_tid = type.new_free_var(f"proxy_for_dot_index_exp")

        deferred_order = deferred.DotIndexOpDeferredOrder(
            exp.loc,
            container_tid,
            index_int,
            proxy_ret_tid
        )
        deferred_list.add(deferred_order)

        return container_sub, proxy_ret_tid, container_ses, container_cs

    elif isinstance(exp, ast.node.GetElementByDotNameExp):
        container_sub, container_tid, container_ses, container_cs = infer_exp_tid(
            project, ctx, deferred_list, exp.container
        )

        field_name = exp.key_name
        assert isinstance(field_name, str)

        proxy_ret_tid = type.new_free_var(f"proxy_for_dot_name_exp")

        deferred_list.add(
            deferred_order=deferred.DotNameOpDeferredOrder(
                exp.loc,
                container_tid,
                field_name,
                proxy_ret_tid
            )
        )

        return container_sub, proxy_ret_tid, container_ses, container_cs

    else:
        raise NotImplementedError(f"Type inference for {exp.__class__.__name__}")


def infer_type_spec_tid(
        project: "frontend.Project",
        ctx: "context.Context",
        deferred_list: "deferred.DeferredList",
        ts: "ast.node.BaseTypeSpec"
):
    sub, tid = help_infer_type_spec_tid(project, ctx, deferred_list, ts)
    ts.finalize_type_info(tid, SES.Tot, CS.No, ctx)
    return sub, tid


def help_infer_type_spec_tid(
        project: "frontend.Project",
        ctx: "context.Context",
        deferred_list: "deferred.DeferredList",
        ts: "ast.node.BaseTypeSpec"
) -> t.Tuple[substitution.Substitution, type.identity.TID]:
    if isinstance(ts, ast.node.IdTypeSpec):
        # looking up the definition:
        found_def_obj = ctx.lookup(ts.name)

        # validating found, universe:
        if found_def_obj is None:
            msg_suffix = f"TypeID {ts.name} used but not defined."
            raise excepts.TyperCompilationError(msg_suffix)
        elif found_def_obj.universe != definition.Universe.Type:
            msg_suffix = f"TypeID {ts.name} not in valid universe in this context."
            raise excepts.TyperCompilationError(msg_suffix)

        # storing found def_rec for later:
        ts.found_def_rec = found_def_obj

        # returning:
        sub, def_tid = found_def_obj.scheme.shallow_instantiate()
        return sub, def_tid

    elif isinstance(ts, ast.node.UnitTypeSpec):
        return substitution.empty, type.get_unit_type()

    elif isinstance(ts, ast.node.FnSignatureTypeSpec):
        lhs_ts = ts.arg_type_spec
        rhs_ts = ts.return_type_spec
        if ts.opt_ses is not None:
            ses = ts.opt_ses
        else:
            # default SES: `Tot`
            ses = SES.Tot

        sub = substitution.empty

        lhs_sub, lhs_tid = infer_type_spec_tid(
            project, ctx, deferred_list,
            lhs_ts
        )
        sub = lhs_sub.compose(sub)

        rhs_sub, rhs_tid = infer_type_spec_tid(
            project, ctx, deferred_list,
            rhs_ts
        )
        sub = rhs_sub.compose(sub)

        cs = ts.closure_spec

        fn_tid = type.get_fn_type(lhs_tid, rhs_tid, ses, cs)

        return sub, fn_tid

    elif isinstance(ts, ast.node.AdtTypeSpec):
        type_ctor = {
            ast.node.AdtKind.Structure: type.get_struct_type,
            ast.node.AdtKind.Union: type.get_union_type
        }[ts.adt_kind]

        sub = substitution.empty
        field_elem_info_list = []
        for field_name, field_type_spec_elem_list in ts.table.typing_elems_map.items():
            if len(field_type_spec_elem_list) == 1:
                field_type_spec_elem = field_type_spec_elem_list[0]
                assert isinstance(field_type_spec_elem, ast.node.Type1VElem)
                field_sub, field_tid = infer_type_spec_tid(
                    project,
                    ctx,
                    deferred_list,
                    field_type_spec_elem.type_spec
                )
                sub = field_sub.compose(sub)
            else:
                # TODO: consider generalizing this constraint to all tables.
                msg_suffix = f"cannot type the same ID multiple times in an ADT."
                raise excepts.TyperCompilationError(msg_suffix)

            elem_info = type.elem.ElemInfo(field_name, field_tid, False)
            field_elem_info_list.append(elem_info)

        field_elem_info_tuple = tuple(field_elem_info_list)
        adt_tid = type_ctor(field_elem_info_tuple)

        return sub, adt_tid

    elif isinstance(ts, ast.node.IdTypeSpecInModule):
        sub, tid, ses, cs = help_type_id_in_module_node(
            project,
            ctx,
            deferred_list,
            ts.data,
            definition.Universe.Type
        )

        assert ses == SES.Tot

        # ignore the closure-spec: if the value is not computable from constants, it will be caught in PTC-checks.

        return sub, tid

    elif isinstance(ts, ast.node.PtrTypeSpec):
        ptd_sub, ptd_tid = infer_type_spec_tid(project, ctx, deferred_list, ts.ptd_ts)
        ptr_tid = type.get_ptr_type(ptd_tid, ts.is_mut)
        return ptd_sub, ptr_tid

    elif isinstance(ts, ast.node.TupleTypeSpec):
        item_tid_list = []
        sub = substitution.empty
        for item_ts in ts.items:
            item_sub, item_tid = infer_type_spec_tid(project, ctx, deferred_list, item_ts)
            sub = item_sub.compose(sub)
            item_tid_list.append(item_tid)
        tuple_tid = type.get_tuple_type(tuple(item_tid_list))
        return sub, tuple_tid

    raise NotImplementedError(f"Type inference for {ts.__class__.__name__}")


def help_type_id_in_module_node(
        project: "frontend.Project",
        ctx: "context.Context",
        deferred_list: "deferred.DeferredList",
        data: "ast.node.IdNodeInModuleHelper",
        expect_du: definition.Universe
) -> t.Tuple[substitution.Substitution, type.identity.TID, SES, CS]:
    # NOTE: IdInModuleNodes are nested and share formal variable mappings THAT CANNOT LEAVE THIS SUB-SYSTEM.
    #   - this means that the substitution returns formal -> actual mappings UNLESS it has no child, in which case
    #     it is the last IdInModuleNode in the process.

    sub = substitution.empty
    out_cs = CS.No
    out_ses = SES.Tot

    # looking up `found_def_obj` referring to [a:]b in this exp:
    if data.opt_container is None:
        # the LHS is None, so the RHS must look up in the local context:
        file_mod_name = data.elem_name
        found_def_obj = ctx.lookup(file_mod_name)

        if found_def_obj is None:
            msg_suffix = f"symbol {file_mod_name} not found"
            raise excepts.TyperCompilationError(msg_suffix)

        # validating the found definition: must be a module since it has children.
        elif not isinstance(found_def_obj, definition.ModRecord):
            msg_suffix = f"expected {file_mod_name} to refer to a file-mod, not other"
            raise excepts.TyperCompilationError(msg_suffix)

        # validating the found definition as a non-bound-var:
        elif found_def_obj.is_bound_var_def_obj:
            msg_suffix = (
                f"cannot access formal argument by `:<name>`. "
                f"(if you really want to do this, please use an explicit alias)"
            )
            raise excepts.TyperCompilationError(msg_suffix)

        # by design, no node of this type can have no child.
        # this block is mostly setup for states encountered below.
        assert data.has_child

    else:
        assert data.opt_container is not None

        # we 'drill-down' through container-expressions until reaching the base-case above.
        # NOTE: this function uniquely returns a substitution with template formal args when it can guarantee it returns
        #       to itself, i.e. `data.has_child` is true.

        # getting a mod-exp for the container:
        container_sub, container_tid, container_ses, container_cs = help_type_id_in_module_node(
            project,
            ctx,
            deferred_list,
            data.opt_container,
            definition.Universe.Module
        )
        container_mod_exp = seeding.mod_tid_exp_map[container_tid]
        sub = sub.compose(container_sub)
        out_ses = unifier.unify_ses(out_ses, container_ses)
        out_cs = unifier.unify_closure_spec(out_cs, container_cs)
        container_ctx = seeding.mod_context_map[container_mod_exp]

        # looking up the element in the container:
        found_def_obj = container_ctx.lookup(data.elem_name, shallow=True)
        if found_def_obj is None:
            msg_suffix = f"element {data.elem_name} not found in existing module"
            raise excepts.TyperCompilationError(msg_suffix)

        # validating the found definition against the expected DU:
        if found_def_obj.universe != expect_du:
            msg_suffix = (
                f"element {data.elem_name} in the wrong universe: "
                f"found {found_def_obj.universe.name}, "
                f"expected {expect_du.name}"
            )
            raise excepts.TyperCompilationError(msg_suffix)

        # validating the found definition as a non-bound-var:
        if found_def_obj.is_bound_var_def_obj:
            msg_suffix = (
                f"cannot access formal argument by `:<name>`. "
                f"(if you really want to do this, please use an explicit alias)"
            )
            raise excepts.TyperCompilationError(msg_suffix)

    # instantiating the found definition's scheme, using actual arguments if provided:
    instantiated_scheme = found_def_obj.scheme
    if not data.elem_args:
        # no template arg call required/automatically instantiate:
        #   - note: we try using 'shallow' so that contextual args are mapped uniquely in children

        instantiation_sub, found_tid = instantiated_scheme.shallow_instantiate()

        # rewriting the type to the fullest extend possible:
        sub = sub.compose(instantiation_sub)
    else:
        # template args provided: must be matched against the definition.

        #
        # first, checking that the def of the called object actually points to a sub-module:
        #

        if not isinstance(found_def_obj, definition.ModRecord):
            msg = f"cannot use any ({len(data.elem_args)}) template args to instantiate a non-module definition"
            raise excepts.TyperCompilationError(msg)

        if not isinstance(found_def_obj.mod_exp, ast.node.SubModExp):
            msg = f"only submodules can accept template args"
            raise excepts.TyperCompilationError(msg)

        #
        # next, comparing definitions in the sub-module against the actual parameters received:
        #

        # checking arg counts:
        instantiated_mod_exp = found_def_obj.mod_exp
        instantiated_mod_ctx = seeding.mod_context_map[instantiated_mod_exp]
        expected_arg_count = len(instantiated_mod_exp.template_arg_names)
        actual_arg_count = len(data.elem_args)
        if expected_arg_count != actual_arg_count:
            msg = f"template argument count wrong: expected {expected_arg_count}, received {actual_arg_count}"
            raise excepts.TyperCompilationError(msg)

        arg_count = actual_arg_count
        assert arg_count == actual_arg_count == expected_arg_count

        # checking universes for actual-formal mismatches:
        # - in other words, ensuring values passed to value args, types to type args.
        # - also sifting arguments by universe to perform appropriate checks:
        actual_type_arg_tid_list = []
        mismatch_list = []
        zipped_args = zip(instantiated_mod_exp.template_arg_names, data.elem_args)
        for arg_index, (formal_name, actual_arg_node) in enumerate(zipped_args):
            name_universe = names.infer_def_universe_of(formal_name)
            if isinstance(actual_arg_node, ast.node.BaseExp):
                if name_universe != definition.Universe.Value:
                    mismatch_list.append(f"- arg #{arg_index}: expected type arg, received a value")
                else:
                    actual_arg_exp = actual_arg_node
                    actual_arg_sub, actual_arg_tid, actual_arg_ses, actual_arg_cs = infer_exp_tid(
                        project,
                        ctx,
                        deferred_list,
                        actual_arg_exp
                    )
                    sub = sub.compose(actual_arg_sub)

                    assert names.infer_def_universe_of(formal_name) == definition.Universe.Value
                    formal_val_def_obj = instantiated_mod_ctx.lookup(formal_name, shallow=True)
                    assert isinstance(formal_val_def_obj, definition.ValueRecord)
                    instantiate_sub, formal_value_arg_tid = formal_val_def_obj.scheme.shallow_instantiate()
                    sub = sub.compose(instantiate_sub)

                    # unifying value args:
                    this_val_arg_sub = unifier.unify_tid(
                        sub.rewrite_type(formal_value_arg_tid),
                        sub.rewrite_type(actual_arg_tid)
                    )
                    sub = sub.compose(this_val_arg_sub)

                    # ensuring SES is 'Tot'
                    if actual_arg_ses != SES.Tot:
                        msg_suffix = f"template arg #{1+arg_index} at {actual_arg_node.loc} must be `TOT`"
                        raise excepts.TyperCompilationError(msg_suffix)

                    # unifying CS:
                    out_cs = unifier.unify_closure_spec(out_cs, actual_arg_cs)
            else:
                assert isinstance(actual_arg_node, ast.node.BaseTypeSpec)
                if name_universe != definition.Universe.Type:
                    mismatch_list.append(f"- arg #{arg_index}: expected value arg, received a type")
                else:
                    assert isinstance(actual_arg_node, ast.node.BaseTypeSpec)
                    assert names.infer_def_universe_of(formal_name) == definition.Universe.Type

                    actual_arg_ts = actual_arg_node
                    actual_arg_sub, actual_type_arg_tid = infer_type_spec_tid(
                        project, ctx, deferred_list,
                        actual_arg_ts
                    )
                    sub = sub.compose(actual_arg_sub)

                    actual_type_arg_tid_list.append(actual_type_arg_tid)

        if mismatch_list:
            mismatch_text = '\n'.join(mismatch_list)
            msg_suffix = f"Mismatched template args:\n{mismatch_text}"
            raise excepts.TyperCompilationError(msg_suffix)

        #
        # instantiating the scheme using type args:
        # - unifies bound and actual type args (monomorphization)
        #

        # NOTE: `polymorphic_instantiate_sub` includes mappings from BoundVars.
        #       `monomorphic_instantiate_sub` includes mappings from FreeVars that instantiate/sub the BoundVars.

        instantiate_sub, found_tid = instantiated_scheme.deep_instantiate()

        # if args provided, unifying actuals with fresh free-vars above.
        # NOTE: before, when actual args were provided, we would unify the actual args with the BoundVar directly.
        # THIS IS INCORRECT: when a template is instantiated twice with different args, all Bound instances are
        # replaced by one template arg.
        # Instead, we want to make a copy (as above) before subbing.
        if actual_type_arg_tid_list:
            # unifying the instantiated free-var
            assert len(actual_type_arg_tid_list) == len(instantiated_scheme.bound_vars)
            for passed_arg, formal_arg_var in zip(actual_type_arg_tid_list, instantiated_scheme.bound_vars):
                placeholder_arg_var = instantiate_sub.rewrite_type(formal_arg_var)
                unify_sub = unifier.unify_tid(passed_arg, placeholder_arg_var)
                instantiate_sub = instantiate_sub.compose(unify_sub)

        sub = sub.compose(instantiate_sub)

    # updating the 'found_tid' with all substitutions so far:
    #   - ideally, this step involves rewriting BoundVar instances with FreeVar ones.
    found_tid = sub.rewrite_type(found_tid)

    # if no child is present, ensure we remove any formal arg mappings to avoid further substitution before return:
    #   - even if no args, may still inherit template args from outer sub-module context
    if not data.has_child:
        sub = sub.get_scheme_body_sub_without_bound_vars(
            instantiated_scheme,
            replace_deeply=True
        )

    # TODO: store the `found_def_obj` on this node for later.
    data.found_def_rec = found_def_obj

    # returning the resulting substitution, TID, SES, and CS:
    return sub, found_tid, out_ses, out_cs


#
# To resolve deferred orders, we would like to rewrite every
# TID in the system when we have a sub.
#

def rewrite_system_with_sub(
        project: "frontend.project.Project",
        any_ctx: "context.Context",
        deferred_list: "deferred.DeferredList",
        rw_sub: "substitution.Substitution"
):
    # 1. rewriting contexts:
    rw_sub.rewrite_contexts_everywhere(any_ctx)

    # 2. rewriting deferred orders:
    deferred_list.rewrite_orders_with(rw_sub)

    # 3. rewriting AST properties:
    rewrite_ast_tids(project, rw_sub)


def rewrite_ast_tids(p, rw_sub):
    for file_mod_exp in p.file_module_exp_list:
        rewrite_ast_tids_in_file_mod_exp(file_mod_exp, rw_sub)


def rewrite_ast_tids_in_file_mod_exp(file_mod_exp, rw_sub):
    for sub_mod_name, sub_mod_exp in file_mod_exp.sub_module_map.items():
        rewrite_ast_tids_in_sub_mod_exp(sub_mod_name, sub_mod_exp, rw_sub)


def rewrite_ast_tids_in_sub_mod_exp(sub_mod_name, sub_mod_exp, rw_sub):
    help_rw_ast_tids_in_table(sub_mod_exp.table, rw_sub)


def rewrite_ast_tids_in_elem(elem, rw_sub):
    assert isinstance(elem, ast.node.BaseElem)
    if isinstance(elem, ast.node.Type1VElem):
        rewrite_ast_tids_in_ts(elem.type_spec, rw_sub)
    elif isinstance(elem, ast.node.Bind1VElem):
        rewrite_ast_tids_in_exp(elem.bound_exp, rw_sub)
    elif isinstance(elem, ast.node.Bind1TElem):
        rewrite_ast_tids_in_ts(elem.bound_type_spec, rw_sub)
    elif isinstance(elem, ast.node.ForceEvalElem):
        rewrite_ast_tids_in_exp(elem.discarded_exp, rw_sub)
    else:
        raise NotImplementedError(f"Unknown element kind: {elem}")


def rewrite_ast_tids_in_ts(ts, rw_sub):
    assert isinstance(ts, ast.node.BaseTypeSpec)
    help_rw_base_typed_node_tid(ts, rw_sub)

    atomic_ts_classes = (
        ast.node.UnitTypeSpec,
        ast.node.IdTypeSpec,
    )
    if isinstance(ts, atomic_ts_classes):
        return

    elif isinstance(ts, ast.node.IdTypeSpecInModule):
        help_rw_ast_tids_in_id_node_in_module(ts.data, rw_sub)

    elif isinstance(ts, ast.node.TupleTypeSpec):
        for item_ts in ts.items:
            rewrite_ast_tids_in_ts(item_ts, rw_sub)

    elif isinstance(ts, ast.node.FnSignatureTypeSpec):
        rewrite_ast_tids_in_ts(ts.arg_type_spec, rw_sub)
        rewrite_ast_tids_in_ts(ts.return_type_spec, rw_sub)

    elif isinstance(ts, ast.node.PtrTypeSpec):
        rewrite_ast_tids_in_ts(ts.ptd_ts, rw_sub)

    elif isinstance(ts, ast.node.ArrayTypeSpec):
        rewrite_ast_tids_in_ts(ts.elem_ts, rw_sub)
        rewrite_ast_tids_in_exp(ts.array_count, rw_sub)

    elif isinstance(ts, ast.node.SliceTypeSpec):
        rewrite_ast_tids_in_ts(ts.elem_ts, rw_sub)

    elif isinstance(ts, ast.node.AdtTypeSpec):
        help_rw_ast_tids_in_table(ts.table, rw_sub)

    else:
        raise NotImplementedError(f"Unknown type-spec: {ts}")


def rewrite_ast_tids_in_exp(exp, rw_sub):
    assert isinstance(exp, ast.node.BaseExp)
    help_rw_base_typed_node_tid(exp, rw_sub)

    atomic_exp_classes = (
        ast.node.UnitExp,
        ast.node.NumberExp,
        ast.node.StringExp,
        ast.node.IdExp
    )
    if isinstance(exp, atomic_exp_classes):
        return

    elif isinstance(exp, ast.node.LambdaExp):
        rewrite_ast_tids_in_exp(exp.body, rw_sub)

    elif isinstance(exp, ast.node.UnaryExp):
        rewrite_ast_tids_in_exp(exp.arg_exp, rw_sub)

    elif isinstance(exp, ast.node.BinaryExp):
        rewrite_ast_tids_in_exp(exp.lt_arg_exp, rw_sub)
        rewrite_ast_tids_in_exp(exp.rt_arg_exp, rw_sub)

    elif isinstance(exp, ast.node.PostfixVCallExp):
        rewrite_ast_tids_in_exp(exp.called_exp, rw_sub)
        rewrite_ast_tids_in_exp(exp.arg_exp, rw_sub)

    elif isinstance(exp, ast.node.AssignExp):
        rewrite_ast_tids_in_exp(exp.src_exp, rw_sub)
        rewrite_ast_tids_in_exp(exp.dst_exp, rw_sub)

    elif isinstance(exp, ast.node.IfExp):
        rewrite_ast_tids_in_exp(exp.cond_exp, rw_sub)
        rewrite_ast_tids_in_exp(exp.then_exp, rw_sub)
        if exp.opt_else_exp is not None:
            rewrite_ast_tids_in_exp(exp.opt_else_exp, rw_sub)

    elif isinstance(exp, ast.node.ChainExp):
        help_rw_ast_tids_in_table(exp.table, rw_sub)
        rewrite_ast_tids_in_exp(exp.opt_tail, rw_sub)

    elif isinstance(exp, ast.node.CastExp):
        rewrite_ast_tids_in_ts(exp.constructor_ts, rw_sub)
        rewrite_ast_tids_in_exp(exp.initializer_data, rw_sub)

    elif isinstance(exp, ast.node.TupleExp):
        for item_exp in exp.items:
            rewrite_ast_tids_in_exp(item_exp, rw_sub)

    elif isinstance(exp, ast.node.IdExpInModule):
        help_rw_ast_tids_in_id_node_in_module(exp.data, rw_sub)

    elif isinstance(exp, ast.node.GetElementByDotIndexExp):
        rewrite_ast_tids_in_exp(exp.container, rw_sub)

    elif isinstance(exp, ast.node.GetElementByDotNameExp):
        rewrite_ast_tids_in_exp(exp.container, rw_sub)

    else:
        raise NotImplementedError(f"Unknown BaseExp: {exp}")



def help_rw_base_typed_node_tid(tn, rw_sub):
    assert isinstance(tn, ast.node.TypedBaseNode)
    if tn.x_tid is not None:
        tn.x_tid = rw_sub.rewrite_type(tn.x_tid)

def help_rw_ast_tids_in_table(table, rw_sub):
    for elem in table.elements:
        rewrite_ast_tids_in_elem(elem, rw_sub)

def help_rw_ast_tids_in_id_node_in_module(id_node_data, rw_sub):
    for arg_node in id_node_data.elem_args:
        if isinstance(arg_node, ast.node.BaseTypeSpec):
            rewrite_ast_tids_in_ts(arg_node, rw_sub)
        elif isinstance(arg_node, ast.node.BaseExp):
            rewrite_ast_tids_in_exp(arg_node, rw_sub)
        else:
            raise NotImplementedError(f"Unknown arg_node: {arg_node}")

