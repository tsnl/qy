import os.path

from .. import panic, feedback
from . import antlr


def parse_file(filepath):
    parse_file_without_caching(filepath)


def parse_file_without_caching(filepath):
    assert os.path.isfile(filepath)

    error_listener = ErrorListener(filepath)

    antlr_text_stream = antlr.FileStream(filepath)
    antlr_lexer = antlr.Lexer(antlr_text_stream)
    antlr_lexer.removeErrorListeners()
    antlr_lexer.addErrorListener(error_listener)

    antlr_token_stream = antlr.CommonTokenStream(antlr_lexer)
    antlr_parser = antlr.Parser(antlr_token_stream)
    antlr_parser.removeErrorListeners()
    antlr_parser._interp.predictionMode = antlr.PredictionMode.LL_EXACT_AMBIG_DETECTION
    antlr_parser.addErrorListener(error_listener)

    visitor = AstConstructorVisitor(filepath)
    source_file_parse_tree = antlr_parser.module()
    return visitor.visit(source_file_parse_tree)


class AstConstructorVisitor(antlr.Visitor):
    # TODO: implement me!
    def __init__(self, filepath: str) -> None:
        super().__init__()
        self.filepath = filepath


class ErrorListener(antlr.BaseErrorListener):
    def __init__(self, source_file_path: str):
        super().__init__()
        self.source_file_path = source_file_path

    def syntaxError(self, recognizer, offending_symbol, line, column, message, e):
        panic.because(
            panic.ExitCode.SyntaxError,
            opt_msg=f"Parser error: {message}",
            opt_file_path=self.source_file_path,
            opt_file_region=feedback.FilePos(line-1, column)
        )

    def reportAmbiguity(self, recognizer, dfa, start_index, stop_index, exact, ambig_alts, configs):
        if not exact:
            # raise excepts.ParserCompilationError(f"Inexact parser ambiguity detected (...)")
            # NOTE: https://www.antlr.org/api/Java/org/antlr/v4/runtime/ANTLRErrorListener.html
            # "...which does not result in a syntax error"
            panic.because(
                panic.ExitCode.SyntaxError,
                opt_msg="syntax ambiguity detected! (TODO: report more info if required)"
            )

    def reportAttemptingFullContext(self, recognizer, dfa, start_index, stop_index, conflicting_alts, configs):
        pass

    def reportContextSensitivity(self, recognizer, dfa, start_index, stop_index, prediction, configs):
        pass
