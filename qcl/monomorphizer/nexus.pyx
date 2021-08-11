"""
NEXUS
This module translates polymorphic, Python AST from a Project into monomorphic MAST in the cpp-extension universe.

First, every ID definition, regardless of scope, is turned into a unique DefID.
In particular, template IDs are turned into special DefIDs that must be substituted out.
This substitution occurs when templated sub-modules are instantiated.

In order to instantiate templates, we must evaluate any total constants passed as template arguments.
Since returning to Python or using Python data-structures for such evaluation is inefficient,
the extension instead maintains its own byte-code/ast format called MAST.

MAST can be queried after monomorphization as input for future passes.

Given an entry-point module with an entry-point function, evaluating the entry point function as a constant 
monomorphizes all referenced template sub-modules and evaluates all directly and indirectly used global constants.

In effect, we statically evaluate all necessary global constants given an entry-point, apply tree-shaking, and store
the end-result in MAST for later.

The key take-away is that...
- monomorphization and evaluation are inter-twined.
- by evaluating global symbol table frame as one big constant, we monomorphize all submods used by an entry point.
- future passes read MAST byte-code to generate more.
"""

from qcl import frontend
from qcl import ast

cimport mast
cimport modules
cimport defs


def monomorphize_project(proj: frontend.project.Project):
    # sourcing entry point:
    entry_point_source_module: frontend.FileModuleSource = proj.entry_point_source_module
    entry_point_file_mod_exp: ast.node.FileModExp = entry_point_source_module.ast_file_mod_exp_from_frontend

    # first, generating MAST code for all file-mods in this project

    # next, evaluating the entry point constant:

    # TODO: all constants that were evaluated for the entry point must be bundled for future passes.
    #       aka UNSHAKEN MONOMORPHIC SET (UMS)

    # TODO: delete this 'test' call that is used to debug.
    test_extension()


def test_extension():
    print("Hello, world!")

