"""
This module detects the types of/denoted by terms.
- Wikipedia - Algorithm W (Hindley Milner Type Inference)
- YouTube - C. Hegemann, Type Inference From Scratch https://www.youtube.com/watch?v=ytPAlhnAKro&t=165s
    - implements Algo W for LC + let-bindings, int & bool literals
    - only missing interfaces
Rather than being efficient, this algorithm prioritizes producing traceable output and parallelizability.
- rather than mutating graphs, use bags of immutable symbols
- use theory to its fullest
"""

from qcl import antlr
from qcl import frontend
from qcl import type
from qcl import ast
from qcl import excepts

from . import context
from . import definition
from . import substitution
from . import scheme
from . import seeding
from . import inference


def type_project(project, all_file_module_list):

    # typing occurs in two phases:
    # - seeding: we generate the types of all file modules in terms of free-vars so imports will resolve
    # - inference: we resolve imports, then generate the types of all sub-modules

    root_context = context.make_default_root()

    debug_path = True
    if debug_path:
        # trying seeding:
        try:
            seeding.seed_project_types(root_context, project, all_file_module_list)
        except excepts.TyperCompilationError as e:
            root_context.print("SEEDING ERROR:")
            print()
            raise e from e

        root_context.print("normal post-seed:")
        print()

        # trying inference:
        try:
            inference.infer_project_types(project, all_file_module_list)
        except excepts.TyperCompilationError as e:
            # DEBUG: so we can inspect types:
            root_context.print("INFERENCE ERROR:")
            print()
            raise e from e

        root_context.print("normal post-inference:")
        print()

    else:
        seeding.seed_project_types(root_context, project, all_file_module_list)
        inference.infer_project_types(project, all_file_module_list)
