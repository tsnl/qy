"""
Types
- nominal type system (i.e. t1 == t2 <=> id(t1) == id(t2))
"""

import abc
import sys
import enum
import math
import typing as t

from . import feedback as fb


class TypeKind(enum.Enum):
    Var_Bound = enum.auto()
    Var = enum.auto()
    Void = enum.auto()
    String = enum.auto()
    Int = enum.auto()
    Float = enum.auto()
    Pointer = enum.auto()
    Procedure = enum.auto()
    Struct = enum.auto()
    Union = enum.auto()


class BaseType(object, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __str__(self) -> str:
        return self.text

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, o: object) -> bool:
        return self is o

    def __hash__(self) -> int:
        return id(self)

    @property
    def is_concrete(self):
        return isinstance(self, BaseConcreteType)

    @property
    def is_composite(self):
        return isinstance(self, BaseCompositeType)

    @property
    def is_var(self):
        return isinstance(self, VarType)

    @property
    def is_atomic(self):
        return isinstance(self, AtomicConcreteType)

    @classmethod
    @abc.abstractmethod
    def kind(cls):
        pass

    def iter_free_vars(self):
        return iter(())


#
# TypeVars:
#

class VarType(BaseType):
    def __init__(self, name: str, opt_loc: t.Optional[fb.ILoc] = None) -> None:
        super().__init__()
        self.name = name
        self.opt_loc = opt_loc

    def __str__(self) -> str:
        return '\'' + self.name + '#' + get_id_str_suffix(self)

    @classmethod
    def kind(cls):
        return TypeKind.Var

    def iter_free_vars(self):
        # assume every Var is free, as though the symbol is written on its own.
        yield self


#
# Concrete Types:
#

class BaseConcreteType(BaseType):
    pass


class AtomicConcreteType(BaseConcreteType):
    pass


class VoidType(AtomicConcreteType):
    singleton = None

    def __str__(self) -> str:
        return "void"

    @classmethod
    def kind(cls):
        return TypeKind.Void


VoidType.singleton = VoidType()


class StringType(AtomicConcreteType):
    singleton = None

    def __str__(self) -> str:
        return "str"
    
    @classmethod
    def kind(cls):
        return TypeKind.String


StringType.singleton = StringType()


class IntType(AtomicConcreteType):
    cache = {}

    def __init__(self, width_in_bits: int, is_signed: bool) -> None:
        """
        Do not invoke this constructor directly.
        """

        super().__init__()
        self.width_in_bits = width_in_bits
        self.is_signed = is_signed

    def __str__(self) -> str:
        if self.width_in_bits == 1 and not self.is_signed:
            return 'bool'
        else:
            return ('i' if self.is_signed else 'u') + str(self.width_in_bits)

    @staticmethod
    def get(width_in_bits: int, is_signed: bool) -> "IntType":
        key = (width_in_bits, is_signed)
        opt_cached_type = IntType.cache.get(key, None)
        if opt_cached_type is not None:
            return opt_cached_type
        else:
            new_cached_type = IntType(width_in_bits, is_signed)
            IntType.cache[key] = new_cached_type
            return new_cached_type

    @classmethod
    def kind(cls):
        return TypeKind.Int


class FloatType(AtomicConcreteType):
    cache = {}

    def __init__(self, width_in_bits: int) -> None:
        assert width_in_bits in (32, 64)
        super().__init__()
        self.width_in_bits = width_in_bits

    def __str__(self) -> str:
        return 'f' + str(self.width_in_bits)

    @staticmethod
    def get(width_in_bits: int) -> "FloatType":
        key = width_in_bits
        opt_cached_type = FloatType.cache.get(key, None)
        if opt_cached_type is not None:
            return opt_cached_type
        else:
            new_cached_type = FloatType(width_in_bits)
            FloatType.cache[key] = new_cached_type
            return new_cached_type

    @classmethod
    def kind(cls):
        return TypeKind.Float


class BaseCompositeType(BaseConcreteType):
    """
    subclasses must preserve the same '__init__.py' signature.
    """

    def __init__(self, fields: t.List[t.Tuple[str, BaseType]], opt_name=None) -> None:
        assert isinstance(fields, list)
        assert ((isinstance(field_name, str) and isinstance(field_type, BaseType) for field_name, field_type in fields))

        super().__init__()
        self.fields = fields
        self.field_names, self.field_types = zip(*self.fields)
        self.opt_name = opt_name

    def copy_with_elements(self, new_elements: t.List[BaseType]) -> "BaseCompositeType":
        return self.__class__(new_elements)

    @classmethod
    def has_user_defined_field_names(cls) -> bool:
        return False

    def iter_free_vars(self):
        for field_type in self.field_types:
            yield from field_type.iter_free_vars()

    def __hash__(self) -> int:
        return hash((self.__class__, *self.field_types))

    def __eq__(self, o: object) -> bool:
        return self.kind == o.kind and self.fields == o.fields



class PointerType(BaseConcreteType):
    def __init__(self, pointee_type: BaseConcreteType) -> None:
        super().__init__([('pointee', pointee_type)])

    @property
    def pointee_type(self):
        return self.elements[0]

    def __str__(self) -> str:
        return f"&{self.pointee_type}"

    @staticmethod
    def new(pointee_type: BaseConcreteType):
        return PointerType([pointee_type])

    @classmethod
    def kind(cls):
        return TypeKind.Pointer


class ProcedureType(BaseCompositeType):
    @property
    def ret_type(self):
        _, ret_type = self.fields[0]
        return ret_type

    @property
    def arg_count(self):
        return len(self.fields) - 1

    def arg_type(self, index):
        _, arg_type = self.fields[1 + index]
        return arg_type

    @property
    def arg_types(self) -> t.Iterable[BaseType]:
        return (
            self.arg_type(i)
            for i in range(self.arg_count)
        )

    def __str__(self) -> str:
        return f"({','.join(map(str, self.arg_types))})=>{self.ret_type}"

    @staticmethod
    def new(arg_types: t.Iterable[BaseConcreteType], ret_type: BaseConcreteType) -> "ProcedureType":
        return ProcedureType(
            [('ret_type', ret_type)] +
            [(f'arg.{i}', arg_type) for i, arg_type in enumerate(arg_types)]
        )

    @classmethod
    def kind(cls):
        return TypeKind.Procedure


class BaseAlgebraicType(BaseCompositeType):
    @abc.abstractclassmethod
    def prefix(cls):
        pass

    @classmethod
    def has_user_defined_field_names(cls) -> bool:
        return True

    def __str__(self) -> str:
        if self.opt_name is None:
            body_text = ','.join((f"{field_name}:{field_type}" for field_name, field_type in self.fields))
            id_suffix = get_id_str_suffix(self)
            return f"{self.prefix()}#{id_suffix}{{{body_text}}}"
        else:
            return self.opt_name


class StructType(BaseAlgebraicType):
    def prefix(cls):
        return "struct"

    @classmethod
    def kind(cls):
        return TypeKind.Struct


class UnionType(BaseAlgebraicType):
    def prefix(cls):
        return "union"

    @classmethod
    def kind(cls):
        return TypeKind.Union


def get_id_str_suffix(it, id_suffix_w=4):
    trimmed_number = id(it)//word_size_in_bytes % 0x10**id_suffix_w
    return hex(trimmed_number)[2:].rjust(id_suffix_w, '0')


word_size_in_bits = int(1+math.log2(sys.maxsize))
word_size_in_bytes = word_size_in_bits // 8
