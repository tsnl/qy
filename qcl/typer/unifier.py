import functools
import typing as t

from qcl import types
from qcl import excepts

from . import substitution


#
#
# Type-inference functions:
#
#


def unify_tid(t: types.identity.TID, u: types.identity.TID, allow_u_mut_ptr=False):
    # NOTE: `allow_u_mut_ptr` is a hack used to allow `*` to de-reference mutable as well as immutable pointers.

    #
    # trivial unification: identical types
    #

    if t == u:
        return substitution.empty

    #
    # variable elimination:
    #

    t_is_var = is_var(t)
    u_is_var = is_var(u)

    if t_is_var or u_is_var:
        if t_is_var:
            var_type = t
            rewritten_type = u
        else:
            assert u_is_var
            var_type = u
            rewritten_type = t

        # FIXME: we relax the occurs check to ignore `{a: a}` substitutions as a 'pass', BUT
        #   - this could lead to termination errors
        #   - this is required because of cyclic imports
        if types.free.occurs(rewritten_type, var_type):
            var_type_text = types.spelling.of(var_type)
            rewritten_type_text = types.spelling.of(rewritten_type)
            msg_suffix = f"unification failed: occurs check failed: {var_type_text} occurs in {rewritten_type_text}"
            raise excepts.TyperCompilationError(msg_suffix)

        return substitution.Substitution({var_type: rewritten_type})

    #
    # other types: return appropriate substitution:
    #

    else:
        # since we cache to guarantee each structurally unique types is mapped to only one ID,
        # we only need to check that the two IDs are equal to verify they are structurally equal too.
        if t == u:
            return substitution.empty

        # two compound types may share the same structure, but different element types.
        # we unify these here.

        tk_t = types.kind.of(t)
        tk_u = types.kind.of(u)

        if tk_t == tk_u == types.kind.TK.Fn:
            # FIXME: if either side-effect-specifier of a function is `Elim_?`, we currently do nothing.
            #   - cannot substitute a function for another function, only var for another var
            #   - may be able to rename SES, but that would violate unique TID per structural types
            #   - perhaps can bundle into basic-check-style post-check

            # TODO: unify `Cs = ClosureSpec`

            t_ses = types.side_effects.of(t)
            u_ses = types.side_effects.of(u)

            if not ses_are_equal(t_ses, u_ses):
                raise_unification_error(t, u, f"cannot unify two function types with incompatible SES")

            s1 = unify_tid(types.elem.tid_of_fn_arg(t), types.elem.tid_of_fn_arg(u))
            s2 = unify_tid(s1.rewrite_type(types.elem.tid_of_fn_ret(t)), s1.rewrite_type(types.elem.tid_of_fn_ret(u)))

            return s1.compose(s2)

        elif tk_t == tk_u and tk_t in (types.kind.TK.Tuple, types.kind.TK.Struct):
            t_len = types.elem.count(t)
            u_len = types.elem.count(u)

            if t_len != u_len:
                raise_unification_error(t, u, f"cannot unify {t_len}-tuple and {u_len}-tuple")

            assert t_len == u_len
            sub = substitution.empty
            for i in range(t_len):
                if tk_t != types.kind.TK.Tuple:
                    t_elem_name = types.elem.field_name_at_ix(t, i)
                    u_elem_name = types.elem.field_name_at_ix(t, i)

                    assert t_elem_name and u_elem_name

                    if t_elem_name != u_elem_name:
                        raise_unification_error(t, u)

                t_elem_tid = types.elem.tid_of_field_ix(t, i)
                u_elem_tid = types.elem.tid_of_field_ix(u, i)
                elem_sub = unify_tid(t_elem_tid, u_elem_tid)
                sub = sub.compose(elem_sub)

            return sub

        elif tk_t == tk_u and tk_t in (types.kind.TK.Pointer, types.kind.TK.Array, types.kind.TK.Slice):
            t_is_mut = types.mem_window.is_mut(t)
            u_is_mut = types.mem_window.is_mut(u)

            if allow_u_mut_ptr:
                if t_is_mut and not u_is_mut:
                    msg_suffix = "cannot unify mutable `t` with immutable `u` pointer in `*ptr` expression"
                    raise_unification_error(t, u, msg_suffix)
            else:
                if t_is_mut != u_is_mut:
                    msg_suffix = "cannot unify pointers with different mut specifiers"
                    raise_unification_error(t, u, msg_suffix)

            if tk_t == types.kind.TK.Pointer:
                return unify_tid(types.elem.tid_of_ptd(t), types.elem.tid_of_ptd(u))
            else:
                assert tk_t in (types.kind.TK.Array, types.kind.TK.Slice)
                s1 = unify_tid(
                    types.elem.tid_of_ptd(t),
                    types.elem.tid_of_ptd(u)
                )
                s2 = unify_tid(
                    types.elem.tid_of_size(t),
                    types.elem.tid_of_size(u)
                )
                return s2.compose(s1)

        else:
            raise_unification_error(t, u)


