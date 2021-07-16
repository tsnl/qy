"""
This module offers names to refer to regions of memory.
"""

import typing as t

from qcl import typer

MemLocID = int

context_list = []


def mint(lifetime_ctx: t.Optional["typer.context.Context"]) -> MemLocID:
    lifetime_id = len(context_list)
    context_list.append(lifetime_ctx)
    assert context_list[lifetime_id] is lifetime_ctx
    return lifetime_id


heap_lifetime = mint(None)
null_lifetime = mint(None)
