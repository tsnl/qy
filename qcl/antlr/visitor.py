import abc

from .gen.NativeQyModuleVisitor import NativeQyModuleVisitor
from qcl import fs_scaffold
from qcl import parser


class BaseVisitor(NativeQyModuleVisitor, metaclass=abc.ABCMeta):
    def __init__(self, source_module: "fs_scaffold.SourceModule"):
        super().__init__()
        self.source_module = source_module

    def lazily_parse_and_apply(self):
        tree = parser.lazily_get_parsed_module_tree(self.source_module.file_path_rel_project)
        self.visit(tree)
