"""
A context is a mapping of value-level variable names to schemes.
"""

from typing import *

from qcl import type

from . import definition


class Context(object):
    def __init__(self, symbol_table: Dict[type.identity.TID, definition.Definition] = None):
        if symbol_table is None:
            self.symbol_table = {}
        else:
            self.symbol_table = symbol_table

    def __setitem__(self, key: type.identity.TID, value: "definition.Definition"):
        self.symbol_table[key] = value

    def __getitem__(self, key: type.identity.TID):
        return self.symbol_table[key]

    def print(self):
        for name, def_obj in self.symbol_table.items():
            if def_obj.universe == definition.DefinitionUniverse.Type:
                print(f"- {name} = {def_obj.scheme.spell()}")
            elif def_obj.universe == definition.DefinitionUniverse.Value:
                print(f"- {name} = {def_obj.scheme.spell()}")
            else:
                raise NotImplementedError(f"Unknown definition.py universe: {def_obj.universe}")
