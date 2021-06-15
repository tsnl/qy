import abc
import os.path as path

from qcl import antlr
from qcl import excepts
from qcl import feedback
from qcl import ast
from qcl import type

from .file import FileModuleSource


cached_file_module_exp_map = {}


def lazily_parse_module_file(source_module: FileModuleSource):
    norm_source_file_path = source_module.file_path

    cached_parse_tree = cached_file_module_exp_map.get(norm_source_file_path, None)
    if cached_parse_tree is not None:
        return cached_parse_tree

    file_module_exp_node = parse_fresh_module_tree(norm_source_file_path)
    cached_file_module_exp_map[norm_source_file_path] = file_module_exp_node
    return file_module_exp_node


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

    antlr_parse_tree = antlr_parser.fileModule()

    file_module_exp_node = AstConstructorVisitor(norm_source_file_path).visit(antlr_parse_tree)
    return file_module_exp_node


class ErrorListener(antlr.ANTLRErrorListener):
    def syntaxError(self, recognizer, offending_symbol, line, column, message, e):
        raise excepts.ParserCompilationError(f"Syntax error: {message}")

    def reportAmbiguity(self, recognizer, dfa, start_index, stop_index, exact, ambig_alts, configs):
        raise excepts.ParserCompilationError(f"Parser ambiguity detected (...)")

    def reportAttemptingFullContext(self, recognizer, dfa, start_index, stop_index, conflicting_alts, configs):
        pass

    def reportContextSensitivity(self, recognizer, dfa, start_index, stop_index, prediction, configs):
        pass


