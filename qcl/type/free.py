from . import identity
from . import kind
from . import elem


def occurs(container_tid: identity.TID, var_id: identity.TID) -> bool:
    c_kind = kind.of(container_tid)
    v_kind = kind.of(var_id)

    assert v_kind in (kind.TK.FreeVar, kind.TK.BoundVar)

    if container_tid == var_id:
        return True
    else:
        compound_tk_set = {
            kind.TK.Fn, kind.TK.Tuple,
            kind.TK.Struct, kind.TK.Union,
            kind.TK.Module
        }
        if c_kind in compound_tk_set:
            return any((
                occurs(elem.tid_of_field_ix(container_tid, i), var_id)
                for i in range(elem.count(container_tid))
            ))

        return False
