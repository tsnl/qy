import abc
import os.path as path

import antlr4

from .gen.NativeQyModuleLexer import NativeQyModuleLexer
from .gen.NativeQyModuleParser import NativeQyModuleParser
from .gen.NativeQyModuleVisitor import NativeQyModuleVisitor

from .. import excepts


cached_parse_tree_map = {}


class BaseVisitor(NativeQyModuleVisitor, metaclass=abc.ABCMeta):
    def __init__(self, raw_source_file_path, norm_source_file_path):
        super().__init__()
        self.raw_source_file_path = raw_source_file_path
        self.norm_source_file_path = norm_source_file_path
        self.source_tree = lazily_get_parsed_module_tree(self.raw_source_file_path)

    def visit_tree(self):
        self.visit(self.source_tree)


def lazily_get_parsed_module_tree(raw_source_file_path):
    norm_source_file_path = path.normpath(raw_source_file_path)
    if not path.isfile(norm_source_file_path):
        raise excepts.ParserCompilationError(f"Source file does not exist: {norm_source_file_path}")

    cached_parse_tree = cached_parse_tree_map.get(norm_source_file_path, None)
    if cached_parse_tree is not None:
        return cached_parse_tree

    return parse_fresh_module_tree(norm_source_file_path)


def parse_fresh_module_tree(norm_source_file_path):
    antlr_source = antlr4.FileStream(norm_source_file_path, encoding='utf-8')
    antlr_lexer = NativeQyModuleLexer(antlr_source)
    antlr_token_stream = antlr4.CommonTokenStream(antlr_lexer)
    antlr_parser = NativeQyModuleParser(antlr_token_stream)

    parse_tree = antlr_parser.topModule()

    return parse_tree
