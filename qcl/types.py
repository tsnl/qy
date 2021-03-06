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


#
# Types:
#

class TypeKind(enum.Enum):
    Var_Bound = enum.auto()
    Var = enum.auto()
    Void = enum.auto()
    Int = enum.auto()
    Float = enum.auto()
    Pointer = enum.auto()
    Procedure = enum.auto()
    Struct = enum.auto()
    Union = enum.auto()
    Array = enum.auto()
    ArrayBox = enum.auto()
    UniqueValue = enum.auto()


class BaseType(object, metaclass=abc.ABCMeta):
    id_counter = 0

    def __init__(self) -> None:
        super().__init__()
        self.id = BaseType.id_counter
        BaseType.id_counter += 1
        
        # common type properties:
        self.is_mut = False

        # optimization cache: computed and cached properties
        self.oc_free_vars = None

    def init_optimization_cache(self):
        self.oc_free_vars = set(self.iter_free_vars())
    
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

    @property
    def is_unique_value(self):
        return isinstance(self, UniqueValueType)

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
        self.init_optimization_cache()

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

class BaseConcreteType(BaseType, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def constructor_arg_type_tuple(self):
        """argument types expected by new/push/heap"""


class AtomicConcreteType(BaseConcreteType):
    def constructor_arg_type_tuple(self):
        return (self,)


class SingletonAtomicConcreteType(AtomicConcreteType):
    def __init__(self) -> None:
        super().__init__()
        self.init_optimization_cache()
        
        # cannot construct a new instance if the singleton slot is already populated.
        assert self.__class__.singleton is None


class VoidType(SingletonAtomicConcreteType):
    singleton = None

    def __str__(self) -> str:
        return "Unit"

    @classmethod
    def kind(cls):
        return TypeKind.Void


VoidType.singleton = VoidType()


class IntType(AtomicConcreteType):
    cache = {}

    def __init__(self, width_in_bits: int, is_signed: bool) -> None:
        """
        Do not invoke this constructor directly.
        """

        super().__init__()
        self.width_in_bits = width_in_bits
        self.is_signed = is_signed
        self.init_optimization_cache()

    def __str__(self) -> str:
        if self.width_in_bits == 1 and not self.is_signed:
            return 'Bool'
        else:
            return ('I' if self.is_signed else 'U') + str(self.width_in_bits)

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
        self.init_optimization_cache()

    def __str__(self) -> str:
        return 'F' + str(self.width_in_bits)

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
    IMPORTANT: subclasses must preserve the same '__init__' signature.
    """

    def __init__(self, fields: t.List[t.Tuple[t.Optional[str], BaseType]], opt_name=None, contents_is_mut=None) -> None:
        assert isinstance(fields, list)
        assert ((isinstance(field_name, (str, type(None))) and isinstance(field_type, BaseType) for field_name, field_type in fields))

        super().__init__()
        self.fields: t.List[t.Tuple[t.Optional[str], BaseType]] = fields
        if len(self.fields) == 1:
            singleton_field_name, singleton_field_type = self.fields[0]
            self.field_names = [singleton_field_name]
            self.field_types = [singleton_field_type]
        else:
            if self.fields:
                self.field_names, self.field_types = zip(*self.fields)
            else:
                self.field_names = []
                self.field_types = []
        
        assert all((isinstance(t, BaseType) for t in self.field_types))
        assert all((isinstance(n, (str, type(None))) for n in self.field_names))
        self.opt_name = opt_name
        self.contents_is_mut = contents_is_mut
        self.init_optimization_cache()

    def copy_with_elements(self, new_elements: t.List[BaseType]) -> "BaseCompositeType":
        # constructing a base type with the same fields:
        copy = self.__class__(new_elements)

        # copying details:
        if isinstance(copy, ProcedureType):
            assert isinstance(self, ProcedureType)
            copy.has_closure_slot = self.has_closure_slot
            copy.is_c_variadic = self.is_c_variadic
        elif isinstance(copy, PointerType):
            assert isinstance(self, PointerType)
            copy.contents_is_mut = self.contents_is_mut
        else:
            pass

        return copy

    @classmethod
    def has_user_defined_field_names(cls) -> bool:
        return False

    def iter_free_vars(self):
        for field_type in self.field_types:
            yield from field_type.iter_free_vars()
    
    def __hash__(self) -> int:
        return hash((self.kind().value, *self.field_types))

    def __eq__(self, o: object) -> bool:
        return self.kind == o.kind and self.fields == o.fields

    def constructor_arg_type_tuple(self):
        return (self,)


class PointerType(BaseCompositeType):
    @property
    def pointee_type(self) -> "BaseType":
        return self.field_types[0]

    def __str__(self) -> str:
        ptr_name = 'MutPtr' if self.contents_is_mut else 'Ptr'
        return f"{ptr_name}[{str(self.pointee_type)}]"

    @staticmethod
    def new(pointee_type: BaseConcreteType, is_mut: bool):
        return PointerType([('pointee', pointee_type)], contents_is_mut=is_mut)

    @classmethod
    def kind(cls):
        return TypeKind.Pointer


class ProcedureType(BaseCompositeType):
    def __init__(self, fields: t.List[t.Tuple[str, BaseType]], opt_name=None, has_closure_slot=None, is_c_variadic=None, contents_is_mut=None) -> None:
        super().__init__(fields, opt_name=opt_name, contents_is_mut=contents_is_mut)
        self.has_closure_slot = has_closure_slot
        self.is_c_variadic = is_c_variadic
    
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
        arrow = '=>' if self.has_closure_slot else '->'
        return f"({','.join(map(str, self.arg_types))}){arrow}{self.ret_type}"

    @staticmethod
    def new(
        arg_types: t.Iterable[BaseConcreteType], 
        ret_type: BaseConcreteType, 
        has_closure_slot: bool = False,
        is_c_variadic: bool = False
    ) -> "ProcedureType":
        pt = ProcedureType(
            [('ret_type', ret_type)] +
            [(f'arg.{i}', arg_type) for i, arg_type in enumerate(arg_types)],
            has_closure_slot=has_closure_slot,
            is_c_variadic=is_c_variadic
        )
        return pt

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

    def constructor_arg_type_tuple(self):
        return tuple(self.field_types)


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


class ArrayType(BaseCompositeType):
    @property
    def element_type(self) -> "BaseType":
        return self.field_types[0]

    @property
    def count_value_encoded_type(self) -> "UniqueValueType":
        return self.field_types[1]
    
    @property
    def count(self):
        return self.count_value_encoded_type.unique_value

    def __str__(self) -> str:
        poly_array_name = 'MutArray' if self.contents_is_mut else 'Array'
        return f"{poly_array_name}[{str(self.element_type)}, {self.count}]"

    @staticmethod
    def new(element_type: BaseConcreteType, count_value_encoding: "UniqueValueType", is_mut: bool):
        assert isinstance(count_value_encoding, UniqueValueType) and isinstance(count_value_encoding.unique_value, int)
        return ArrayType([('element_type', element_type), ('encoded_count', count_value_encoding)], contents_is_mut=is_mut)

    @classmethod
    def kind(cls):
        return TypeKind.Array

    def constructor_arg_type_tuple(self):
        return (self.element_type,)


class ArrayBoxType(BaseCompositeType):
    @property
    def element_type(self) -> "BaseType":
        return self.field_types[0]

    def __str__(self) -> str:
        poly_array_name = 'MutArrayBox' if self.contents_is_mut else 'ArrayBox'
        return f"{poly_array_name}[{str(self.element_type)}]"

    @staticmethod
    def new(element_type: BaseConcreteType, is_mut: bool):
        return ArrayBoxType([('element_type', element_type)], contents_is_mut=is_mut)

    @classmethod
    def kind(cls):
        return TypeKind.ArrayBox

    def constructor_arg_type_tuple(self):
        return (IntType.get(64, is_signed=True),)


class UniqueValueType(BaseType):
    def __init__(self, unique_value: object):
        super().__init__()
        self.unique_value = unique_value

    def __eq__(self, o: object) -> bool:
        return isinstance(o, UniqueValueType) and self.value == o.value

    def __hash__(self) -> int:
        return hash(self.unique_value)
    
    def __str__(self) -> str:
        return str(self.unique_value)

    @classmethod
    def kind(cls):
        return TypeKind.UniqueValue

    def constructor_arg_type_tuple(self):
        raise NotImplementedError("Cannot construct a unique-value-type (using 'new', 'heap', 'push')")


def get_id_str_suffix(it, id_suffix_w=4):
    # trimmed_number = id(it)//word_size_in_bytes % 0x10**id_suffix_w
    # return hex(trimmed_number)[2:].rjust(id_suffix_w, '0')
    trimmed_number = hex(it.id)[2:]
    return trimmed_number
    

word_size_in_bits = int(1+math.log2(sys.maxsize))
word_size_in_bytes = word_size_in_bits // 8

