"""
A context is a mapping of value-level variable names to schemes.
Each `Context` object is part of a larger tree data-structure that efficiently
handles shadowing definitions and substitution mappings.
"""

import typing as t

from qcl import type
from qcl import feedback as fb
from qcl import ast

from . import definition


class Context(object):
    opt_parent_context: t.Optional["Context"]
    root_context: "Context"
    child_context_list: t.List["Context"]
    symbol_table: t.Dict[str, definition.BaseRecord]
    opt_func: t.Optional["ast.node.LambdaExp"]

    def __init__(
            self, purpose: str, loc: fb.ILoc,
            opt_parent_context: t.Optional["Context"],
            symbol_table: t.Dict[str, definition.BaseRecord] = None,
            local_type_template_arg_map: t.Optional[t.Dict[str, type.identity.TID]] = None,
            opt_func: t.Optional["ast.node.LambdaExp"] = None
    ):
        super().__init__()

        # metadata and relationships:
        self.purpose = purpose
        self.loc = loc
        self.child_context_list = []

        # initializing the parent context, inheriting relevant props:
        self.opt_parent_context = opt_parent_context
        if self.opt_parent_context is None:
            self.root_context = self
            self.opt_func = opt_func
        else:
            self.root_context = self.opt_parent_context.root_context
            self.opt_parent_context.child_context_list.append(self)

            # if `opt_func` is not provided (is None), we use the parent context's 'opt_func', which may be `None`
            self.opt_func = opt_func if opt_func is not None else self.opt_parent_context.opt_func

        # initializing the symbol table:
        if symbol_table is None:
            self.symbol_table = {}
        else:
            self.symbol_table = symbol_table

        # computing a map of all bound type variables in scope:
        if local_type_template_arg_map is not None:
            self.local_type_template_arg_map = local_type_template_arg_map

            if self.opt_parent_context is not None:
                gm = (self.opt_parent_context.global_type_template_arg_map | self.local_type_template_arg_map)
                self.global_type_template_arg_map = gm
            else:
                self.global_type_template_arg_map = self.local_type_template_arg_map
        else:
            self.local_type_template_arg_map = {}

            if self.opt_parent_context is not None:
                self.global_type_template_arg_map = self.opt_parent_context.global_type_template_arg_map
            else:
                self.global_type_template_arg_map = self.local_type_template_arg_map

        # defining each local type template argument in this context using the BoundVar types supplied:
        for type_template_arg_name, fresh_bound_var in self.local_type_template_arg_map.items():
            def_record = definition.TypeRecord(type_template_arg_name, self.loc, fresh_bound_var, self.opt_func)
            assert self.try_define(type_template_arg_name, def_record)

    def push_context(self, purpose: str, loc: fb.ILoc, opt_symbol_table=None, opt_type_arg_map=None, opt_func=None):
        return Context(purpose, loc, self, opt_symbol_table, opt_type_arg_map, opt_func=opt_func)

    def try_define(self, def_name: str, def_record: definition.BaseRecord) -> bool:
        if def_name in self.symbol_table:
            return False
        else:
            assert def_record is not None
            self.symbol_table[def_name] = def_record
            def_record.scheme.init_def_context(self)
            return True

    def lookup(self, def_name, shallow=False):
        found_def = self.symbol_table.get(def_name, None)
        if found_def is not None:
            return found_def

        if not shallow and self.opt_parent_context:
            return self.opt_parent_context.lookup(def_name, shallow=False)
        else:
            return None

    def print(self, title=None, indent_count=0):
        indent_text = ' ' * indent_count

        if title is not None:
            print(f"{indent_text}{title}")

        print(f"{indent_text}+ {self.purpose} @ {hex(id(self))}")
        for name, def_obj in self.symbol_table.items():
            if def_obj.universe in (definition.Universe.Value, definition.Universe.Module):
                sep = "::"
            else:
                sep = "="

            print(f"{indent_text}  - {name} {sep} {def_obj.scheme.spell()}")

        for child_context in self.child_context_list:
            child_context.print(indent_count=indent_count+2)

    def map_everyone(self, fn: t.Callable[["Context"], None]):
        self.root_context.map_descendants(fn)

    def map_descendants(self, fn):
        fn(self)

        for child_context in self.child_context_list:
            child_context.map_descendants(fn)

    def map_ancestors(self, fn: t.Callable[["Context"], None]):
        context = self
        while context is not None:
            fn(context)
            context = context.opt_parent_context


def make_default_root():
    def new_builtin_type_def(def_name: str, def_type_id: type.identity.TID) -> definition.TypeRecord:
        loc = fb.BuiltinLoc(def_name)
        def_obj = definition.TypeRecord(def_name, loc, def_type_id, opt_func=None)
        return def_obj

    return Context(
        purpose="default-root-context",
        loc=fb.BuiltinLoc("root_context_loc"),
        opt_parent_context=None,
        symbol_table=dict(
            **{
                "Str": new_builtin_type_def("String", type.get_str_type()),
            },
            **{
                f"I{n_bits}": new_builtin_type_def(
                    f"SignedInt<{n_bits}>", type.get_int_type(n_bits // 8, is_unsigned=False)
                )
                for n_bits in (8, 16, 32, 64, 128)
            },
            **{
                f"U{n_bits}": new_builtin_type_def(
                    f"UnsignedInt<{n_bits}>", type.get_int_type(n_bits//8, is_unsigned=True)
                )
                for n_bits in (8, 16, 32, 64, 128)
            },
            **{
                f"F{n_bits}": new_builtin_type_def(
                    f"Float<{n_bits}>", type.get_float_type(n_bits//8)
                )
                for n_bits in (16, 32, 64)
            }
        )
    )