class AstConstructorVisitor(antlr.NativeQyModuleVisitor):

    #
    #
    # General Visitor stuff
    #
    #

    def __init__(self, module_file_path):
        super().__init__()
        self.module_file_path = module_file_path

    def ctx_loc(self, ctx: antlr.ParserRuleContext):
        # setting the start line and column according to ANTLR:
        start_line = ctx.start.line
        start_col = ctx.start.column

        # setting the end line and column according to ANTLR:
        if ctx.stop is not None:
            end_line = ctx.stop.line
            end_col = ctx.stop.column

            # extending the end column by the length of the last token:
            # FIXME: inefficient check to ensure no 'string' tokens
            if '\n' not in ctx.stop.text:
                end_col += len(ctx.stop.text)
        else:
            end_line = start_line
            end_col = start_col

        return feedback.TextFileLoc(
            self.module_file_path,
            start_line, 1 + start_col,
            end_line, 1 + end_col
        )

    #
    #
    # Modules:
    #
    #

    def visitFileModule(self, ctx):
        return ast.node.FileModuleExp(
            self.ctx_loc(ctx),
            self.visit(ctx.imports) if ctx.imports else {},
            self.visit(ctx.exports) if ctx.exports else [],
            dict((self.visit(mod_def) for mod_def in ctx.moduleDefs))
        )

    def visitModuleImports(self, ctx):
        return dict((self.visit(line) for line in ctx.lines))

    def visitImportLine(self, ctx):
        return ctx.name.text, self.visit(ctx.path).text

    def visitModuleExports(self, ctx):
        return [self.visit(line) for line in ctx.lines]

    def visitExportLine(self, ctx):
        return ctx.name

    def visitModuleDef(self, ctx):
        module_name = ctx.name.text
        module_args = [id_tok.text for id_tok in ctx.args]
        module_elements = self.visit(ctx.body)

        module_exp = ast.node.SubModuleExp(self.ctx_loc(ctx), module_args, module_elements)

        return module_name, module_exp

    #
    #
    # Tables & elements:
    #
    #

    def visitTableWrapper(self, ctx):
        return [self.visit(element) for element in ctx.elements]

    def visitTypeValIdElement(self, ctx):
        return ast.node.TypingValueIDElement(
            self.ctx_loc(ctx),
            ctx.lhs_id.text,
            self.visit(ctx.ts)
        )

    def visitBindValIdElement(self, ctx):
        return ast.node.BindOneValueIDElement(
            self.ctx_loc(ctx),
            ctx.lhs_id.text,
            self.visit(ctx.init_exp)
        )

    def visitBindTypeIdElement(self, ctx):
        return ast.node.BindOneTypeIDElement(
            self.ctx_loc(ctx),
            ctx.lhs_id.text,
            self.visit(ctx.init_ts)
        )

    #
    #
    # Expressions:
    #
    #

    #
    # ID:
    #

    def visitIdExp(self, ctx):
        return ast.node.IdExp(self.ctx_loc(ctx), ctx.tk.text)

    #
    # Numbers:
    #

    def visitThroughIntPrimaryExp(self, ctx):
        return self.visit(ctx.through)

    def visitDecIntExp(self, ctx):
        super().visitDecIntExp(ctx)
        return ast.node.NumberExp(self.ctx_loc(ctx), ctx.tk.text)

    def visitHexIntExp(self, ctx):
        super().visitHexIntExp(ctx)
        return ast.node.NumberExp(self.ctx_loc(ctx), ctx.tk.text)

    def visitDecFloatExp(self, ctx):
        super().visitDecFloatExp(ctx)
        return ast.node.NumberExp(self.ctx_loc(ctx), ctx.tk.text)

    #
    # Strings:
    #

    def visitStringExp(self, ctx):
        super().visitStringExp(ctx)
        return self.visit(ctx.it)

    def visitStringPrimaryExp(self, ctx):
        super().visitStringPrimaryExp(ctx)
        return ast.node.StringExp(
            self.ctx_loc(ctx),
            [self.visit(chunk) for chunk in ctx.chunks]
        )

    def helpVisitStringChunk(self, ctx, quote_str):
        content = ctx.tk.text[len(quote_str):-len(quote_str)]
        runes = []
        index = 0

        while index < len(content):
            if content[index] == '\\':
                if content[index + 1] == '\\':
                    runes.append(ord('\\'))
                    index += 2
                elif content[index + 1] == 'n':
                    runes.append(ord('\n'))
                    index += 2
                elif content[index + 1] == 'r':
                    runes.append(ord('\r'))
                    index += 2
                elif content[index + 1] == 'typer':
                    runes.append(ord('\t'))
                    index += 2

                elif len(quote_str) == 1 and content[index + 1] == quote_str:
                    runes.append(ord(quote_str))
                    index += 2

                elif content[index + 1] == 'u':
                    code_point_text = content[index + 2:index + 2 + 4]
                    runes.append(int(code_point_text, 16))
                    index += 2 + 4
                elif content[index + 1] == 'U':
                    code_point_text = content[index + 2:index + 2 + 8]
                    runes.append(int(code_point_text, 16))
                    index += 2 + 8
            else:
                runes.append(ord(content[index]))
                index += 1

        return runes

    def visitSqStringChunk(self, ctx):
        quote_str = "'"
        runes = self.helpVisitStringChunk(ctx, quote_str)
        return ast.node.StringExpChunk(
            self.ctx_loc(ctx),
            runes, quote_str
        )

    def visitDqStringChunk(self, ctx):
        quote_str = '"'
        runes = self.helpVisitStringChunk(ctx, quote_str)
        return ast.node.StringExpChunk(
            self.ctx_loc(ctx),
            runes, quote_str
        )

    def visitMlSqStringChunk(self, ctx):
        quote_str = "'''"
        runes = self.helpVisitStringChunk(ctx, quote_str)
        return ast.node.StringExpChunk(
            self.ctx_loc(ctx),
            runes, quote_str
        )

    def visitMlDqStringChunk(self, ctx):
        quote_str = '"""'
        runes = self.helpVisitStringChunk(ctx, quote_str)
        return ast.node.StringExpChunk(
            self.ctx_loc(ctx),
            runes, quote_str
        )

    #
    # Primary compounds:
    #

    def visitUnitExp(self, ctx):
        return ast.node.UnitExp(self.ctx_loc(ctx))

    def visitIdentityParenExp(self, ctx):
        return self.visit(ctx.wrapped)

    def visitThroughParenPrimaryExp(self, ctx):
        return self.visit(ctx.through)

    def visitChainExp(self, ctx):
        return self.visit(ctx.it)

    def visitTupleExp(self, ctx):
        return self.visit(ctx.it)

    def visitCastExp(self, ctx):
        return self.visit(ctx.it)

    def visitTuplePrimaryExp(self, ctx):
        return ast.node.TupleExp(
            self.ctx_loc(ctx),
            [self.visit(item) for item in ctx.items]
        )

    def visitChainPrimaryExp(self, ctx):
        elements, opt_tail = self.visit(ctx.chain_table_wrapper)
        return ast.node.ChainExp(
            self.ctx_loc(ctx),
            elements, opt_tail,
            opt_prefix_ts=self.visit(ctx.ts),
            opt_prefix_es=self.visit(ctx.es)
        )

    def visitChainTableWrapper(self, ctx):
        return (
            [self.visit(element) for element in ctx.elements],
            (self.visit(ctx.tail) if ctx.tail is not None else None)
        )

    def visitCastPrimaryExp(self, ctx):
        return ast.node.CastExp(
            self.ctx_loc(ctx),
            self.visit(ctx.ts), self.visit(ctx.data)
        )

    #
    # Constructions (using type specs):
    # TODO: implement construction visitor
    #

    #
    # Postfix Expressions:
    #

    def visitThroughPostfixExp(self, ctx):
        return self.visit(ctx.through)

    def visitCallExp(self, ctx):
        return ast.node.PostfixVCallExp(
            self.ctx_loc(ctx),
            self.visit(ctx.called_exp),
            self.visit(ctx.arg),
            has_se=(ctx.has_se is not None)
        )

    def visitDotNameKeyExp(self, ctx):
        return ast.node.GetElementByNameExp(
            self.ctx_loc(ctx),
            self.visit(ctx.lhs),
            ctx.str_key.text
        )

    def visitDotIntKeyExp(self, ctx):
        return ast.node.GetElementByIndexExp(
            self.ctx_loc(ctx),
            self.visit(ctx.lhs),
            self.visit(ctx.int_key),
            False
        )

    #
    # Unary expressions:
    #

    def visitUnaryExp(self, ctx):
        if ctx.through is not None:
            return self.visit(ctx.through)
        else:
            return ast.node.UnaryExp(
                self.ctx_loc(ctx),
                self.visit(ctx.op),
                self.visit(ctx.arg)
            )

    def visitUnaryOp(self, ctx):
        return {
            'not': ast.node.UnaryOp.LogicalNot,
            '+': ast.node.UnaryOp.Pos,
            '-': ast.node.UnaryOp.Neg,
            '*': ast.node.UnaryOp.DeRef,
            '&mut': ast.node.UnaryOp.GetMutableRef,
            '&': ast.node.UnaryOp.GetImmutableRef
        }[ctx.getText()]

    #
    # Binary operators:
    #

    def helpVisitBinaryExp(self, ctx):
        if ctx.through is not None:
            return self.visit(ctx.through)
        else:
            lt_arg = self.visit(ctx.lt)
            rt_arg = self.visit(ctx.rt)
            binary_op = {
                '^': ast.node.BinaryOp.Pow,
                '*': ast.node.BinaryOp.Mul,
                '/': ast.node.BinaryOp.Div,
                '%': ast.node.BinaryOp.Rem,
                '+': ast.node.BinaryOp.Add,
                '-': ast.node.BinaryOp.Sub,
                '<': ast.node.BinaryOp.LT,
                '>': ast.node.BinaryOp.GT,
                '<=': ast.node.BinaryOp.LEq,
                '>=': ast.node.BinaryOp.GEq,
                '==': ast.node.BinaryOp.Eq,
                '!=': ast.node.BinaryOp.NE,
                'and': ast.node.BinaryOp.LogicalAnd,
                'or': ast.node.BinaryOp.LogicalOr
            }[ctx.op.text]
            return ast.node.BinaryExp(
                self.ctx_loc(ctx),
                binary_op,
                lt_arg, rt_arg
            )

    def visitPowBinaryExp(self, ctx):
        return self.helpVisitBinaryExp(ctx)

    def visitMulBinaryExp(self, ctx):
        return self.helpVisitBinaryExp(ctx)

    def visitAddBinaryExp(self, ctx):
        return self.helpVisitBinaryExp(ctx)

    def visitCmpBinaryExp(self, ctx):
        return self.helpVisitBinaryExp(ctx)

    def visitEqBinaryExp(self, ctx):
        return self.helpVisitBinaryExp(ctx)

    def visitLogicalAndBinaryExp(self, ctx):
        return self.helpVisitBinaryExp(ctx)

    def visitLogicalOrBinaryExp(self, ctx):
        return self.helpVisitBinaryExp(ctx)

    #
    # assignExp
    #

    def visitAssignExp(self, ctx):
        if ctx.through is not None:
            return self.visit(ctx.through)
        else:
            return ast.node.AssignExp(
                self.ctx_loc(ctx),
                self.visit(ctx.dst),
                self.visit(ctx.src)
            )

    #
    # bulkyExp
    #

    def visitBulkyExp(self, ctx):
        if ctx.through:
            return self.visit(ctx.through)
        elif ctx.if_exp:
            return self.visit(ctx.if_exp)
        elif ctx.fn_exp:
            return self.visit(ctx.fn_exp)
        else:
            assert False and "Unknown bulkyExp type."

    def visitIfExp(self, ctx):
        return ast.node.IfExp(
            self.ctx_loc(ctx),
            self.visit(ctx.cond),
            self.visit(ctx.then_branch),
            self.visit(ctx.opt_else_branch) if ctx.opt_else_branch else None
        )

    def visitElseBranchExp(self, ctx):
        if ctx.chain_exp:
            return self.visit(ctx.chain_exp)
        elif ctx.if_exp:
            return self.visit(ctx.if_exp)
        else:
            assert False and "Unknown 'elseBranchExp'"

    def visitFnExp(self, ctx):
        return ast.node.LambdaExp(
            self.ctx_loc(ctx),
            [fn_arg.text for fn_arg in ctx.args],
            self.visit(ctx.body)
        )

    #
    #
    # Type-specs:
    #
    #

    def visitTypeSpec(self, ctx):
        return self.visit(ctx.through)

    def visitUnitTypeSpec(self, ctx):
        return ast.node.UnitTypeSpec(self.ctx_loc(ctx))

    def visitIdentityParenTypeSpec(self, ctx):
        return self.visit(ctx.wrapped)

    def visitTupleTypeSpec(self, ctx):
        return ast.node.TupleTypeSpec(
            self.ctx_loc(ctx),
            [self.visit(it) for it in ctx.items]
        )

    def visitIdTypeSpec(self, ctx):
        return ast.node.IdTypeSpec(
            self.ctx_loc(ctx),
            ctx.tk.text
        )

    def visitThroughParenTypeSpec(self, ctx):
        return self.visit(ctx.through)

    def visitFnSgnTypeSpec(self, ctx):
        return ast.node.FnSignatureTypeSpec(
            self.ctx_loc(ctx),
            self.visit(ctx.lt),
            self.visit(ctx.rt)
        )

    def visitStructTypeSpec(self, ctx):
        return ast.node.AdtTypeSpec(
            ast.node.AdtKind.Structure,
            self.ctx_loc(ctx),
            self.visit(ctx.elements)
        )

    def visitTaggedUnionTypeSpec(self, ctx):
        return ast.node.AdtTypeSpec(
            ast.node.AdtKind.TaggedUnion,
            self.ctx_loc(ctx),
            self.visit(ctx.elements)
        )

    def visitUntaggedUnionTypeSpec(self, ctx):
        return ast.node.AdtTypeSpec(
            ast.node.AdtKind.UntaggedUnion,
            self.ctx_loc(ctx),
            self.visit(ctx.elements)
        )

    #
    # effects-spec:
    #

    def visitEffectsSpec(self, ctx):
        return {
            'Tot': type.side_effects.SES.Tot,
            'Dv': type.side_effects.SES.Dv,
            'Exn': type.side_effects.SES.Exn,
            'ST': type.side_effects.SES.ST,
            'ML': type.side_effects.SES.ML
        }[ctx.getText()]

    #
    # TODO:
    #

    # - visit effectsSpec
    # - visit struct
    # - visit pointer, array, type-spec
    # - visit make expressions
    # - visit array, type-spec expressions
    # - modules may accept template arguments
    # - accessing IDs from another module, possibly calling a template function (module).
