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
        new_mod_tid = out_sub.rewrite_type(new_mod_tid)

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
    if isinstance(elem, (ast.node.Bind1VElem, ast.node.Bind1TElem)):
        if isinstance(elem, ast.node.Bind1VElem):
            sub, rhs_tid = infer_exp_tid(ctx, elem.bound_exp)
        else:
            assert isinstance(elem, ast.node.Bind1TElem)
            sub, rhs_tid = infer_type_spec_tid(ctx, elem.bound_type_spec)

        lhs_def_obj = ctx.lookup(elem.id_name, shallow=True)
        if lhs_def_obj is not None:
            # pre-seeded:
            sub_lhs, lhs_tid = sub.rewrite_scheme(lhs_def_obj.scheme).instantiate()
            sub = sub.compose(sub_lhs)
        else:
            # un-seeded: bound inside a chain
            raise NotImplementedError("binding elem in chains")

        unify_sub = unifier.unify(lhs_tid, rhs_tid)
        sub = sub.compose(unify_sub)

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
        # TODO: validate that the found definition is in the right universe.

        found_def_obj = ctx.lookup(exp.name)
        if found_def_obj is not None:
            ret_sub, def_tid = found_def_obj.scheme.instantiate()
            return ret_sub, def_tid
        else:
            raise excepts.TyperCompilationError(f"Symbol {exp.name} used but not defined.")

    elif isinstance(exp, ast.node.GetModElementExp):
        # FIXME: something is really fishy about how we handle containers here...
        #   - elem_args should instantiate the found elem independent of the container

        ret_sub = substitution.empty

        # looking up `found_def_obj` referring to [a:]b in this exp:
        if exp.opt_container is None:
            # the LHS is None, so the RHS must look up in the local context:
            file_mod_name = exp.elem_name
            found_def_obj = ctx.lookup(file_mod_name)

            if found_def_obj is None:
                msg_suffix = f"symbol {file_mod_name} not found"
                raise excepts.TyperCompilationError(msg_suffix)
            elif not isinstance(found_def_obj, definition.ModRecord):
                msg_suffix = f"expected {file_mod_name} to refer to a file-mod, not other"
                raise excepts.TyperCompilationError(msg_suffix)
        else:
            assert exp.opt_container is not None

            # getting a mod-exp for the container:
            container_sub, container_tid = infer_exp_tid(ctx, exp.opt_container)
            container_mod_exp = seeding.mod_tid_exp_map[container_tid]
            container_ctx = seeding.mod_context_map[container_mod_exp]

            # updating the existing sub with the sub from this inference:
            ret_sub = ret_sub.compose(container_sub)

            # looking up the element in the container:
            found_def_obj = container_ctx.lookup(exp.elem_name, shallow=True)
            if found_def_obj is None:
                msg_suffix = f"element {exp.elem_name} not found in existing module"
                raise excepts.TyperCompilationError(msg_suffix)

        # instantiating the found definition's scheme, using actual arguments if provided:
        instantiated_scheme = found_def_obj.scheme
        if not exp.elem_args:
            # no template arg call required/automatically instantiate:
            instantiation_sub, found_tid = instantiated_scheme.instantiate()
            ret_sub = ret_sub.compose(instantiation_sub)
            return ret_sub, ret_sub.rewrite_type(found_tid)
        else:
            # template args provided: must be matched against the definition.

            #
            # first, checking that the def of the called object actually points to a sub-module:
            #

            if not isinstance(found_def_obj, definition.ModRecord):
                msg = f"cannot use any ({len(exp.elem_args)}) template args to instantiate a non-module definition"
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
            actual_arg_count = len(exp.elem_args)
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
            zipped_args = zip(instantiated_mod_exp.template_arg_names, exp.elem_args)
            for arg_index, (formal_name, actual_arg_node) in enumerate(zipped_args):
                name_universe = names.infer_def_universe_of(formal_name)
                if isinstance(actual_arg_node, ast.node.BaseExp):
                    if name_universe != definition.Universe.Value:
                        mismatch_list.append(f"- arg #{arg_index}: expected type arg, received a value")
                    else:
                        actual_arg_exp = actual_arg_node
                        actual_arg_sub, actual_value_arg_tid = infer_exp_tid(ctx, actual_arg_exp)
                        ret_sub = ret_sub.compose(actual_arg_sub)

                        assert names.infer_def_universe_of(formal_name) == definition.Universe.Value
                        formal_val_def_obj = instantiated_mod_ctx.lookup(formal_name, shallow=True)
                        assert isinstance(formal_val_def_obj, definition.ValueRecord)
                        instantiate_sub, formal_value_arg_tid = formal_val_def_obj.scheme.instantiate()
                        ret_sub = ret_sub.compose(instantiate_sub)

                        # unifying value args:
                        this_val_arg_sub = unifier.unify(
                            ret_sub.rewrite_type(formal_value_arg_tid),
                            ret_sub.rewrite_type(actual_value_arg_tid)
                        )
                        ret_sub = ret_sub.compose(this_val_arg_sub)
                else:
                    assert isinstance(actual_arg_node, ast.node.BaseTypeSpec)
                    if name_universe != definition.Universe.Type:
                        mismatch_list.append(f"- arg #{arg_index}: expected value arg, received a type")
                    else:
                        assert isinstance(actual_arg_node, ast.node.BaseTypeSpec)
                        assert names.infer_def_universe_of(formal_name) == definition.Universe.Type

                        actual_arg_ts = actual_arg_node
                        actual_arg_sub, actual_type_arg_tid = infer_type_spec_tid(ctx, actual_arg_ts)
                        ret_sub = ret_sub.compose(actual_arg_sub)

                        actual_type_arg_tid_list.append(actual_type_arg_tid)

            if mismatch_list:
                mismatch_text = '\n'.join(mismatch_list)
                msg_suffix = f"Mismatched template args:\n{mismatch_text}"
                raise excepts.TyperCompilationError(msg_suffix)

            # instantiating the scheme using type args:
            # - unifies bound and actual type args, thereby monomorphizing
            instantiate_sub, found_tid = instantiated_scheme.instantiate(args=actual_type_arg_tid_list)
            ret_sub = ret_sub.compose(instantiate_sub)

            # returning the resulting substitution and TID:
            return ret_sub, ret_sub.rewrite_type(found_tid)

    #
    # context-independent branches:
    #

    elif isinstance(exp, ast.node.UnitExp):
        return substitution.empty, type.get_unit_type()

    elif isinstance(exp, ast.node.StringExp):
        return substitution.empty, type.get_str_type()

    elif isinstance(exp, ast.node.NumberExp):
        # FIXME: the type module truncates single-bit variables by only storing byte-count.

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

        s2, actual_arg_tid = infer_exp_tid(ctx, exp.arg_exp)
        actual_arg_tid = s1.rewrite_type(actual_arg_tid)

        s12 = s1.compose(s2)

        ses = type.side_effects.SES.Elim_AnyNonTot if exp.has_se else type.side_effects.SES.Tot
        actual_fn_tid = type.get_fn_type(actual_arg_tid, ret_tid, ses)
        actual_fn_tid = s12.rewrite_type(actual_fn_tid)

        s3 = unifier.unify(actual_fn_tid, formal_fn_tid)

        s123 = s12.compose(s3)

        return s123, s123.rewrite_type(ret_tid)

    elif isinstance(exp, ast.node.CastExp):
        s1, src_tid = infer_exp_tid(ctx, exp.initializer_data)
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

        return ret_sub, ret_sub.rewrite_type(dst_tid)

    elif isinstance(exp, ast.node.LambdaExp):
        # each lambda gets its own scope (for formal args)
        lambda_ctx = ctx.push_context(f"lambda-{exp.loc}")

        # inferring the 'arg_tid':
        # NOTE: arg kind depends on arg count:
        # - if 0 args, arg kind is trivially unit
        # - if 2 or more args, arg kind is trivially tuple
        # - if 1 arg, arg type is just that arg's type.
        actual_arg_tid = None
        if not exp.arg_names:
            actual_arg_tid = type.get_unit_type()
        else:
            elem_arg_tid_list = []
            for i, arg_name in enumerate(exp.arg_names):
                actual_arg_tid = type.new_free_var(f"lambda-formal-arg:{arg_name}")
                arg_def_obj = definition.ValueRecord(exp.loc, actual_arg_tid)
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
        ret_sub, ret_tid = infer_exp_tid(lambda_ctx, exp.body)

        # reading the side-effects specifier from the expression:
        ses = type.side_effects.SES.Tot
        if exp.opt_ses is not None:
            ses = exp.opt_ses

        # now, the type of the lambda is the type of the function that accepts the given args and returns the specified
        # return expression:
        fn_tid = type.get_fn_type(actual_arg_tid, ret_tid, ses)
        return ret_sub, fn_tid

    # TODO: type a chain expression
    elif isinstance(exp, ast.node.ChainExp):
        raise NotImplementedError("Type inference for chain expressions")

    # TODO: type an 'if' expression:
    elif isinstance(exp, ast.node.IfExp):
        pass

    else:
        raise NotImplementedError(f"Type inference for {exp.__class__.__name__}")


def infer_type_spec_tid(
        ctx: context.Context, ts: ast.node.BaseTypeSpec
) -> Tuple[substitution.Substitution, type.identity.TID]:
    if isinstance(ts, ast.node.IdTypeSpec):
        found_def_obj = ctx.lookup(ts.name)
        # TODO: validate that the found definition is in the right universe.
        if found_def_obj is not None:
            sub, def_tid = found_def_obj.scheme.instantiate()
            return sub, def_tid
        else:
            raise excepts.TyperCompilationError(f"Symbol {ts.name} used but not defined.")

    raise NotImplementedError(f"Type inference for {ts.__class__.__name__}")


def raise_cast_error(src_tid, dst_tid, more=None):
    spell_src = type.spelling.of(src_tid)
    spell_dst = type.spelling.of(dst_tid)
    msg_suffix = f"Cannot cast to {spell_dst} from {spell_src}"
    if more is not None:
        msg_suffix += f": {more}"
    raise excepts.TyperCompilationError(msg_suffix)
