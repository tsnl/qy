"""
In practice, we can view effects-specifiers as a property of the function type.
This is because an effects-specifier can be used either to qualify a lambda's return or within a chain to qualify a
sub-chain.
When used within a sub-chain, the effect-specifier is validated against the parent chain's effect-specifier,
**just like an assignment expression, an allocator, or a throw statement**.
Thus, in correct code, the most general effects-specifier bubbles up inductively to the function return type.
Upon execution, the function upholds the specified effects until it returns.
"""

import enum
from typing import *

from . import identity
from . import kind


@enum.unique
class SES(enum.Enum):
    """
    SES = Side-Effects Specifier
    """
    Tot = enum.auto()
    Dv = enum.auto()
    ST = enum.auto()
    Exn = enum.auto()
    ML = enum.auto()
    Elim_AnyNonTot = enum.auto()


side_effects: Dict[identity.TID, SES] = {}


def init(fn_tid: identity.TID, ses: SES):
    assert kind.of(fn_tid) == kind.TK.Fn
    side_effects[fn_tid] = ses


def of(fn_tid: identity.TID):
    return side_effects[fn_tid]
