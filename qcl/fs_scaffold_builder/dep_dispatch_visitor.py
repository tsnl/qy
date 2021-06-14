"""
This module extracts file dependencies from freshly parsed abstract syntax trees.
- e.g. imported source modules
- e.g. linked header, source, archive, or shared object files
It modifies the fs-scaffold.
"""

import ast as py_ast

from qcl import antlr


class DepDispatchVisitor(antlr.BaseVisitor):
    def __init__(self, source_module):
        super().__init__(source_module)
        self.new_source_module_list = []

    def visitImportLine(self, ctx):
        content_dir_path = self.source_module.project.abs_content_dir_path
        assert content_dir_path is not None

        # import a source file:
        raw_dispatched_dependency_path = ctx.path.getText()
        dispatched_dependency_path = py_ast.literal_eval(raw_dispatched_dependency_path)
        dispatched_dependency_path = dispatched_dependency_path.replace('$', content_dir_path)

        new_source_module = self.source_module.load_relative_source_module(dispatched_dependency_path)
        self.new_source_module_list.append(new_source_module)

    # we can add more methods here to add different kinds of dependencies.
