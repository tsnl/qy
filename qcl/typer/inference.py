import dataclasses
from functools import cache, reduce
from qcl.type import side_effects
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


file_mod_inferences: Dict["ast.node.FileModExp", FileModTypeInferenceInfo] = {}
sub_mod_inferences: Dict["ast.node.SubModExp", SubModTypeInferenceInfo]


def infer_project_types(
        project: frontend.Project,
        all_file_module_list: List["ast.node.FileModExp"]
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
        file_mod_tid = infer_file_mod_exp_tid(file_module_exp)


def infer_file_mod_exp_tid(file_mod_exp: "ast.node.FileModExp") -> type.identity.TID:
    # we use `seeding.mod_tid[...]` to resolve module imports out-of-order
    cached_mod_inference = file_mod_inferences.get(file_mod_exp, None)
    if cached_mod_inference is not None:
        return cached_mod_inference.tid
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

        # creating a new module type:
        new_mod_tid = type.new_module_type(tuple(elem_info_list))
        out_sub = out_sub.compose(substitution.Substitution({seeded_file_mod_exp_tid: new_mod_tid}))
        new_mod_tid = out_sub.rewrite_type(new_mod_tid)

        # updating caches (including seeded values, called re-seeding):
        # NOTE: re-seeding is 'unsafe', but much more efficient than creating a copy map.
        # THUS, both the original and new TIDs correctly map to the correct file-mod-exp.
        file_mod_inferences[file_mod_exp] = FileModTypeInferenceInfo(new_mod_tid, out_sub)
        seeding.mod_tid_exp_map[new_mod_tid] = file_mod_exp

        file_mod_ses = type.side_effects.SES.Tot

        out_sub.rewrite_contexts_everywhere(file_mod_ctx)
        file_mod_exp.finalize_type_info(new_mod_tid, file_mod_ses, file_mod_ctx)
        return new_mod_tid


def infer_sub_mod_exp_tid(
        sub_mod_exp: "ast.node.SubModExp"
) -> Tuple[substitution.Substitution, type.identity.TID]:
    # acquiring the seeded context, updating our caches:
    seeded_sub_mod_exp_tid = seeding.mod_exp_tid_map[sub_mod_exp]
    sub_mod_ctx = seeding.mod_context_map[sub_mod_exp]

    out_sub = substitution.empty

    elem_info_list: List[type.elem.ElemInfo] = []

    for elem in sub_mod_exp.table.ordered_value_imp_bind_elems:
        assert isinstance(elem, ast.node.BaseBindElem)
        infer_binding_elem_types(sub_mod_ctx, elem, True, elem_info_list)

    for elem in sub_mod_exp.table.ordered_type_bind_elems:
        infer_binding_elem_types(sub_mod_ctx, elem, True, elem_info_list)

    for elem in sub_mod_exp.table.ordered_typing_elems:
        infer_typing_elem_types(sub_mod_ctx, elem)

    sub_mod_exp_tid = type.new_module_type(tuple(elem_info_list))
    out_sub = out_sub.compose(substitution.Substitution({seeded_sub_mod_exp_tid: sub_mod_exp_tid}))

    sub_mod_exp_ses = type.side_effects.SES.Tot

    # re-seeding the new sub_mod's TID:
    seeding.mod_tid_exp_map[sub_mod_exp_tid] = sub_mod_exp
    sub_mod_exp.finalize_type_info(sub_mod_exp_tid, sub_mod_exp_ses, sub_mod_ctx)
    return out_sub, sub_mod_exp_tid


def infer_binding_elem_types(
        ctx: "context.Context", elem: "ast.node.BaseBindElem",
        is_bound_globally_visible: bool,
        opt_elem_info_list: Optional[List["type.elem.ElemInfo"]]
) -> Optional[type.side_effects.SES]:

    if isinstance(elem, (ast.node.Bind1VElem, ast.node.Bind1TElem)):
        if isinstance(elem, ast.node.Bind1VElem):
            sub, rhs_tid, rhs_ses = infer_exp_tid(ctx, elem.bound_exp)
            du = definition.Universe.Value
            is_type_field = False
        else:
            assert isinstance(elem, ast.node.Bind1TElem)
            assert elem.bound_type_spec is not None
            sub, rhs_tid = infer_type_spec_tid(ctx, elem.bound_type_spec)
            rhs_ses = None
            du = definition.Universe.Type
            is_type_field = True

        lhs_def_obj = ctx.lookup(elem.id_name, shallow=True)
        if lhs_def_obj is not None:
            help_def_pre_seeded_id_in_context(ctx, lhs_def_obj, rhs_tid, sub)
        else:
            # un-seeded: bound inside a chain.
            # we must define a new symbol

            id_name = elem.id_name
            def_tid = rhs_tid

            # defining the bound symbol using `set_tid`
            if du == definition.Universe.Value:
                def_rec = definition.ValueRecord(id_name, elem.loc, def_tid, is_globally_visible=is_bound_globally_visible)
            elif du == definition.Universe.Type:
                def_rec = definition.TypeRecord(elem.name, elem.loc, def_tid, is_globally_visible=is_bound_globally_visible)
            else:
                raise NotImplementedError("Unknown universe in binding")

            def_ok = ctx.try_define(id_name, def_rec)
            if not def_ok:
                msg_suffix = f"definition `{id_name}` clashes with another definition in this scope."
                raise excepts.TyperCompilationError(msg_suffix)

            # no substitutions generated-- we're all done.

        # updating contexts globally:
        sub.rewrite_contexts_everywhere(ctx)

        # appending to the `ElemInfo` list to construct fields:
        if opt_elem_info_list is not None:
            elem_info = type.elem.ElemInfo(elem.id_name, rhs_tid, is_type_field)
            opt_elem_info_list.append(elem_info)
        
        # return bound TID, optionally SES
        return rhs_ses

    else:
        raise NotImplementedError(f"Unknown elem type: {elem.__class__.__name__}")


def infer_imp_elem_types(
    ctx: "context.Context", elem: "ast.node.BaseImperativeElem"
) -> Tuple[type.identity.TID, type.side_effects.SES]:
    if isinstance(elem, ast.node.ForceEvalElem):
        sub, exp_tid, exp_ses = infer_exp_tid(ctx, elem.discarded_exp)
        sub.rewrite_contexts_everywhere(ctx)
        return exp_ses
    else:
        raise NotImplementedError(f"Unknown elem type: {elem.__class__.__name__}")


def infer_typing_elem_types(ctx: "context.Context", elem: "ast.node.BaseTypingElem") -> None:
    if isinstance(elem, ast.node.Type1VElem):
        sub, rhs_tid = infer_type_spec_tid(ctx, elem.type_spec)

        # since binding elements are always processed before typing elements, we can
        # assume any used symbols are in this context.
        # NOTE: in order to type formal args, we need to allow searching in a non-shallow way.
        #       we should generate a warning if query depth > 1, with an exception for formal args
        #       at depth 2 (since formal args are defined in their own shell-context)
        lhs_def_obj = ctx.lookup(elem.id_name)
        if lhs_def_obj is not None:
            help_def_pre_seeded_id_in_context(ctx, lhs_def_obj, rhs_tid, sub)
        else:
            msg_suffix = f"cannot type undefined symbol {elem.id_name}"
            raise excepts.TyperCompilationError(msg_suffix)

        instantiate_sub, lhs_tid = lhs_def_obj.scheme.shallow_instantiate()
        sub = unifier.unify(lhs_tid, rhs_tid)
        sub = sub.compose(instantiate_sub)

        sub.rewrite_contexts_everywhere(ctx)
    
    else:
        raise NotImplementedError("Typing any BaseTypingElem")


def help_def_pre_seeded_id_in_context(ctx, lhs_def_obj, def_tid, sub):
    # NOTE: since this ID is pre-seeded, we do not need to instantiate the scheme, rather unify body directly.
    assert not lhs_def_obj.scheme.bound_vars
    sub = sub.get_scheme_body_sub_without_bound_vars(lhs_def_obj.scheme)

    unify_sub = unifier.unify(lhs_def_obj.scheme.body_tid, def_tid)
    sub = sub.compose(unify_sub)

    sub.rewrite_contexts_everywhere(ctx)


def infer_exp_tid(
        ctx: "context.Context", exp: "ast.node.BaseExp"
) -> Tuple[substitution.Substitution, type.identity.TID, type.side_effects.SES]:
    sub, tid, ses = help_infer_exp_tid(ctx, exp)
    exp.finalize_type_info(tid, ses, ctx)
    return sub, tid, ses


def help_infer_exp_tid(
        ctx: "context.Context", exp: "ast.node.BaseExp"
) -> Tuple[substitution.Substitution, type.identity.TID, type.side_effects.SES]:
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
        call_ses = type.side_effects.SES.Tot

        # returning:
        ret_sub, def_tid = found_def_obj.scheme.shallow_instantiate()
        return ret_sub, def_tid, call_ses

    elif isinstance(exp, ast.node.IdExpInModule):
        return help_type_id_in_module_node(ctx, exp.data, definition.Universe.Value)

    #
    # context-independent branches:
    #

    elif isinstance(exp, ast.node.UnitExp):
        return substitution.empty, type.get_unit_type(), type.side_effects.SES.Tot

    elif isinstance(exp, ast.node.StringExp):
        return substitution.empty, type.get_str_type(), type.side_effects.SES.Tot

    elif isinstance(exp, ast.node.NumberExp):
        # FIXME: the type module truncates single-bit variables by only storing byte-count.

        default_number_width_in_bits = 32

        if exp.width_in_bits is None:
            width_in_bits = default_number_width_in_bits
        else:
            width_in_bits = exp.width_in_bits

        if exp.is_explicitly_float:
            return substitution.empty, type.get_float_type(width_in_bits//8), type.side_effects.SES.Tot

        elif exp.is_explicitly_unsigned_int:
            return substitution.empty, type.get_int_type(width_in_bits//8, is_unsigned=True), type.side_effects.SES.Tot

        else:
            assert exp.is_explicitly_signed_int
            return substitution.empty, type.get_int_type(width_in_bits//8, is_unsigned=False), type.side_effects.SES.Tot

    elif isinstance(exp, ast.node.PostfixVCallExp):
        ret_tid = type.new_free_var(f"fn-call")

        s1, formal_fn_tid, fn_exp_ses = infer_exp_tid(ctx, exp.called_exp)

        s2, actual_arg_tid, arg_exp_ses = infer_exp_tid(ctx, exp.arg_exp)
        actual_arg_tid = s1.rewrite_type(actual_arg_tid)

        s12 = s1.compose(s2)

        call_ses = type.side_effects.SES.Elim_AnyNonTot if exp.has_se else type.side_effects.SES.Tot
        actual_fn_tid = type.get_fn_type(actual_arg_tid, ret_tid, call_ses)
        actual_fn_tid = s12.rewrite_type(actual_fn_tid)

        s3 = unifier.unify(actual_fn_tid, formal_fn_tid)

        s123 = s12.compose(s3)

        # checking that '!' used with formal definitions of the right side-effects specifier:
        formal_ses = type.side_effects.of(formal_fn_tid)
        formal_ses_is_tot = (formal_ses == type.side_effects.SES.Tot)
        call_ses_is_tot = (call_ses == type.side_effects.SES.Tot)
        if formal_ses_is_tot and not call_ses_is_tot:
            msg_suffix = "Total function called with '!' specifier"
            raise excepts.TyperCompilationError(msg_suffix)
        elif not formal_ses_is_tot and call_ses_is_tot:
            msg_suffix = "Non-total function must be called with a '!' specifier"
            raise excepts.TyperCompilationError(msg_suffix)

        exp_ses = unifier.unify_ses(call_ses, fn_exp_ses, arg_exp_ses)
        
        return s123, s123.rewrite_type(ret_tid), exp_ses

    elif isinstance(exp, ast.node.CastExp):
        s1, src_tid, exp_ses = infer_exp_tid(ctx, exp.initializer_data)
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
            ret_sub = ret_sub.compose(ptd_unify_sub)

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

        return ret_sub, ret_sub.rewrite_type(dst_tid), exp_ses

    elif isinstance(exp, ast.node.LambdaExp):
        # each lambda gets its own scope (for formal args)
        lambda_ctx = ctx.push_context(f"lambda-{exp.loc}", exp.loc)

        # inferring the 'arg_tid':
        # NOTE: arg kind depends on arg count:
        # - if 0 args, arg kind is unit
        # - if 2 or more args, arg kind is tuple
        # - if 1 arg, arg type is just that arg's type.
        if not exp.arg_names:
            actual_arg_tid = type.get_unit_type()
        else:
            elem_arg_tid_list = []
            for i, arg_name in enumerate(exp.arg_names):
                actual_arg_tid = type.new_free_var(f"lambda-formal-arg:{arg_name}")
                arg_def_obj = definition.ValueRecord(arg_name, exp.loc, actual_arg_tid, is_globally_visible=False)
                formal_arg_def_ok = lambda_ctx.try_define(arg_name, arg_def_obj)
                if not formal_arg_def_ok:
                    msg_suffix = f"lambda formal arg #{i}: `{arg_name}` clashes with a prior definition in this scope."
                    raise excepts.TyperCompilationError(msg_suffix)

                elem_arg_tid_list.append(actual_arg_tid)

            assert elem_arg_tid_list
            if len(elem_arg_tid_list) == 1:
                actual_arg_tid = elem_arg_tid_list[0]
            else:
                actual_arg_tid = type.get_tuple_type(tuple(elem_arg_tid_list))

        assert actual_arg_tid is not None

        # inferring the 'ret_tid' from the body expression:
        ret_sub, ret_tid, ret_ses = infer_exp_tid(lambda_ctx, exp.body)
        exp.finalize_fn_ses(ret_ses)

        # now, the type of the lambda is the type of the function that accepts the given args and returns the specified
        # return expression:
        fn_tid = type.get_fn_type(actual_arg_tid, ret_tid, ret_ses)
        return ret_sub, fn_tid, type.side_effects.SES.Tot

    # typing chain expressions:
    elif isinstance(exp, ast.node.ChainExp):
        chain_ctx = ctx.push_context("chain-ctx", exp.loc)
        sub = substitution.empty
        chain_ses = exp.opt_prefix_es if exp.opt_prefix_es is not None else type.side_effects.SES.Tot

        if exp.table.elements:
            # first, effecting binding and imperative elements in order:
            #   - this ensures that initialization orders are correct
            for elem in exp.table.ordered_value_imp_bind_elems:
                if isinstance(elem, ast.node.Bind1VElem):
                    exp_ses = infer_binding_elem_types(chain_ctx, elem, is_bound_globally_visible=False, opt_elem_info_list=None)
                    assert exp_ses is not None
                else:
                    assert isinstance(elem, ast.node.BaseImperativeElem)
                    exp_ses = infer_imp_elem_types(chain_ctx, elem)

                if exp_ses is not None:
                    chain_ses = unifier.unify_ses(exp_ses, chain_ses)

            # then, defining each type binding element:
            for elem in exp.table.ordered_type_bind_elems:
                opt_ses = infer_binding_elem_types(chain_ctx, elem, is_bound_globally_visible=False, opt_elem_info_list=None)
                assert opt_ses is None

            # then, effecting each 'typing' element:
            for elem in exp.table.ordered_typing_elems:
                infer_typing_elem_types(chain_ctx, elem)

        if exp.opt_tail is not None:
            tail_sub, tail_tid, tail_ses = infer_exp_tid(chain_ctx, exp.opt_tail)
            sub = sub.compose(tail_sub)
            chain_ses = unifier.unify_ses(chain_ses, tail_ses)
        else:
            tail_tid = type.get_unit_type()

        return sub, tail_tid, chain_ses

    # typing unary, binary expressions:
    elif isinstance(exp, ast.node.UnaryExp):
        if exp.unary_op == ast.node.UnaryOp.DeRef:
            sub = substitution.empty

            ptd_tid = type.new_free_var("ptd")
            var_ptr_tid = type.get_ptr_type(ptd_tid, ptr_is_mut=False)
            
            exp_ptr_sub, exp_ptr_tid, exp_ptr_ses = infer_exp_tid(ctx, exp.arg_exp)
            sub = sub.compose(exp_ptr_sub)

            # NOTE: very important to place `exp` second here, since `allow_u_mut_ptr` lets us
            #       unify the immutable `var_ptr_tid` with a potentially mutable `exp_ptr_tid`
            unify_sub = unifier.unify(var_ptr_tid, exp_ptr_tid, allow_u_mut_ptr=True)
            sub = sub.compose(unify_sub)
    
            return sub, ptd_tid, exp_ptr_ses
        
        else:
            raise NotImplementedError(f"typing UnaryExp with unary op {exp.unary_op.name}")
        
    elif isinstance(exp, ast.node.BinaryExp):
        raise NotImplementedError(f"typing BinaryExp with binary op {exp.binary_op.name}")

    # typing AssignExp:
    elif isinstance(exp, ast.node.AssignExp):
        raise NotImplementedError(f"typing AssignExp")

    else:
        raise NotImplementedError(f"Type inference for {exp.__class__.__name__}")


def infer_type_spec_tid(
        ctx: "context.Context", ts: "ast.node.BaseTypeSpec"
):
    sub, tid = help_infer_type_spec_tid(ctx, ts)
    ts.finalize_type_info(tid, type.side_effects.SES.Tot, ctx)
    return sub, tid


def help_infer_type_spec_tid(
        ctx: "context.Context", ts: "ast.node.BaseTypeSpec"
) -> Tuple[substitution.Substitution, type.identity.TID]:
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

    elif isinstance(ts, ast.node.FnSignatureTypeSpec):
        lhs_ts = ts.arg_type_spec
        rhs_ts = ts.return_type_spec
        if ts.opt_ses is not None:
            ses = ts.opt_ses
        else:
            # default SES: `Tot`
            ses = type.side_effects.SES.Tot

        sub = substitution.empty

        lhs_sub, lhs_tid = infer_type_spec_tid(ctx, lhs_ts)
        sub = sub.compose(lhs_sub)

        rhs_sub, rhs_tid = infer_type_spec_tid(ctx, rhs_ts)
        sub = sub.compose(rhs_sub)

        fn_ts = type.get_fn_type(lhs_tid, rhs_tid, ses)

        return sub, fn_ts

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
                sub = sub.compose(field_sub)
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
        return help_type_id_in_module_node(ctx, ts.data, definition.Universe.Type)

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
) -> Tuple[context.Context, type.identity.TID, type.side_effects.SES]:
    # NOTE: IdInModuleNodes are nested and share formal variable mappings THAT CANNOT LEAVE THIS SUB-SYSTEM.
    #   - this means that the substitution returns formal -> actual mappings UNLESS it has no child, in which case
    #     it is the last IdInModuleNode in the process.

    sub = substitution.empty

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
        container_sub, container_tid = help_type_id_in_module_node(ctx, data.opt_container, definition.Universe.Module)
        container_mod_exp = seeding.mod_tid_exp_map[container_tid]
        sub = sub.compose(container_sub)

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

        # FIXME: somehow, executing THIS--v statement changes the scheme in the global definition, even though I am
        #        unsure of how.
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
                    actual_arg_sub, actual_value_arg_tid = infer_exp_tid(ctx, actual_arg_exp)
                    sub = sub.compose(actual_arg_sub)

                    assert names.infer_def_universe_of(formal_name) == definition.Universe.Value
                    formal_val_def_obj = instantiated_mod_ctx.lookup(formal_name, shallow=True)
                    assert isinstance(formal_val_def_obj, definition.ValueRecord)
                    instantiate_sub, formal_value_arg_tid = formal_val_def_obj.scheme.shallow_instantiate()
                    sub = sub.compose(instantiate_sub)

                    # unifying value args:
                    this_val_arg_sub = unifier.unify(
                        sub.rewrite_type(formal_value_arg_tid),
                        sub.rewrite_type(actual_value_arg_tid)
                    )
                    sub = sub.compose(this_val_arg_sub)
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

    # returning the resulting substitution, TID, and SES:
    ses = type.side_effects.SES.Tot
    return sub, found_tid, ses
