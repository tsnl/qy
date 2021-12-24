"""
`ast1` represents the contents of a single Qy source file.
"""

import abc
import typing as t
import enum
from collections import defaultdict

from qcl import common

from . import feedback as fb

#
#
# Helpers:
#
#

OptStr = t.Optional[str]


#
#
# Constants:
#
#

class UnaryOperator(enum.Enum):
    DeRef = enum.auto()
    LogicalNot = enum.auto()
    Minus = enum.auto()
    Plus = enum.auto()


class BinaryOperator(enum.Enum):
    Mul = enum.auto()
    Div = enum.auto()
    Mod = enum.auto()
    Add = enum.auto()
    Sub = enum.auto()
    LSh = enum.auto()
    RSh = enum.auto()
    LThan = enum.auto()
    GThan = enum.auto()
    LEq = enum.auto()
    GEq = enum.auto()
    Eq = enum.auto()
    NEq = enum.auto()
    BitwiseAnd = enum.auto()
    BitwiseXOr = enum.auto()
    BitwiseOr = enum.auto()
    LogicalAnd = enum.auto()
    LogicalOr = enum.auto()


class BuiltinPrimitiveTypeIdentity(enum.Enum):
    Float32 = enum.auto()
    Float64 = enum.auto()
    Int64 = enum.auto()
    Int32 = enum.auto()
    Int16 = enum.auto()
    Int8 = enum.auto()
    UInt64 = enum.auto()
    UInt32 = enum.auto()
    UInt16 = enum.auto()
    UInt8 = enum.auto()
    Bool = enum.auto()
    Void = enum.auto()
    String = enum.auto()


class LinearTypeOp(enum.Enum):
    Product = enum.auto()
    Sum = enum.auto()


#
#
# Base classes and mixins:
#
#

class BaseFileNode(object, metaclass=abc.ABCMeta):
    def __init__(self, loc: fb.ILoc):
        super().__init__()
        self.loc = loc
        self.wb_ctx = None

    @property
    def desc(self):
        return self.__class__.__name__


class WbTypeMixin(common.Mixin):
    all = []
    
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.wb_type = None

        WbTypeMixin.all.append(self)

    @staticmethod
    def apply_sub_everywhere(sub):
        for ast_node in WbTypeMixin.all:
            if ast_node.wb_type is not None:
                ast_node.wb_type = sub.rewrite_type(ast_node.wb_type)


class BaseTypeSpec(WbTypeMixin, BaseFileNode):
    def __init__(self, loc: fb.ILoc):
        super().__init__(loc)


class BaseExpression(WbTypeMixin, BaseFileNode):
    def __init__(self, loc: fb.ILoc):
        super().__init__(loc)


class BaseStatement(BaseFileNode):
    def __init__(self, loc: fb.ILoc):
        super().__init__(loc)


class MIdQualifierNode(common.Mixin):
    def __init__(self, name: str, *args, **kwargs) -> None:
        assert isinstance(self, BaseFileNode)
        super().__init__(*args, **kwargs)
        self.name = name

    def lookup_def_obj(self):
        assert self.wb_ctx is not None
        res = self.wb_ctx.try_lookup(self.name)
        assert res is not None
        return res



#
#
# Statements:
#
#

class BaseIdQualifierStatement(MIdQualifierNode, BaseStatement):
    def __init__(self, loc: fb.ILoc, name: str):
        super().__init__(name, loc)


class Bind1vStatement(BaseIdQualifierStatement):
    def __init__(self, loc: fb.ILoc, name: str, initializer: BaseExpression):
        super().__init__(loc, name)
        self.initializer = initializer


class Bind1fStatement(BaseIdQualifierStatement):
    def __init__(self, loc: fb.ILoc, name: str, args: t.List[str], body: t.List[BaseStatement]):
        super().__init__(loc, name)
        self.args = args
        self.body = body


class Bind1tStatement(BaseIdQualifierStatement):
    def __init__(self, loc: fb.ILoc, name: str, initializer: BaseTypeSpec):
        super().__init__(loc, name)
        self.initializer = initializer


class Type1vStatement(BaseIdQualifierStatement):
    def __init__(self, loc: fb.ILoc, name: str, ts: BaseTypeSpec, is_export_line: bool):
        super().__init__(loc, name)
        self.ts = ts
        self.is_export_line = is_export_line


class ConstStatement(BaseStatement):
    def __init__(self, loc: fb.ILoc, body: t.List[BaseStatement], const_type_spec: "BaseTypeSpec"):
        super().__init__(loc)
        self.loc = loc
        self.body = body
        self.const_type_spec = const_type_spec


class IteStatement(BaseStatement):
    def __init__(
        self,
        loc: fb.ILoc,
        cond: BaseExpression,
        then_block: t.List[BaseStatement],
        else_block: t.List[BaseStatement]
    ):
        super().__init__(loc)
        self.cond = cond
        self.then_block = then_block
        self.else_block = else_block


class ReturnStatement(BaseStatement):
    def __init__(self, loc, returned_exp: BaseExpression):
        super().__init__(loc)
        self.returned_exp = returned_exp


#
#
# Expressions:
#
#

