import abc
import os.path as path

from qcl import antlr
from qcl import excepts


cached_parse_tree_map = {}


def lazily_get_parsed_module_tree(raw_source_file_path):
    norm_source_file_path = path.normpath(raw_source_file_path)

    cached_parse_tree = cached_parse_tree_map.get(norm_source_file_path, None)
    if cached_parse_tree is not None:
        return cached_parse_tree

    return parse_fresh_module_tree(norm_source_file_path)


def parse_fresh_module_tree(norm_source_file_path):
    if not path.isfile(norm_source_file_path):
        raise excepts.ParserCompilationError(f"Source file does not exist: {norm_source_file_path}")

    # NOTE: we first read the file into a Python string to...
    #   1. convert all CRLF ('\r\n') and CR ('\r') into LF ('\n'), therby normalizing input
    #   2. keep a copy of text and lines for error reporting later.
    with open(norm_source_file_path, 'r') as source_file:
        source_text = source_file.read()
        # source_lines = source_text.split('\n')

    antlr_error_listener = ErrorListener()

    antlr_text_stream = antlr.InputStream(source_text)
    antlr_lexer = antlr.NativeQyModuleLexer(antlr_text_stream)
    antlr_lexer.removeErrorListeners()
    antlr_lexer.addErrorListener(antlr_error_listener)

    antlr_token_stream = antlr.CommonTokenStream(antlr_lexer)
    antlr_parser = antlr.NativeQyModuleParser(antlr_token_stream)
    antlr_parser.addErrorListener(antlr_error_listener)

    parse_tree = antlr_parser.topModule()
    return parse_tree


class ErrorListener(antlr.ANTLRErrorListener):
    def syntaxError(self, recognizer, offending_symbol, line, column, message, e):
        raise excepts.ParserCompilationError(f"Syntax error: {message}")

    def reportAmbiguity(self, recognizer, dfa, startIndex, stopIndex, exact, ambigAlts, configs):
        raise excepts.ParserCompilationError(f"Parser ambiguity detected (...)")

    def reportAttemptingFullContext(self, recognizer, dfa, startIndex, stopIndex, conflictingAlts, configs):
        pass

    def reportContextSensitivity(self, recognizer, dfa, startIndex, stopIndex, prediction, configs):
        pass