def is_var(tid: types.identity.TID):
    return types.kind.of(tid) in (types.kind.TK.BoundVar, types.kind.TK.FreeVar)


def raise_unification_error(t: types.identity.TID, u: types.identity.TID, opt_msg=""):
    spell_t = types.spelling.of(t)
    spell_u = types.spelling.of(u)

    message = f"unification error: cannot unify {spell_t} and {spell_u}"
    if opt_msg:
        message += f": {opt_msg}"

    raise excepts.TyperCompilationError(message)


#
#
# SES-inference helpers:
#
#

SES = types.side_effects.SES


def unify_ses(*ses_iterator):
    return functools.reduce(unify_ses_binary, ses_iterator)
    

def unify_ses_binary(ses1, ses2):
    opt_unified_ses = {
        (types.side_effects.SES.Tot, types.side_effects.SES.Tot): types.side_effects.SES.Tot,
        (types.side_effects.SES.Tot, types.side_effects.SES.Dv): types.side_effects.SES.Dv,
        (types.side_effects.SES.Tot, types.side_effects.SES.ST): types.side_effects.SES.ST,
        (types.side_effects.SES.Tot, types.side_effects.SES.Exn): types.side_effects.SES.Exn,
        (types.side_effects.SES.Tot, types.side_effects.SES.ML): types.side_effects.SES.ML,

        (types.side_effects.SES.Dv, types.side_effects.SES.Tot): types.side_effects.SES.Dv,
        (types.side_effects.SES.Dv, types.side_effects.SES.Dv): types.side_effects.SES.Dv,
        (types.side_effects.SES.Dv, types.side_effects.SES.ST): types.side_effects.SES.ST,
        (types.side_effects.SES.Dv, types.side_effects.SES.Exn): types.side_effects.SES.Exn,
        (types.side_effects.SES.Dv, types.side_effects.SES.ML): types.side_effects.SES.ML,

        (types.side_effects.SES.ST, types.side_effects.SES.Tot): types.side_effects.SES.ST,
        (types.side_effects.SES.ST, types.side_effects.SES.Dv): types.side_effects.SES.ST,
        (types.side_effects.SES.ST, types.side_effects.SES.ST): types.side_effects.SES.ST,
        (types.side_effects.SES.ST, types.side_effects.SES.Exn): types.side_effects.SES.ML,
        (types.side_effects.SES.ST, types.side_effects.SES.ML): types.side_effects.SES.ML,

        (types.side_effects.SES.Exn, types.side_effects.SES.Tot): types.side_effects.SES.Exn,
        (types.side_effects.SES.Exn, types.side_effects.SES.Dv): types.side_effects.SES.Exn,
        (types.side_effects.SES.Exn, types.side_effects.SES.ST): types.side_effects.SES.ML,
        (types.side_effects.SES.Exn, types.side_effects.SES.Exn): types.side_effects.SES.Exn,
        (types.side_effects.SES.Exn, types.side_effects.SES.ML): types.side_effects.SES.ML,

        (types.side_effects.SES.ML, types.side_effects.SES.Tot): types.side_effects.SES.ML,
        (types.side_effects.SES.ML, types.side_effects.SES.Dv): types.side_effects.SES.ML,
        (types.side_effects.SES.ML, types.side_effects.SES.ST): types.side_effects.SES.ML,
        (types.side_effects.SES.ML, types.side_effects.SES.Exn): types.side_effects.SES.ML,
        (types.side_effects.SES.ML, types.side_effects.SES.ML): types.side_effects.SES.ML,

        (types.side_effects.SES.Elim_AnyNonTot, types.side_effects.SES.Tot): types.side_effects.SES.Elim_AnyNonTot,
        (types.side_effects.SES.Elim_AnyNonTot, types.side_effects.SES.Dv): types.side_effects.SES.Dv,
        (types.side_effects.SES.Elim_AnyNonTot, types.side_effects.SES.Exn): types.side_effects.SES.Exn,
        (types.side_effects.SES.Elim_AnyNonTot, types.side_effects.SES.ST): types.side_effects.SES.ST,
        (types.side_effects.SES.Elim_AnyNonTot, types.side_effects.SES.ML): types.side_effects.SES.ML,

        (types.side_effects.SES.Tot, types.side_effects.SES.Elim_AnyNonTot): types.side_effects.SES.Elim_AnyNonTot,
        (types.side_effects.SES.Dv, types.side_effects.SES.Elim_AnyNonTot): types.side_effects.SES.Dv,
        (types.side_effects.SES.Exn, types.side_effects.SES.Elim_AnyNonTot): types.side_effects.SES.Exn,
        (types.side_effects.SES.ST, types.side_effects.SES.Elim_AnyNonTot): types.side_effects.SES.ST,
        (types.side_effects.SES.ML, types.side_effects.SES.Elim_AnyNonTot): types.side_effects.SES.ML
    }[ses1, ses2]
    if opt_unified_ses is not None:
        return opt_unified_ses
    else:
        msg_suffix = f"SES unification error: {ses1} U {ses2}"
        raise excepts.TyperCompilationError(msg_suffix)


