"""
This module handles several checks that do not require the VM but that guarantee fitness
to interpret code.

- TODO: checking closures: computing all non-local IDs (CANCELLED-- moved to typer)
    - using an explicit 'nonlocal' statement like Python is not only redundant 
      (since all bound constants are read-only), but would make currying ugly.
    - thus, each LambdaExp must store a list of enclosed variables & initializer Definition
      records
- TODO: validate `push` expressions (CANCELLED-- moved to typer)
    - when these DefRec objects are ENCLOSED or RETURNED, their lifetime gets 'promoted'
    - objects with a promoted lifetime must be allocated using `heap` rather than `push`
        - this is a basic form of escape-analysis
        - once we infer nonlocal enclosed IDs, we can view a lambda as a struct containing
            a copy of each nonlocal enclosed ID's value at the point of definition.
        - copies of pointers are still pointers: since variables are immutably bound, we
            simply check if pointers to `push`-ed data are NEVER returned, even by copy
    - this whole pass can be simplified: think of fluid propagation: we want to push fluid
        in from `push` nodes, allow the fluid to flow in the pipes of assignment or 
        `[i]`-indexing (which returns a pointer into a memory window), and check for LEAKS 
        outside the `push`-ed function frame.
    - NOTE: must consider each function frame in isolation: a function that returns a 
        pushed pointer to itself still leaks, since it returns ANY pushed pointer. 
    - NOTE: `push` cannot be used outside a LambdaExp.
    - TODO: need a `free` statement that can de-allocate several IDs referring to 
        pointers, slices, or arrays.
- TODO: checking that Type1VElem only refers to most local possible IDs
    - in general, means ID must be in same scope
    - exceptions: 
        - LambdaExp, where formal-args live in 'shell' scope
"""

import functools

from qcl import frontend
from qcl import typer
from qcl import types
from qcl import ast
from qcl import excepts


SES = types.side_effects.SES


def run(project: frontend.Project):
    # TODO: implement each above pass...
    # print("INFO: PTCC: basic_checks OK")
    print("INFO: monomorphizer: basic_checks WIP...")
