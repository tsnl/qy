"""
Types
- nominal type system (i.e. t1 == t2 <=> id(t1) == id(t2))
"""

import abc
import typing as t

from . import feedback as fb


class BaseType(object, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __str__(self) -> str:
        return self.text

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, o: object) -> bool:
        return self is o

    @property
    def is_concrete(self):
        return isinstance(self, BaseConcreteType)

    @property
    def is_var(self):
        return isinstance(self, BaseVarType)

    @property
    def is_atomic(self):
        return isinstance(self, AtomicConcreteType)


#
# TypeVars:
#

class BaseVarType(BaseType):
    def __init__(self, name: str, opt_loc: t.Optional[fb.ILoc] = None) -> None:
        super().__init__()
        self.name = name
        self.opt_loc = opt_loc

    def __str__(self) -> str:
        return '\'' + self.name


class BoundVarType(BaseVarType):
    pass


class FreeVarType(BaseVarType):
    pass


#
# Concrete Types:
#

class BaseConcreteType(BaseType):
    pass


class AtomicConcreteType(BaseConcreteType):
    pass


class VoidType(AtomicConcreteType):
    def __str__(self) -> str:
        return "void"


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
        return f"{'u' if not self.is_signed else ''}int{self.width_in_bits}"

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


class FloatType(AtomicConcreteType):
    cache = {}

    def __init__(self, width_in_bits: int) -> None:
        assert width_in_bits in (32, 64)
        super().__init__()
        self.width_in_bits = width_in_bits

    def __str__(self) -> str:
        return f"float{self.width_in_bits}"

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


class ProcedureType(BaseCompositeType):
    @property
    def ret_type(self):
        return self.fields[0]
    
    @property
    def arg_count(self):
        return len(self.fields) - 1

    @property
    def arg_type(self, index):
        return self.fields[1 + index]

    @property
    def arg_types(self) -> t.Iterable[BaseType]:
        for i in range(self.arg_count):
            yield self.arg_type(i)

    def __str__(self) -> str:
        return f"({', '.join(self.arg_types)}) => {self.ret_type}"

    @staticmethod
    def new(arg_types: t.Iterable[BaseConcreteType], ret_type: BaseConcreteType):
        return ProcedureType(
            [('ret_type', ret_type)] + 
            [((f'arg.{i}', arg_type) for i, arg_type in enumerate(arg_types))]
        )


class BaseAlgebraicType(BaseCompositeType):
    @abc.abstractclassmethod
    def prefix(cls):
        pass

    def __str__(self) -> str:
        if self.opt_name is None:
            body_text = ','.join((f"{field_name}:{field_type}" for field_name, field_type in self.fields))
            return f"{self.prefix()}.{hex(id(self)//8 % 0x1000)}{{{body_text}}}"
        else:
            return self.opt_name


class StructType(BaseAlgebraicType):
    def prefix(cls):
        return "struct"


class UnionType(BaseAlgebraicType):
    def prefix(cls):
        return "union"
