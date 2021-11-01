"""
`ast1` represents the contents of a single Qy source file.
"""

import abc
import typing as t

from . import feedback as fb


#
#
# Base classes:
#
#

class BaseFileNode(object, metaclass=abc.ABCMeta):
    def __init__(self, loc: fb.ILoc):
        super().__init__()


class BaseTypeSpec(BaseFileNode):
    pass


class BaseExpression(BaseFileNode):
    pass


class BaseStatement(BaseFileNode):
    pass


#
#
# Statements:
#
#

class Bind1vStatement(BaseStatement):
    def __init__(self, loc: fb.ILoc, name: str, initializer: BaseExpression):
        super().__init__(loc)
        self.name = name
        self.initializer = initializer


class Bind1fStatement(BaseStatement):
    def __init__(self, loc: fb.ILoc, name: str, args: t.List[str], body: t.List[BaseStatement]):
        super().__init__(loc)
        self.name = name
        self.args = args
        self.body = body


class Bind1tStatement(BaseStatement):
    def __init__(self, loc: fb.ILoc, name: str, initializer: BaseTypeSpec):
        super().__init__(loc)
        self.name = name
        self.initializer = initializer


class Type1vStatement(BaseStatement):
    def __init__(self, loc: fb.ILoc, name: str, ts: BaseTypeSpec, is_export_line: bool):
        super().__init__(loc)
        self.name = name
        self.ts = ts
        self.is_export_line = is_export_line


class ConstStatement(BaseStatement):
    def __init__(self, loc: fb.ILoc, body: t.List[BaseStatement]):
        super().__init__(loc)
        self.loc = loc
        self.body = body


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
        print("IntExpression:", self.text)


class FloatExpression(BaseNumberExpression):
    def __init__(self, loc: fb.ILoc, text: str, value: float, width_in_bits=64):
        super().__init__(loc, text, value, width_in_bits)
        self.value: float
        print("FloatExpression:", self.text)


class StringExpression(BaseExpression):
    def __init__(self, loc: fb.ILoc, pieces: t.List[str], value: str):
        super().__init__(loc)
        self.pieces = pieces
        self.value = value
