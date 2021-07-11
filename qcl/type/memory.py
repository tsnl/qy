import enum

from . import identity


class RelMemLoc(enum.Enum):
    """
    RelMemLoc denotes where a pointer's memory is stored. It is only returned for memory window types.
    It is used to identify if assignment is `Tot` (to the local stack) or `ST` (to non-local stack/heap)
    - most expressions are stored on the stack, locally
    - IDs refer to data that may be stored on the stack, either locally or non-locally, or in the heap as a global
      variable.
    We use two simplified states, since we only need to decide if `:=` is TOT (for stack-local) or ST (otherwise).
    """

    StackLocal = enum.auto()
    HeapOrStackNonLocal = enum.auto()


class ClosureSpec(enum.Enum):
    """
    ClosureSpec is used by functions to specify whether non-locals can be passed via an extra 'context' pointer.
    """

    No = enum.auto()
    Yes = enum.auto()

    # `Maybe` unifies with both `No` and `Yes`, and is used for lambdas that may be converted to either.
    Maybe = enum.auto()


fn_closure_spec_table = {}


def init_func(fn_tid: "identity.TID", closure_spec: ClosureSpec):
    fn_closure_spec_table[fn_tid] = closure_spec


def closure_spec(fn_tid: "identity.TID"):
    return fn_closure_spec_table[fn_tid]
