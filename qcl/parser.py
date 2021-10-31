import os.path
import typing as t

import antlr

from . import feedback as fb
from . import panic
from . import ast1
from . import config


def parse_one_file(abs_file_path: str) -> t.List[ast1.BaseStatement]:
    """
    (lazily) parses the contents of a source file.
    """
    if config.DEBUG_MODE:
        assert abs_file_path == os.path.abspath(abs_file_path)

    opt_cached_result = parsed_stmts_cache.get(abs_file_path, None)
    if opt_cached_result is not None:
        return opt_cached_result
    else:
        fresh_result = parse_one_file_without_caching(abs_file_path)
        parsed_stmts_cache[abs_file_path] = fresh_result
        return fresh_result


parsed_stmts_cache: t.Dict[str, t.List[ast1.BaseStatement]] = {}


def parse_one_file_without_caching(abs_file_path: str) -> t.List[ast1.BaseStatement]:
    if config.DEBUG_MODE:
        assert os.path.isfile(abs_file_path)

    error_listener = QyErrorListener(abs_file_path)

    antlr_text_stream = antlr.FileStream(abs_file_path)
    antlr_lexer = antlr.QySourceFileLexer(antlr_text_stream)
    antlr_lexer.removeErrorListeners()
    antlr_lexer.addErrorListener(error_listener)

    antlr_token_stream = antlr.CommonTokenStream(antlr_lexer)
    antlr_parser = antlr.QySourceFileParser(antlr_token_stream)
    antlr_parser.removeErrorListeners()
    antlr_parser.addErrorListener(error_listener)

    return AstConstructorVisitor(abs_file_path).visit(antlr_parser.sourceFile())


class QyErrorListener(antlr.ANTLR4ErrorListener):
    def __init__(self, source_file_path: str):
        super().__init__()
        self.source_file_path = source_file_path

    def syntaxError(self, recognizer, offending_symbol, line, column, message, e):
        panic.because(
            panic.ExitCode.SyntaxError,
            opt_msg=message,
            opt_file_path=self.source_file_path,
            opt_file_region=fb.FilePos(line-1, column)
        )

    def reportAmbiguity(self, recognizer, dfa, start_index, stop_index, exact, ambig_alts, configs):
        if not exact:
            # raise excepts.ParserCompilationError(f"Inexact parser ambiguity detected (...)")
            panic.because(
                panic.ExitCode.SyntaxError,
                opt_msg="syntax ambiguity detected! (TODO: report more info if required)"
            )

    def reportAttemptingFullContext(self, recognizer, dfa, start_index, stop_index, conflicting_alts, configs):
        pass

    def reportContextSensitivity(self, recognizer, dfa, start_index, stop_index, prediction, configs):
        pass


class AstConstructorVisitor(antlr.QySourceFileVisitor):
    def __init__(self, source_file_path: str):
        super().__init__()
        self.source_file_path = source_file_path

    def ctx_loc(self, ctx: antlr.ParserRuleContext):
        # setting the start line and column according to ANTLR:
        start_line_index = ctx.start.line - 1
        start_col_index = ctx.start.column

        # setting the end line and column according to ANTLR:
        if ctx.stop is not None:
            end_line_index = ctx.stop.line
            end_col_index = ctx.stop.column

            # extending the end column by the length of the last token:
            # FIXME: inefficient check to ensure no 'multiline-string-literal' tokens
            #        can be replaced by a better check in ANTLR-- e.g. using vocabulary?
            if '\n' not in ctx.stop.text:
                end_col_index += len(ctx.stop.text)
        else:
            end_line_index = start_line_index
            end_col_index = start_col_index

        return fb.FileLoc(
            self.source_file_path,
            fb.FileSpan(
                fb.FilePos(start_line_index, start_col_index),
                fb.FilePos(end_line_index, end_col_index)
            )
        )

    # TODO: implement remaining visitor methods
