from . import identity
from . import elem
from . import scalar_width_in_bits
from . import mem_window
from . import kind
from . import side_effects

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
        return f"I{scalar_width_in_bits.of(tid)}"
    elif type_kind == kind.TK.UnsignedInt:
        return f"U{scalar_width_in_bits.of(tid)}"
    elif type_kind == kind.TK.Float:
        return f"F{scalar_width_in_bits.of(tid)}"

    elif type_kind == kind.TK.Pointer:
        if mem_window.is_mut(tid):
            return f"![{of(elem.tid_of_ptd(tid))}]"
        else:
            return f"[{of(elem.tid_of_ptd(tid))}]"
    elif type_kind == kind.TK.Array:
        if mem_window.is_mut(tid):
            return f"![{of(elem.tid_of_ptd(tid))}, N_{tid}]"
        else:
            return f"[{of(elem.tid_of_ptd(tid))}, N_{tid}]"
    elif type_kind == kind.TK.Slice:
        if mem_window.is_mut(tid):
            return f"![{of(elem.tid_of_ptd(tid))}, ?]"
        else:
            return f"[{of(elem.tid_of_ptd(tid))}, ?]"

    elif type_kind == kind.TK.Fn:
        lhs_spelling = of(elem.tid_of_fn_arg(tid))
        rhs_spelling = of(elem.tid_of_fn_ret(tid))
        ses_spelling = of_ses(side_effects.of(tid))

        # if lhs_spelling[0] != '(':
        #     lhs_spelling = f"({lhs_spelling})"

        return f"{lhs_spelling} -> {ses_spelling} {rhs_spelling}"

    elif type_kind in (kind.TK.Struct, kind.TK.Union, kind.TK.Module):
        prefix_keyword_map = {
            kind.TK.Struct: "Struct",
            kind.TK.Union: "Union",
            kind.TK.Module: "Module"
        }

        elem_count = elem.count(tid)
        prefix_keyword = prefix_keyword_map[type_kind]

        if elem_count > 0:
            field_text_iterator = (
                f"{elem.field_name_at_ix(tid, i)}"
                f"{' = ' if elem.is_type_field_at_field_ix(tid, i) else ': '}"
                f"{of(elem.tid_of_field_ix(tid, i))}"
                for i in range(elem_count)
            )
            return f"{prefix_keyword} {{ {'; '.join(field_text_iterator)} }}"
        else:
            return f"{prefix_keyword} {{}}"

    elif type_kind in (kind.TK.BoundVar, kind.TK.FreeVar):
        return f"{tid}:{var_names[tid]}"

    elif type_kind == kind.TK.Tuple:
        content = ', '.join((of(elem.tid_of_field_ix(tid, i)) for i in range(elem.count(tid))))
        return f"({content})"

    else:
        raise NotImplementedError(f"`spell` for type of kind {type_kind}")


def of_ses(ses: side_effects.SES):
    return {
        side_effects.SES.Tot: "TOT",
        side_effects.SES.Dv: "DV",
        side_effects.SES.ST: "ST",
        side_effects.SES.Exn: "EXN",
        side_effects.SES.ML: "ML",
        side_effects.SES.Elim_AnyNonTot: "<AnyNonTot>"
    }.get(ses, "?")
