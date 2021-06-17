from qcl import type
from qcl import excepts

from . import substitution


def unify(t: type.identity.TID, u: type.identity.TID):
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

        if type.free.occurs(rewritten_type, var_type):
            raise excepts.TyperCompilationError("unification failed: occurs check failed")

        return substitution.Substitution({var_type: rewritten_type})

    #
    # other types: return appropriate substitution:
    #

    else:
        # since we cache to guarantee each structurally unique type is mapped to only one ID,
        # we only need to check that the two IDs are equal to verify they are structurally equal too.
        if t == u:
            return substitution.empty

        # two compound types may share the same structure, but different element types.
        # we unify these here.

        tk_t = type.kind.of(t)
        tk_u = type.kind.of(u)

        if tk_t == tk_u == type.kind.TK.Fn:
            # FIXME: if either side-effect-specifier of a function is `Elim_?`, we currently do nothing.
            #   - cannot substitute a function for another function, only var for another var
            #   - may be able to rename SES, but that would violate unique TID per structural type
            #   - perhaps can bundle into basic-check-style post-check

            s1 = unify(type.elem.tid_of_fn_arg(t), type.elem.tid_of_fn_arg(u))
            s2 = unify(s1.rewrite_type(type.elem.tid_of_fn_ret(t)), s1.rewrite_type(type.elem.tid_of_fn_ret(u)))

            return s1.compose(s2)

        elif tk_t == tk_u and tk_t in (type.kind.TK.Tuple, type.kind.TK.Struct, type.kind.TK.Enum, type.kind.TK.Union):
            t_len = type.elem.count(t)
            u_len = type.elem.count(u)

            if t_len != u_len:
                raise_unification_error(t, u, f"cannot unify {t_len}-tuple and {u_len}-tuple")

            assert t_len == u_len
            sub = substitution.empty
            for i in range(t_len):
                if tk_t != type.kind.TK.Tuple:
                    t_elem_name = type.elem.field_name_at_ix(t, i)
                    u_elem_name = type.elem.field_name_at_ix(t, i)

                    assert t_elem_name and u_elem_name

                    if t_elem_name != u_elem_name:
                        raise_unification_error(t, u)

                t_elem_tid = type.elem.tid_of_field_ix(t, i)
                u_elem_tid = type.elem.tid_of_field_ix(u, i)
                elem_sub = unify(t_elem_tid, u_elem_tid)
                sub = sub.compose(elem_sub)

            return sub

        elif tk_t == tk_u and tk_t in (type.kind.TK.Pointer, type.kind.TK.Array, type.kind.TK.Slice):
            return unify(type.elem.tid_of_ptd(t), type.elem.tid_of_ptd(u))

        else:
            raise_unification_error(t, u)


def is_var(tid: type.identity.TID):
    return type.kind.of(tid) in (type.kind.TK.BoundVar, type.kind.TK.FreeVar)


def raise_unification_error(t, u, opt_msg=""):
    spell_t = type.spelling.of(t)
    spell_u = type.spelling.of(u)

    message = f"unification error: cannot unify {spell_t} and {spell_u}"
    if opt_msg:
        message += f": {opt_msg}"

    raise excepts.TyperCompilationError(message)
