import enum

from qcl.type import identity


class CS(enum.Enum):
    """
    ClosureSpec is used by functions to specify whether non-locals can be passed via an extra 'context' pointer.
    """

    No = enum.auto()
    Yes = enum.auto()

    # `Maybe` unifies with both `No` and `Yes`, and is used for lambdas that may be converted to either.
    Maybe = enum.auto()


fn_closure_spec_table = {}


def init_func(fn_tid: "identity.TID", closure_spec: CS):
    fn_closure_spec_table[fn_tid] = closure_spec


def of(fn_tid: "identity.TID"):
    try:
        return fn_closure_spec_table[fn_tid]
    except KeyError:
        return CS.Maybe
