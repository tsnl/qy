from typing import *
import enum
import dataclasses

from qcl import feedback
from qcl import type
from qcl import scheme

from . import defs


class Context(object):
    def __init__(self):
        self.symbol_table = {}

    def __setitem__(self, key: type.identity.TID, value: "Definition"):
        self.symbol_table[key] = value

    def __getitem__(self, key: type.identity.TID):
        return self.symbol_table[key]

    def print(self):
        for name, definition in self.symbol_table.items():
            if definition.universe == defs.DefinitionUniverse.Type:
                print(f"- {name} = {definition.scheme.spell()}")
            elif definition.universe == defs.DefinitionUniverse.Value:
                print(f"- {name} = {definition.scheme.spell()}")
            else:
                raise NotImplementedError(f"Unknown definition universe: {definition.universe}")
