import dataclasses
import typing as t

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


SES = type.side_effects.SES
CS = type.memory.ClosureSpec


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
        all_file_module_list: t.List["ast.node.FileModExp"]
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
        sub, file_mod_tid = infer_file_mod_exp_tid(file_module_exp)


def infer_file_mod_exp_tid(
        file_mod_exp: "ast.node.FileModExp"
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
            import_sub, imported_mod_tid = infer_file_mod_exp_tid(imported_file_mod_exp)

            # composing substitutions:
            # NOTE: all previous elements are now invalidated.
            out_sub = out_sub.compose(import_sub)

            # adding the new elem_info_list:
            new_elem_info = type.elem.ElemInfo(import_mod_name, imported_mod_tid, False)
            elem_info_list.append(new_elem_info)

        # FROM SUB-MODS:
        # adding elem_info for each sub-mod:
        for sub_mod_name, sub_mod_exp in file_mod_exp.sub_module_map.items():
            sub_mod_substitution, sub_mod_tid = infer_sub_mod_exp_tid(sub_mod_exp)

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
        out_sub.rewrite_contexts_everywhere(file_mod_ctx)

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
        sub_mod_exp: "ast.node.SubModExp"
) -> t.Tuple[substitution.Substitution, type.identity.TID]:
    # acquiring the seeded context, updating our caches:
    seeded_sub_mod_exp_tid = seeding.mod_exp_tid_map[sub_mod_exp]
    sub_mod_ctx = seeding.mod_context_map[sub_mod_exp]

    out_sub = substitution.empty

    elem_info_list: t.List[type.elem.ElemInfo] = []

    for elem in sub_mod_exp.table.ordered_value_imp_bind_elems:
        assert isinstance(elem, ast.node.BaseBindElem)
        opt_ses, cs, elem_sub = infer_binding_elem_types(sub_mod_ctx, elem, True, elem_info_list)
        out_sub = elem_sub.compose(out_sub)
        # ignoring CS:
        # if not NO, must be a function that requires closures.
        # if a function requires closures, it must be for a nested function, since as a sub-module element,
        #   it is global and cannot have any closed elements.

    for elem in sub_mod_exp.table.ordered_type_bind_elems:
        opt_ses, cs, elem_sub = infer_binding_elem_types(sub_mod_ctx, elem, True, elem_info_list)
        out_sub = elem_sub.compose(out_sub)

    for elem in sub_mod_exp.table.ordered_typing_elems:
        elem_sub = infer_typing_elem_types(sub_mod_ctx, elem)
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
        ctx: "context.Context", elem: "ast.node.BaseBindElem",
        is_bound_globally_visible: bool,
        opt_elem_info_list: t.Optional[t.List[type.elem.ElemInfo]]
) -> t.Tuple[t.Optional[SES], CS, substitution.Substitution]:

    if isinstance(elem, (ast.node.Bind1VElem, ast.node.Bind1TElem)):
        if isinstance(elem, ast.node.Bind1VElem):
            sub, rhs_tid, opt_rhs_ses, rhs_cs = infer_exp_tid(ctx, elem.bound_exp)
            du = definition.Universe.Value
            is_type_field = False
        else:
            assert isinstance(elem, ast.node.Bind1TElem)
            assert elem.bound_type_spec is not None
            sub, rhs_tid = infer_type_spec_tid(ctx, elem.bound_type_spec)
            opt_rhs_ses = None
            rhs_cs = CS.No
            du = definition.Universe.Type
            is_type_field = True

        lhs_def_obj = ctx.lookup(elem.id_name, shallow=True)
        if lhs_def_obj is not None:
            def_sub = unify_existing_def(ctx, lhs_def_obj, rhs_tid, sub)
            sub = def_sub.compose(sub)
        else:
            # un-seeded: bound inside a chain.
            # we must define a new symbol

            id_name = elem.id_name
            def_tid = rhs_tid

            # defining the bound symbol using `set_tid`
            if du == definition.Universe.Value:
                def_rec = definition.ValueRecord(
                    id_name, elem.loc, def_tid,
                    opt_func=ctx.opt_func,
                    is_protected_from_global_scope=(not is_bound_globally_visible)
                )
            elif du == definition.Universe.Type:
                def_rec = definition.TypeRecord(
                    id_name, elem.loc, def_tid,
                    opt_func=ctx.opt_func,
                    is_protected_from_global_scope=(not is_bound_globally_visible)
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
    ctx: "context.Context", elem: "ast.node.BaseImperativeElem"
) -> t.Tuple[type.identity.TID, SES, CS, substitution.Substitution]:
    if isinstance(elem, ast.node.ForceEvalElem):
        sub, exp_tid, exp_ses, exp_cs = infer_exp_tid(ctx, elem.discarded_exp)
        # sub.rewrite_contexts_everywhere(ctx)
        return exp_tid, exp_ses, exp_cs, sub
    else:
        raise NotImplementedError(f"Unknown elem type: {elem.__class__.__name__}")


