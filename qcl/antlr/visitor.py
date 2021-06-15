import abc

from .gen.NativeQyModuleVisitor import NativeQyModuleVisitor
from qcl import fs_scaffold
from qcl import parser


class BaseVisitor(NativeQyModuleVisitor, metaclass=abc.ABCMeta):
    def __init__(self, source_module: "frontend.FileModuleSource"):
        super().__init__()
        self.source_module = source_module

    def lazily_parse_and_apply(self):
        tree = parser.lazily_parse_module_file(self.source_module.file_path_rel_cwd)
        self.visit(tree)
