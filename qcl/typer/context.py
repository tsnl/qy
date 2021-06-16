"""
A context is a mapping of value-level variable names to schemes.
It is broken into a tree of frames to introduce and remove symbols.
"""

from typing import *

from qcl import type
from qcl import feedback as fb

from . import scheme
from . import definition


class ContextManager(object):
    def __init__(self, root_context: "Context" = None):
        super().__init__()
        if root_context is not None:
            self.root_context = root_context
        else:
            self.root_context = default_root_context

        assert self.root_context is not None
        self.context_stack = [root_context]

    @property
    def top_context(self) -> Optional["Context"]:
        return self.context_stack[-1]

    def push_context(self, opt_new_context=None):
        if opt_new_context is None:
            new_context = Context(opt_parent_frame=self.top_context)
        else:
            new_context = opt_new_context

        assert new_context is not None
        self.context_stack.append(new_context)

    def pop_context(self):
        self.context_stack.pop()

    def try_define(self, def_name: str, def_obj: definition.BaseDef) -> bool:
        assert self.top_context is not None

        if def_name in self.top_context:
            return False
        else:
            self.top_context[def_name] = def_obj
            return True

    def lookup(self, def_name):
        for context in reversed(self.context_stack):
            found_def = context.symbol_table.get(def_name, None)
            if found_def is not None:
                assert isinstance(found_def, definition.Definition)
                return found_def
        else:
            return None

    def map(self, fn: Callable[["Context"], None]):
        self.root_context.map(fn)


class Context(object):
    def __init__(
            self,
            opt_parent_frame: Optional["Context"],
            symbol_table: Dict[str, definition.BaseDef] = None
    ):
        super().__init__()

        self.opt_parent_frame = opt_parent_frame
        self.child_frames = []
        if self.opt_parent_frame is not None:
            self.opt_parent_frame.child_frames.append(self)

        if symbol_table is None:
            self.symbol_table = {}
        else:
            self.symbol_table = symbol_table

    def __contains__(self, name: str):
        return name in self.symbol_table

    def __setitem__(self, key: str, value: definition.BaseDef):
        self.symbol_table[key] = value

    def __getitem__(self, key: str) -> definition.BaseDef:
        return self.symbol_table[key]

    def print(self):
        for name, def_obj in self.symbol_table.items():
            if def_obj.universe == definition.DefinitionUniverse.Type:
                print(f"- {name} = {def_obj.scheme.spell()}")
            elif def_obj.universe == definition.DefinitionUniverse.Value:
                print(f"- {name} = {def_obj.scheme.spell()}")
            else:
                raise NotImplementedError(f"Unknown definition.py universe: {def_obj.universe}")

    def map(self, fn: Callable[["Context"], None]):
        fn(self)

        for child_frame in self.child_frames:
            child_frame.map(fn)


def make_default_root_context():
    def new_builtin_type_def(def_name: str, def_type_id: type.identity.TID) -> definition.TypeDef:
        loc = fb.BuiltinLoc(def_name)
        def_obj = definition.TypeDef(loc, def_type_id)
        return def_obj

    return Context(
        opt_parent_frame=None,
        symbol_table=dict(
            **{
                "String": new_builtin_type_def("String", type.get_str_type()),
            },
            **{
                f"Int{n_bits}": new_builtin_type_def(
                    f"SignedInt<{n_bits}>", type.get_int_type(n_bits // 8, is_unsigned=False)
                )
                for n_bits in (8, 16, 32, 64, 128)
            },
            **{
                f"UInt{n_bits}": new_builtin_type_def(
                    f"UnsignedInt<{n_bits}>", type.get_int_type(n_bits//8, is_unsigned=True)
                )
                for n_bits in (8, 16, 32, 64, 128)
            },
            **{
                f"Float{n_bits}": new_builtin_type_def(
                    f"Float<{n_bits}>", type.get_float_type(n_bits//8)
                )
                for n_bits in (16, 32, 64)
            }
        )
    )


default_root_context = make_default_root_context()