def infer_typing_elem_types(ctx: "context.Context", elem: "ast.node.BaseTypingElem") -> substitution.Substitution:
    if isinstance(elem, ast.node.Type1VElem):
        sub, rhs_tid = infer_type_spec_tid(ctx, elem.type_spec)

        # since binding elements are always processed before typing elements, we can
        # assume any used symbols are in this context.
        # NOTE: in order to type formal args, we need to allow searching in a non-shallow way.
        #       we should generate a warning if query depth > 1, with an exception for formal args
        #       at depth 2 (since formal args are defined in their own shell-context)
        lhs_def_obj = ctx.lookup(elem.id_name)
        if lhs_def_obj is not None:
            def_sub = unify_existing_def(ctx, lhs_def_obj, rhs_tid, sub)
            sub = def_sub.compose(sub)
        else:
            msg_suffix = f"cannot type undefined symbol {elem.id_name}"
            raise excepts.TyperCompilationError(msg_suffix)

        instantiate_sub, lhs_tid = lhs_def_obj.scheme.shallow_instantiate()
        sub = instantiate_sub.compose(sub)

        unify_sub = unifier.unify(lhs_tid, rhs_tid)
        sub = unify_sub.compose(sub)

        # sub.rewrite_contexts_everywhere(ctx)
        return sub

    else:
        raise NotImplementedError("Typing any BaseTypingElem")


def unify_existing_def(ctx, lhs_def_obj, new_def_tid, sub) -> substitution.Substitution:
    # NOTE: since this ID is pre-seeded, we do not need to instantiate the scheme, rather unify body directly.
    assert not lhs_def_obj.scheme.bound_vars
    sub = sub.get_scheme_body_sub_without_bound_vars(lhs_def_obj.scheme)

    # NOTE: the existing def can be immutable: internally promoted to mutable by unifier
    # NOTE: directly access body_tid to avoid instantiating free vars
    old_def_tid = lhs_def_obj.scheme.body_tid
    unify_sub = unifier.unify(old_def_tid, new_def_tid, allow_u_mut_ptr=True)
    sub = sub.compose(unify_sub)

    # NOTE: we need to rewrite contexts as soon as unifying definitions to avoid multiple subs of an old seed
    #   - sub composition cannot handle such divergent mappings
    #   - this may rewrite `old_def_tid`
    sub.rewrite_contexts_everywhere(ctx)

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
            new_def_ses != SES.Elim_AnyNonTot and
            old_def_ses == SES.Elim_AnyNonTot
        )
        #
        # Comparing CS (ClosureSpec):
        #

        new_def_cs = type.memory.closure_spec(new_def_tid)
        old_def_cs = type.memory.closure_spec(old_def_tid)

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
        ctx: "context.Context", exp: "ast.node.BaseExp"
) -> t.Tuple[substitution.Substitution, type.identity.TID, SES, CS]:
    sub, tid, ses, cs = help_infer_exp_tid(ctx, exp)
    exp.finalize_type_info(tid, ses, cs, ctx)
    return sub, tid, ses, cs


