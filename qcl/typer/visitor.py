from qcl.antlr import BaseVisitor


class TyperVisitor(BaseVisitor):
    """
    This visitor returns a `(context, type)` tuple for each relevant kind of AST node.
    The context returned in the end details the type of various expressions.
    """
