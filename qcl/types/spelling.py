from . import identity
from . import elem
from . import scalar_width_in_bytes
from . import is_mut
from . import kind

VarPrintComponent = str

var_names = {}


def init_var_name(tid: identity.TID, name: str):
    var_names[tid] = name


def of(tid: identity.TID):
    type_kind = kind.of(tid)
    assert type_kind is not None

    if type_kind == kind.TK.Unit:
        return "()"
    elif type_kind == kind.TK.String:
        return "String"

    elif type_kind == kind.TK.SignedInt:
        return f"Int{scalar_width_in_bytes.of(tid)}"
    elif type_kind == kind.TK.UnsignedInt:
        return f"UInt{scalar_width_in_bytes.of(tid)}"
    elif type_kind == kind.TK.Float:
        return f"Float{scalar_width_in_bytes.of(tid)}"

    elif type_kind == kind.TK.Pointer:
        if is_mut.ptr(tid):
            return f"[{of(elem.tid_of_ptd(tid))}]"
        else:
            return f"mut[{of(elem.tid_of_ptd(tid))}]"
    elif type_kind == kind.TK.Array:
        if is_mut.ptr(tid):
            return f"[{of(elem.tid_of_ptd(tid))}, N{tid}]"
        else:
            return f"mut[{of(elem.tid_of_ptd(tid))}, N{tid}]"
    elif type_kind == kind.TK.Slice:
        if is_mut.ptr(tid):
            return f"[{of(elem.tid_of_ptd(tid))}, ?]"
        else:
            return f"mut[{of(elem.tid_of_ptd(tid))}, ?]"

    elif type_kind == kind.TK.Fn:
        lhs_spelling = of(elem.tid_of_fn_arg(tid))
        if lhs_spelling[0] == '(':
            return f"{lhs_spelling} -> {elem.tid_of_fn_ret(tid)}"
        else:
            return f"({lhs_spelling}) -> {elem.tid_of_fn_ret(tid)}"

    elif type_kind in (kind.TK.Struct, kind.TK.Union, kind.TK.Enum):
        prefix_keyword_map = {
            kind.TK.Struct: "Struct",
            kind.TK.Enum: "Enum",
            kind.TK.Union: "Union"
        }

        elem_count = elem.count_elems(tid)
        prefix_keyword = prefix_keyword_map[type_kind]
        field_text_iterator = (
            of(elem.tid_of_field_ix(tid, i))
            for i in range(elem_count)
        )

        return f"{prefix_keyword} {{ {', '.join(field_text_iterator)} }}"

    elif type_kind in (kind.TK.BoundVar, kind.TK.FreeVar):
        return var_names[tid]

    else:
        raise NotImplementedError(f"`spell` for type of kind {type_kind}")