def help_infer_exp_tid(
        ctx: "context.Context", exp: "ast.node.BaseExp"
) -> t.Tuple[substitution.Substitution, type.identity.TID, SES, CS]:
    #
    # context-dependent branches: ID, ModAddressID
    #

    if isinstance(exp, ast.node.IdExp):
        found_def_obj = ctx.lookup(exp.name)

        # ensuring the definition exists:
        if found_def_obj is None:
            raise excepts.TyperCompilationError(f"Symbol {exp.name} used but not defined.")

        # ensuring the definition is in the right universe (not a module)
        du = names.infer_def_universe_of(exp.name)
        if du != definition.Universe.Value:
            raise excepts.TyperCompilationError(
                f"Symbol {exp.name} is not defined in the 'Value' universe. Are you missing a `:` suffix?"
            )

        # storing the found definition on the ID:
        exp.found_def_rec = found_def_obj

        # SES is always `Tot` for a `load` operation:
        call_ses = SES.Tot

        if found_def_obj.opt_container_func is None:
            # found def is a global ID. No closure required.
            closure_spec = CS.No
        else:
            # found def is defined inside a function.

            # we cannot access an ID in this context or a higher context with a container func without being in a func
            # ourselves.
            assert ctx.opt_func is not None

            # checking if the accessed ID is in the same function as us, or a higher one (in which case, this is a
            # non-local ID)
            id_is_closure = ctx.opt_func != found_def_obj.opt_container_func
            if not id_is_closure:
                closure_spec = CS.No
            else:
                closure_spec = CS.Yes

                # adding this ID to the function's 'enclosed set'
                ctx.opt_func.add_non_local(exp.name, found_def_obj)

        # returning:
        ret_sub, def_tid = found_def_obj.scheme.shallow_instantiate()
        return ret_sub, def_tid, call_ses, closure_spec

    elif isinstance(exp, ast.node.IdExpInModule):
        sub, tid, ses, cs = help_type_id_in_module_node(ctx, exp.data, definition.Universe.Value)
        return sub, tid, ses, cs

    #
    # context-independent branches:
    #

    elif isinstance(exp, ast.node.UnitExp):
        return substitution.empty, type.get_unit_type(), SES.Tot, CS.No

    elif isinstance(exp, ast.node.StringExp):
        return substitution.empty, type.get_str_type(), SES.Tot, CS.No

    elif isinstance(exp, ast.node.NumberExp):
        # FIXME: the type module truncates single-bit variables by only storing byte-count.

        default_number_width_in_bits = 32

        if exp.width_in_bits is None:
            width_in_bits = default_number_width_in_bits
        else:
            width_in_bits = exp.width_in_bits

        if exp.is_explicitly_float:
            return (
                substitution.empty,
                type.get_float_type(width_in_bits//8),
                SES.Tot,
                CS.No
            )

        elif exp.is_explicitly_unsigned_int:
            return (
                substitution.empty,
                type.get_int_type(width_in_bits//8, is_unsigned=True),
                SES.Tot,
                CS.No
            )
        else:
            assert exp.is_explicitly_signed_int
            return (
                substitution.empty,
                type.get_int_type(width_in_bits//8, is_unsigned=False),
                SES.Tot,
                CS.No
            )

    elif isinstance(exp, ast.node.PostfixVCallExp):
        ret_tid = type.new_free_var(f"fn-call")

        s1, formal_fn_tid, fn_exp_ses, fn_cs = infer_exp_tid(ctx, exp.called_exp)

        s2, formal_arg_tid, arg_exp_ses, arg_cs = infer_exp_tid(ctx, exp.arg_exp)
        formal_arg_tid = s1.rewrite_type(formal_arg_tid)

        s12 = s2.compose(s1)

        call_ses = SES.Elim_AnyNonTot if exp.has_se else SES.Tot

        closure_spec = type.memory.closure_spec(formal_fn_tid)

        actual_fn_tid = type.get_fn_type(formal_arg_tid, ret_tid, call_ses, closure_spec)
        actual_fn_tid = s12.rewrite_type(actual_fn_tid)

        s3 = unifier.unify(actual_fn_tid, formal_fn_tid)

        s123 = s3.compose(s12)

        # checking that '!' used with formal definitions of the right side-effects specifier:
        formal_ses = type.side_effects.of(formal_fn_tid)
        formal_ses_is_tot = (formal_ses == SES.Tot)
        call_ses_is_tot = (call_ses == SES.Tot)
        if formal_ses_is_tot and not call_ses_is_tot:
            msg_suffix = "Total function called with '!' specifier"
            raise excepts.TyperCompilationError(msg_suffix)
        elif not formal_ses_is_tot and call_ses_is_tot:
            msg_suffix = "Non-total function must be called with a '!' specifier"
            raise excepts.TyperCompilationError(msg_suffix)

        exp_ses = unifier.unify_ses(call_ses, fn_exp_ses, arg_exp_ses)

        exp_cs = unifier.unify_closure_spec(fn_cs, arg_cs)

        return s123, s123.rewrite_type(ret_tid), exp_ses, exp_cs

    elif isinstance(exp, ast.node.CastExp):
        s1, src_tid, exp_ses, exp_cs = infer_exp_tid(ctx, exp.initializer_data)
        s2, dst_tid = infer_type_spec_tid(ctx, exp.constructor_ts)
        dst_tid = s1.rewrite_type(dst_tid)
        ret_sub = s1.compose(s2)

        #
        # checking if conversion is valid:
        #

        src_tk = type.kind.of(src_tid)
        dst_tk = type.kind.of(dst_tid)

        simple_monomorphic_tk_set = {
            type.kind.TK.Unit,
            type.kind.TK.String
        }
        number_tk_set = {
            type.kind.TK.SignedInt,
            type.kind.TK.UnsignedInt,
            type.kind.TK.Float
        }
        simple_window_tk_set = {
            type.kind.TK.Pointer,
            type.kind.TK.Array
        }
        slice_src_tk_set = {
            type.kind.TK.Slice,
            type.kind.TK.Array
        }
        var_tk_set = {
            type.kind.TK.FreeVar,
            type.kind.TK.BoundVar,
        }

        # TODO: compare src_tid and dst_tid to ensure they can be inter-converted.
        #   - Unit only from Unit, String only from String
        #   - SignedInt, UnsignedInt, Float from SignedInt, UnsignedInt, Float (numbers interchangeable)
        #   - Struct, Tuple from Struct, Tuple
        #       - need to perform element-wise conversion
        #       - length mismatch from tuple or struct unacceptable <=> mostly identity operation on packed bytes
        #   - Enum, Union from other Enum, Union
        #       - can construct enum/union branch using `EnumType:variant` or `UnionType:variant` (syntax WIP)
        #   - Array from Array only, Pointer from Pointer only, Slice from Array or Slice
        #       - NOTE: can unify content type for all three containers: implies that `reinterpret_cast`-type behavior
        #         is a totally different expression/function.
        #       - NOTE: must also ensure `mut` specifier matches: can convert from `mut` to non-mut but not vice-versa.
        #   - cannot cast any other type kind

        # case 1: String, Unit
        if dst_tk in simple_monomorphic_tk_set:
            if src_tid != dst_tid:
                raise_cast_error(src_tid, dst_tid)

        # case 2: numbers
        elif dst_tk in number_tk_set:
            if src_tk not in number_tk_set:
                raise_cast_error(src_tid, dst_tid)

        # case 3: array/ptr
        elif dst_tk in simple_window_tk_set:
            # checking that we are only converting array -> array and ptr -> ptr
            if src_tk != dst_tk:
                raise_cast_error(src_tid, dst_tid, "cannot convert array to pointer or vice-versa")

            # checking both share the same mutability:
            dst_is_mut = bool(type.is_mut.ptr_or_array_or_slice(dst_tid))
            src_is_mut = bool(type.is_mut.ptr_or_array_or_slice(src_tid))
            if dst_is_mut and not src_is_mut:
                raise_cast_error(src_tid, dst_tid, "cannot cast immutable window to a mutable one")

            # attempting to unify content types => error if failed.
            ptd_unify_sub = unifier.unify(
                type.elem.tid_of_ptd(src_tid),
                type.elem.tid_of_ptd(dst_tid)
            )
            ret_sub = ptd_unify_sub.compose(ret_sub)

            # if both arrays, check if length is identical:
            if dst_tk == type.kind.TK.Array:
                # TODO: need to further validate the arrays are of the same length
                # NOTE: can also determine this in 'basic checks' later
                pass

        # case 4: slice
        elif dst_tk == type.kind.TK.Slice:
            if src_tk not in slice_src_tk_set:
                raise_cast_error(src_tid, dst_tid)

        # case 5: ensure no inference errors
        elif src_tk in var_tk_set or dst_tk in var_tk_set:
            # TODO: since this is tripped, we should switch to a deferred checking system
            #   - this means appending `src_tid` and `dst_tid` to a list in the context that admits substitutions
            #       - consider extending the context with 'orders' so 'sub' works
            #   - run the above code on `src_tid` and `dst_tid` after inference (introduce a 3rd pass)
            raise NotImplementedError("cannot check casting of var types")

        #
        # all OK!
        #

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
                formal_arg_tid = type.new_free_var(f"lambda-formal-arg:{arg_name}")
                arg_def_obj = definition.ValueRecord(arg_name, exp.loc, formal_arg_tid, opt_func=exp)
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

        # inferring the 'ret_tid' and 'closure_spec' from the body expression:
        ret_sub, ret_tid, ret_ses, closure_spec = infer_exp_tid(lambda_ctx, exp.body)
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
                        chain_ctx, elem,
                        is_bound_globally_visible=False,
                        opt_elem_info_list=None
                    )
                    assert exp_ses is not None
                    sub = exp_sub.compose(sub)
                    output_cs = unifier.unify_closure_spec(output_cs, exp_cs)
                else:
                    assert isinstance(elem, ast.node.BaseImperativeElem)
                    exp_tid, exp_ses, exp_cs, exp_sub = infer_imp_elem_types(chain_ctx, elem)
                    sub = exp_sub.compose(sub)
                    output_cs = unifier.unify_closure_spec(output_cs, exp_cs)

                if exp_ses is not None:
                    if not unifier.compare_ses(expected_ses, exp_ses):
                        raise excepts.TyperCompilationError(f"element #{1+elem_index} violates SES for chain")
                    expected_ses = unifier.unify_ses(exp_ses, expected_ses)

            # then, defining each type binding element:
            for elem in exp.table.ordered_type_bind_elems:
                opt_ses, elem_cs, elem_sub = infer_binding_elem_types(
                    chain_ctx, elem,
                    is_bound_globally_visible=False,
                    opt_elem_info_list=None
                )
                assert opt_ses is None
                assert elem_cs == CS.No
                sub = elem_sub.compose(sub)

            # then, effecting each 'typing' element:
            for elem in exp.table.ordered_typing_elems:
                infer_typing_elem_types(chain_ctx, elem)

        if exp.opt_tail is not None:
            tail_sub, tail_tid, tail_ses, tail_cs = infer_exp_tid(chain_ctx, exp.opt_tail)
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
        if exp.unary_op in (ast.node.UnaryOp.DeRefImmutable, ast.node.UnaryOp.DeRefMutable):
            sub = substitution.empty

            initializer_tid = type.new_free_var("ptd")
            if exp.unary_op == ast.node.UnaryOp.DeRefImmutable:
                var_ptr_tid = type.get_ptr_type(initializer_tid, ptr_is_mut=False)
            elif exp.unary_op == ast.node.UnaryOp.DeRefMutable:
                var_ptr_tid = type.get_ptr_type(initializer_tid, ptr_is_mut=True)
            else:
                raise NotImplementedError("unknown ptr type for `var_ptr_tid`")
            
            exp_ptr_sub, exp_ptr_tid, exp_ptr_ses, exp_ptr_cs = infer_exp_tid(ctx, exp.arg_exp)
            sub = exp_ptr_sub.compose(sub)

            # NOTE: very important to place `exp` second here, since `allow_u_mut_ptr` lets us
            #       unify the immutable `var_ptr_tid` with a potentially mutable `exp_ptr_tid`
            unify_sub = unifier.unify(var_ptr_tid, exp_ptr_tid, allow_u_mut_ptr=True)
            sub = unify_sub.compose(sub)
            initializer_tid = sub.rewrite_type(initializer_tid)

            # NOTE: regardless of whether we de-reference a mutable or immutable pointer, this op is still `TOT`

            return sub, initializer_tid, exp_ptr_ses, exp_ptr_cs

        else:
            raise NotImplementedError(f"typing UnaryExp with unary op {exp.unary_op.name}")
        
    elif isinstance(exp, ast.node.BinaryExp):
        raise NotImplementedError(f"typing BinaryExp with binary op {exp.binary_op.name}")

    # typing AssignExp:
    elif isinstance(exp, ast.node.AssignExp):
        ptd_tid = type.new_free_var("assign.ptd")
        ptr_tid = type.get_ptr_type(ptd_tid, True)

        sub = substitution.empty

        val_exp_sub, val_exp_tid, val_exp_ses, val_exp_cs = infer_exp_tid(ctx, exp.src_exp)
        sub = val_exp_sub.compose(sub)

        ptr_exp_sub, ptr_exp_tid, ptr_exp_ses, ptr_exp_cs = infer_exp_tid(ctx, exp.dst_exp)
        sub = ptr_exp_sub.compose(sub)

        unify_sub_1 = unifier.unify(ptr_tid, ptr_exp_tid)
        sub = unify_sub_1.compose(sub)
        unify_sub_2 = unifier.unify(ptd_tid, val_exp_tid)
        sub = unify_sub_2.compose(sub)

        exp_cs = unifier.unify_closure_spec(val_exp_cs, ptr_exp_cs)

        # TODO: alter `ST` to `Tot` if the destination pointer is stack-allocated
        #   - this must be determined in the typer
        #   - we need to track which pointers are 'stack-local' in any function frame
        #   - we cannot associate pointers with function instances because a func may pass a stack pointer to itself
        #   - perhaps we can associate each value with where it is stored:
        #       - Stack_Local, Stack_NonLocal, Heap_Global, Heap_NonGlobal
        #       - returned along with TID, sub, SES

        assign_ses = unifier.unify_ses(
            SES.ST,
            val_exp_ses,
            ptr_exp_ses
        )

        return sub, ptd_tid, assign_ses, exp_cs

    # typing memory windows:
    elif isinstance(exp, (ast.node.AllocatePtrExp, ast.node.AllocateArrayExp, ast.node.AllocateSliceExp)):
        alloc_ses = {
            ast.node.Allocator.Stack: SES.Tot,
            ast.node.Allocator.Heap: SES.ML
        }[exp.allocator]

        # TODO: verify that `push` only invoked in a function: check ctx.opt_func

        initializer_sub, initializer_tid, initializer_ses, initializer_cs = infer_exp_tid(ctx, exp.initializer_exp)
        if isinstance(exp, ast.node.AllocatePtrExp):
            ptr_tid = type.get_ptr_type(initializer_tid, exp.is_mut)
            ptr_ses = unifier.unify_ses(initializer_ses, alloc_ses)
            return initializer_sub, ptr_tid, ptr_ses, initializer_cs
        elif isinstance(exp, ast.node.AllocateArrayExp):
            # TODO: unify array 'size' parameter's type, get SES and CS
            array_tid = type.get_array_type(initializer_tid, exp.is_mut)
            array_ses = unifier.unify_ses(initializer_ses, alloc_ses)
            return initializer_sub, array_tid, array_ses, initializer_cs
        elif isinstance(exp, ast.node.AllocateSliceExp):
            slice_tid = type.get_slice_type(initializer_tid, exp.is_mut)
            # TODO: unify slice 'size' parameter's type, get SES and CS
            slice_ses = unifier.unify_ses(initializer_ses, alloc_ses)
            return initializer_sub, slice_tid, slice_ses, initializer_cs

    else:
        raise NotImplementedError(f"Type inference for {exp.__class__.__name__}")


def infer_type_spec_tid(
        ctx: "context.Context", ts: "ast.node.BaseTypeSpec"
):
    sub, tid = help_infer_type_spec_tid(ctx, ts)
    ts.finalize_type_info(tid, SES.Tot, CS.No, ctx)
    return sub, tid


def help_infer_type_spec_tid(
        ctx: "context.Context", ts: "ast.node.BaseTypeSpec"
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

        lhs_sub, lhs_tid = infer_type_spec_tid(ctx, lhs_ts)
        sub = lhs_sub.compose(sub)

        rhs_sub, rhs_tid = infer_type_spec_tid(ctx, rhs_ts)
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
                field_sub, field_tid = infer_type_spec_tid(ctx, field_type_spec_elem.type_spec)
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
        sub, tid, ses, cs = help_type_id_in_module_node(ctx, ts.data, definition.Universe.Type)

        if ses != SES.Tot:
            raise excepts.TyperCompilationError(
                "Cannot use non-TOT expressions as template arguments"
            )

        if cs == CS.Yes:
            raise excepts.TyperCompilationError(
                "Cannot use non-local variables as constants in type expressions"
            )

        return sub, tid

    elif isinstance(ts, ast.node.PtrTypeSpec):
        ptd_sub, ptd_tid = infer_type_spec_tid(ctx, ts.ptd_ts)
        ptr_tid = type.get_ptr_type(ptd_tid, ts.is_mut)
        return ptd_sub, ptr_tid

    raise NotImplementedError(f"Type inference for {ts.__class__.__name__}")


def raise_cast_error(src_tid, dst_tid, more=None):
    spell_src = type.spelling.of(src_tid)
    spell_dst = type.spelling.of(dst_tid)
    msg_suffix = f"Cannot cast to {spell_dst} from {spell_src}"
    if more is not None:
        msg_suffix += f": {more}"
    raise excepts.TyperCompilationError(msg_suffix)


def help_type_id_in_module_node(
    ctx, data: "ast.node.IdNodeInModuleHelper", expect_du: definition.Universe
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
            ctx, data.opt_container,
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
                    actual_arg_sub, actual_arg_tid, actual_arg_ses, actual_arg_cs = infer_exp_tid(ctx, actual_arg_exp)
                    sub = sub.compose(actual_arg_sub)

                    assert names.infer_def_universe_of(formal_name) == definition.Universe.Value
                    formal_val_def_obj = instantiated_mod_ctx.lookup(formal_name, shallow=True)
                    assert isinstance(formal_val_def_obj, definition.ValueRecord)
                    instantiate_sub, formal_value_arg_tid = formal_val_def_obj.scheme.shallow_instantiate()
                    sub = sub.compose(instantiate_sub)

                    # unifying value args:
                    this_val_arg_sub = unifier.unify(
                        sub.rewrite_type(formal_value_arg_tid),
                        sub.rewrite_type(actual_arg_tid)
                    )
                    sub = sub.compose(this_val_arg_sub)

                    # unifying SES and CS:
                    out_ses = unifier.unify_ses(out_ses, actual_arg_ses)
                    out_cs = unifier.unify_closure_spec(out_cs, actual_arg_cs)
            else:
                assert isinstance(actual_arg_node, ast.node.BaseTypeSpec)
                if name_universe != definition.Universe.Type:
                    mismatch_list.append(f"- arg #{arg_index}: expected value arg, received a type")
                else:
                    assert isinstance(actual_arg_node, ast.node.BaseTypeSpec)
                    assert names.infer_def_universe_of(formal_name) == definition.Universe.Type

                    actual_arg_ts = actual_arg_node
                    actual_arg_sub, actual_type_arg_tid = infer_type_spec_tid(ctx, actual_arg_ts)
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
                unify_sub = unifier.unify(passed_arg, placeholder_arg_var)
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

    # returning the resulting substitution, TID, SES, and CS:
    return sub, found_tid, out_ses, out_cs
