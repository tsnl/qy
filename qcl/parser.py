import os.path
import typing as t

from . import antlr
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

    opt_cached_result = file_parse_cache.get(abs_file_path, None)
    if opt_cached_result is not None:
        return opt_cached_result
    else:
        fresh_result = parse_one_file_without_caching(abs_file_path)
        file_parse_cache[abs_file_path] = fresh_result
        return fresh_result


file_parse_cache: t.Dict[str, t.List[ast1.BaseStatement]] = {}


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

    visitor = AstConstructorVisitor(abs_file_path)
    source_file_parse_tree = antlr_parser.sourceFile()
    return visitor.visit(source_file_parse_tree)


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

    def loc(self, ctx: antlr.ParserRuleContext):
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

    def visitSourceFile(self, ctx: antlr.QySourceFileParser.SourceFileContext) -> t.List[ast1.BaseStatement]:
        return self.visit(ctx.unwrapped_block)

    def visitBlock(self, ctx: antlr.QySourceFileParser.BlockContext) -> t.List[ast1.BaseStatement]:
        return self.visit(ctx.unwrapped_block)

    def visitUnwrappedBlock(self, ctx: antlr.QySourceFileParser.UnwrappedBlockContext) -> t.List[ast1.BaseStatement]:
        return [
            self.visit(statement_ctx)
            for statement_ctx in ctx.statements
        ]

    def visitStatement(self, ctx: antlr.QySourceFileParser.StatementContext) -> ast1.BaseStatement:
        if ctx.b1v is not None:
            return ctx.b1v
        elif ctx.b1f is not None:
            return ctx.b1f
        elif ctx.b1t is not None:
            return ctx.b1t
        elif ctx.t1v is not None:
            return ctx.t1v
        elif ctx.con is not None:
            return ctx.con
        elif ctx.ite is not None:
            return ctx.ite
        else:
            raise NotImplementedError("Unknown 'statement' kind in parser")

    def visitBind1vStatement(self, ctx: antlr.QySourceFileParser.Bind1vStatementContext) -> ast1.Bind1vStatement:
        return ast1.Bind1vStatement(self.loc(ctx), ctx.name.text, self.visit(ctx.initializer))

    def visitBind1fStatement(self, ctx: antlr.QySourceFileParser.Bind1fStatementContext) -> ast1.Bind1fStatement:
        arg_name_list = [arg_tk.text for arg_tk in ctx.args]
        if ctx.body_exp is not None:
            ret_exp = self.visit(ctx.body_exp)
            body_stmt_list = [ast1.ReturnStatement(ret_exp.loc, ret_exp)]
        elif ctx.body_block is not None:
            body_stmt_list = self.visit(ctx.body_block)
        else:
            raise NotImplementedError("Unknown 'body' term in Bind1fStatement")

        return ast1.Bind1fStatement(self.loc(ctx), ctx.name.text, arg_name_list, body_stmt_list)

    def visitBind1tStatement(self, ctx: antlr.QySourceFileParser.Bind1tStatementContext) -> ast1.Bind1tStatement:
        return ast1.Bind1tStatement(self.loc(ctx), ctx.name.text, self.visit(ctx.initializer))

    def visitType1vStatement(self, ctx: antlr.QySourceFileParser.Type1vStatementContext) -> ast1.Type1vStatement:
        is_export_line = ctx.is_pub is not None
        return ast1.Type1vStatement(self.loc(ctx), ctx.name.text, self.visit(ctx.ts), is_export_line)

    def visitConstStatement(self, ctx: antlr.QySourceFileParser.ConstStatementContext) -> ast1.ConstStatement:
        return ast1.ConstStatement(self.loc(ctx), self.visit(ctx.b))

    def visitIteStatement(self, ctx: antlr.QySourceFileParser.IteStatementContext) -> ast1.IteStatement:
        then_body = self.visit(ctx.then_body)

        if ctx.elif_stmt is not None:
            else_body = [self.visit(ctx.elif_stmt)]
        elif ctx.else_body is not None:
            else_body = self.visit(ctx.else_body)
        else:
            else_body = []

        return ast1.IteStatement(self.loc(ctx), self.visit(ctx.cond), then_body, else_body)

    def visitReturnStatement(self, ctx: antlr.QySourceFileParser.ReturnStatementContext) -> ast1.ReturnStatement:
        return ast1.ReturnStatement(self.loc(ctx), self.visit(ctx.ret_exp))

    # TODO: implement remaining visitor methods

    def visitExpression(self, ctx: antlr.QySourceFileParser.ExpressionContext):
        raise NotImplementedError("Parsing 'expression'")

    def visitTypeSpec(self, ctx: antlr.QySourceFileParser.TypeSpecContext):
        raise NotImplementedError("Parsing 'typeSpec'")