def compare_ses(top_allowed_ses: "types.side_effects.SES", compared_ses: "types.side_effects.SES"):
    if top_allowed_ses == types.side_effects.SES.Tot:
        return compared_ses == types.side_effects.SES.Tot
    else:
        if compared_ses == types.side_effects.SES.Elim_AnyNonTot:
            return True
        elif top_allowed_ses == types.side_effects.SES.Dv:
            return compared_ses in (types.side_effects.SES.Tot, types.side_effects.SES.Dv)
        elif top_allowed_ses == types.side_effects.SES.Exn:
            return compared_ses in (types.side_effects.SES.Tot, types.side_effects.SES.Dv, types.side_effects.SES.Exn)
        elif top_allowed_ses == types.side_effects.SES.ST:
            return compared_ses in (types.side_effects.SES.Tot, types.side_effects.SES.Dv, types.side_effects.SES.ST)
        elif top_allowed_ses == types.side_effects.SES.ML:
            return compared_ses in (
                types.side_effects.SES.Tot,
                types.side_effects.SES.Dv,
                types.side_effects.SES.ST,
                types.side_effects.SES.ML
            )
        else:
            raise excepts.CompilationError("Unknown side-effects specifier in `compare_ses`")


type_ = types


def ses_are_equal(ses1: "type_.side_effects.SES", ses2: "type_.side_effects.SES"):
    if ses1 == SES.Elim_AnyNonTot:
        return ses2 == SES.Elim_AnyNonTot or ses2 != SES.Tot
    else:
        return ses1 == ses2

