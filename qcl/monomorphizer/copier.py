"""
This module copies AST nodes into MAST nodes with some mandatory substitutions applied (monomorphization).
Since the result of this substitution is pure, this is performed in a lazy/caching way.
"""

import abc
import typing as t

from qcl import ast

from . import mast


def copy_sub_mod_with_args(sub_mod_exp: "ast.node.SubModExp", actual_args: t.List["BaseActualArg"]):
    if not sub_mod_exp.template_arg_names:
        return copy_monomorphic_sub_mod_with_args(sub_mod_exp)
    else:
        return copy_polymorphic_sub_mod_with_args(sub_mod_exp, actual_args)


def copy_monomorphic_sub_mod_with_args(sub_mod_exp: "ast.node.SubModExp") -> mast.MastSubModExp:
    """
    TODO: implement me!
    Since the input sub-module is monomorphic, we can directly cache all arguments.
    :param sub_mod_exp: the `sub_mod_exp` instance to cache
    :return: the monomorphic version of this sub-mod-exp
    """


def copy_polymorphic_sub_mod_with_args(sub_mod_exp: "ast.node.SubModExp"):
    pass


class BaseActualArg(object, metaclass=abc.ABCMeta):
    pass


class ValueActualArg(BaseActualArg):
    pass


class TypeActualArg(BaseActualArg):
    pass