class BaseNumberExpression(BaseExpression):
    def __init__(self, loc: fb.ILoc, text: str, value: t.Union[int, float], width_in_bits: int):
        super().__init__(loc)
        self.text = text
        self.value = value
        self.width_in_bits = width_in_bits


class IntExpression(BaseNumberExpression):
    def __init__(
            self,
            loc: fb.ILoc,
            text: str,
            value: int,
            base: int,
            is_unsigned: bool,
            width_in_bits: int = 32
    ):
        super().__init__(loc, text, value, width_in_bits)
        self.value: int
        self.text_base = base
        self.is_unsigned = is_unsigned
        # print("IntExpression:", self.text)


class FloatExpression(BaseNumberExpression):
    def __init__(self, loc: fb.ILoc, text: str, value: float, width_in_bits=64):
        super().__init__(loc, text, value, width_in_bits)
        self.value: float
        # print("FloatExpression:", self.text)


class StringExpression(BaseExpression):
    def __init__(self, loc: fb.ILoc, pieces: t.List[str], value: str):
        super().__init__(loc)
        self.pieces = pieces
        self.value = value
        # print("StringExpression:", self.pieces, repr(self.value))


class BuiltinConPrevExpression(BaseExpression):
    pass


class IdRefExpression(MIdQualifierNode, BaseExpression):
    def __init__(self, loc: fb.ILoc, name: str):
        super().__init__(name, loc)


class ProcCallExpression(BaseExpression):
    def __init__(self, loc: fb.ILoc, proc: BaseExpression, arg_exps: t.List[BaseExpression]):
        super().__init__(loc)
        self.proc = proc
        self.arg_exps = arg_exps


class ConstructorExpression(BaseExpression):
    def __init__(self, loc: fb.ILoc, made_ts: BaseTypeSpec, initializer_list: t.List[BaseExpression]):
        super().__init__(loc)
        self.made_ts = made_ts
        self.initializer_list = initializer_list


class DotIdExpression(BaseExpression):
    def __init__(self, loc: fb.ILoc, container: BaseExpression, key: str):
        super().__init__(loc)
        self.container = container
        self.key = key


class UnaryOpExpression(BaseExpression):
    def __init__(self, loc: fb.ILoc, operator: UnaryOperator, operand: BaseExpression):
        super().__init__(loc)
        self.operator = operator
        self.operand = operand


class BinaryOpExpression(BaseExpression):
    def __init__(self, loc: fb.ILoc, operator: BinaryOperator, lt_operand: BaseExpression, rt_operand: BaseExpression):
        super().__init__(loc)
        self.operator = operator
        self.lt_operand = lt_operand
        self.rt_operand = rt_operand


#
#
# Type specifiers:
#
#

class IdRefTypeSpec(MIdQualifierNode, BaseTypeSpec):
    def __init__(self, loc: fb.ILoc, name: str):
        super().__init__(name, loc)


class BuiltinPrimitiveTypeSpec(BaseTypeSpec):
    def __init__(self, loc: fb.ILoc, identity: BuiltinPrimitiveTypeIdentity):
        super().__init__(loc)
        self.identity = identity

    @property
    def is_unsigned_int(self) -> bool:
        return self.identity in {
            BuiltinPrimitiveTypeIdentity.UInt8,
            BuiltinPrimitiveTypeIdentity.UInt16,
            BuiltinPrimitiveTypeIdentity.UInt32,
            BuiltinPrimitiveTypeIdentity.UInt64
        }

    @property
    def int_width_in_bits(self) -> t.Optional[int]:
        return {
            BuiltinPrimitiveTypeIdentity.Int8: 8,
            BuiltinPrimitiveTypeIdentity.Int16: 16,
            BuiltinPrimitiveTypeIdentity.Int32: 32,
            BuiltinPrimitiveTypeIdentity.Int64: 64,
            BuiltinPrimitiveTypeIdentity.UInt8: 8,
            BuiltinPrimitiveTypeIdentity.UInt16: 16,
            BuiltinPrimitiveTypeIdentity.UInt32: 32,
            BuiltinPrimitiveTypeIdentity.UInt64: 64
        }.get(self.identity, None)


class AdtTypeSpec(BaseTypeSpec):
    def __init__(self, loc: fb.ILoc, linear_op: LinearTypeOp, args: t.List[t.Tuple[OptStr, BaseTypeSpec]]):
        super().__init__(loc)
        self.linear_op = linear_op
        self.fields_list = args
        self.fields_dict = {
            arg_pair[0]: arg_pair[1]
            for arg_pair in args
            if arg_pair[0] is not None
        }


class PtrTypeSpec(BaseTypeSpec):
    def __init__(self, loc: fb.ILoc, pointee_type_spec: BaseTypeSpec, is_mut: bool):
        super().__init__(loc)
        self.pointee_type_spec = pointee_type_spec
        self.is_mut = is_mut


class ProcSignatureTypeSpec(BaseTypeSpec):
    def __init__(self, loc: fb.ILoc, args: t.List[t.Tuple[OptStr, BaseTypeSpec]], ret_ts: BaseTypeSpec):
        super().__init__(loc)
        self.args_list = args
        self.ret_ts = ret_ts
