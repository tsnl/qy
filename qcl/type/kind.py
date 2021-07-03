import enum
from typing import *

from . import identity

kinds: Dict[identity.TID, "KindComponent"] = {}


def init(tid: identity.TID, type_kind: "TK"):
    kinds[tid] = type_kind


def of(tid: identity.TID) -> "TK":
    return kinds[tid]


@enum.unique
class TK(enum.Enum):
    Unit = enum.auto()
    String = enum.auto()
    SignedInt = enum.auto()
    UnsignedInt = enum.auto()
    Float = enum.auto()
    Pointer = enum.auto()
    Array = enum.auto()
    Slice = enum.auto()
    Fn = enum.auto()
    Tuple = enum.auto()
    Struct = enum.auto()
    Union = enum.auto()
    Module = enum.auto()
    FreeVar = enum.auto()
    BoundVar = enum.auto()


KindComponent = TK
