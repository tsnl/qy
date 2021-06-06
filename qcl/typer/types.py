import enum


class TypeKind(enum.Enum):
    Unit = enum.auto()
    String = enum.auto()
    Int = enum.auto()
    Float = enum.auto()
    Func = enum.auto()
    Struct = enum.auto()
    Enum = enum.auto()
    Union = enum.auto()
    Tuple = enum.auto()
    Module = enum.auto()
    FreeVar = enum.auto()
    BoundVar = enum.auto()
