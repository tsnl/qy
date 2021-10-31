"""
`ast1` represents the contents of a single Qy source file.
"""

import abc

from . import feedback as fb


class BaseFileNode(object, metaclass=abc.ABCMeta):
    def __init__(self, loc: fb.ILoc):
        super().__init__()


class BaseTypeSpec(BaseFileNode):
    pass


class BaseExpression(BaseFileNode):
    pass


class BaseStatement(BaseFileNode):
    pass
