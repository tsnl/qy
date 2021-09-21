"""
A context is a mapping of value-level variable names to schemes.
Each `Context` object is part of a larger tree data-structure that efficiently
handles shadowing definitions and substitution mappings.
"""

import typing as t
from collections import namedtuple

from qcl import frontend
from qcl import types
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
            self,
            project: "frontend.Project",
            purpose: str, loc: fb.ILoc,
            opt_parent_context: t.Optional["Context"],
            symbol_table: t.Dict[str, definition.BaseRecord] = None,
            local_type_template_arg_tid_map: t.Optional[t.Dict[str, types.identity.TID]] = None,
            opt_func: t.Optional["ast.node.LambdaExp"] = None,
            opt_container_submodule: t.Optional["ast.node.SubModExp"] = None
    ):
        #
        # Initialization:
        #

        super().__init__()

        # metadata and relationships:
        self.project = project
        self.purpose = purpose
        self.loc = loc
        self.child_context_list = []

        # initializing the parent context, inheriting relevant props:
        self.opt_parent_context = opt_parent_context
        if self.opt_parent_context is None:
            self.root_context = self
            self.opt_func = opt_func
            self.opt_container_submodule = opt_container_submodule
        else:
            self.root_context = self.opt_parent_context.root_context
            self.opt_parent_context.child_context_list.append(self)

            # if `opt_func` is not provided (is None), we use the parent context's 'opt_func', which may be `None`
            self.opt_func = opt_func if opt_func is not None else self.opt_parent_context.opt_func

            # inheriting the optional container submodule:
            opt_parent_container_submodule = self.opt_parent_context.opt_container_submodule
            if opt_parent_container_submodule is not None:
                self.opt_container_submodule = opt_parent_container_submodule
                if opt_container_submodule is not None:
                    assert opt_container_submodule is self.opt_container_submodule
            else:
                self.opt_container_submodule = opt_container_submodule

        # initializing the symbol table:
        if symbol_table is None:
            self.symbol_table = {}
        else:
            self.symbol_table = symbol_table

        # initializing a lifetime for this context:
        self.lifetime = types.lifetime.mint(self)

        #
        # Derived/computed properties:
        #

        # computing a map of all bound types variables in scope:
        if local_type_template_arg_tid_map is not None:
            self.local_type_template_arg_tid_map = local_type_template_arg_tid_map

            if self.opt_parent_context is not None:
                gm = (self.opt_parent_context.global_type_template_arg_tid_map | self.local_type_template_arg_tid_map)
                self.global_type_template_arg_tid_map = gm
            else:
                self.global_type_template_arg_tid_map = self.local_type_template_arg_tid_map
        else:
            self.local_type_template_arg_tid_map = {}

            if self.opt_parent_context is not None:
                self.global_type_template_arg_tid_map = self.opt_parent_context.global_type_template_arg_tid_map
            else:
                self.global_type_template_arg_tid_map = self.local_type_template_arg_tid_map

        # defining each local types template argument in this context using the BoundVar types supplied.
        # NOTE: despite the term 'local', these symbols are always globally visible: they are 'local' to the
        #       encapsulating scheme.
        self.local_type_template_arg_def_map = {}
        for type_template_arg_name, fresh_bound_var in self.local_type_template_arg_tid_map.items():
            def_record = definition.TypeRecord(
                project,
                type_template_arg_name,
                self.loc, fresh_bound_var, self.opt_func,
                is_bound_globally_visible=True,
                def_is_bound_var=True
            )
            def_ok = self.try_define(type_template_arg_name, def_record)
            assert def_ok
            self.local_type_template_arg_def_map[type_template_arg_name] = def_record

    def push_context(
            self,
            purpose: str,
            loc: fb.ILoc,
            opt_symbol_table=None,
            opt_type_arg_map=None,
            opt_func=None,
            opt_container_submodule=None,
    ):
        return Context(
            self.project,
            purpose, loc,
            self,
            symbol_table=opt_symbol_table,
            local_type_template_arg_tid_map=opt_type_arg_map,
            opt_func=opt_func,
            opt_container_submodule=opt_container_submodule
        )

    def try_define(self, def_name: str, def_record: definition.BaseRecord) -> bool:
        if def_name in self.symbol_table:
            return False
        else:
            assert def_record is not None
            self.symbol_table[def_name] = def_record
            def_record.init_def_context(self)
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
                sep = "~"
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

    # def unify_lifetime_set_for_mem_window_tid(self, mem_window_tid, lifetime_set):
    #     pass
    #
    # def mem_window_lifetime_set(self, mem_window_tid):
    #     digest, lifetime_set = self.lifetimes_map.get(mem_window_tid, (None, None))
    #     return lifetime_set
    #
    # def mem_window_contents_may_be_local(self):
    #     pass


def make_default_root(project):
    def new_builtin_type_def(def_name: str, def_type_id: types.identity.TID) -> definition.TypeRecord:
        loc = fb.BuiltinLoc(def_name)
        def_obj = definition.TypeRecord(
            project,
            def_name, loc,
            def_type_id,
            opt_func=None,
            is_bound_globally_visible=True,
            def_is_bound_var=False
        )
        return def_obj

    return Context(
        project=project,
        purpose="default-root-context",
        loc=fb.BuiltinLoc("root_context_loc"),
        opt_parent_context=None,
        symbol_table=dict(
            **{
                "Str": new_builtin_type_def("String", types.get_str_type()),
            },
            **{
                f"I{n_bits}": new_builtin_type_def(
                    f"SignedInt<{n_bits}>", types.get_int_type(n_bits, is_unsigned=False)
                )
                for n_bits in (8, 16, 32, 64, 128)
            },
            **{
                f"U{n_bits}": new_builtin_type_def(
                    f"UnsignedInt<{n_bits}>", types.get_int_type(n_bits, is_unsigned=True)
                )
                for n_bits in (1, 8, 16, 32, 64, 128)
            },
            **{
                f"F{n_bits}": new_builtin_type_def(
                    f"Float<{n_bits}>", types.get_float_type(n_bits)
                )
                for n_bits in (16, 32, 64)
            }
        )
    )


LifetimesDigest = namedtuple("LifetimesDigest", [
    "may_be_local",
    "may_be_non_local"
])
