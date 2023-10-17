import os.path
import typing as t
import re
import ast as python_ast

from . import antlr
from . import feedback as fb
from . import panic
from . import ast1
from . import config


def parse_one_file(abs_file_path: str) -> t.List[ast1.BaseStatement]:
    """
    (lazily) parses the contents of a source file.
    """
    if config.COMPILER_IN_DEBUG_MODE:
        assert abs_file_path == os.path.abspath(abs_file_path)
    
    print(f"\t{abs_file_path}")
    
    opt_cached_result = file_parse_cache.get(abs_file_path, None)
    if opt_cached_result is not None:
        return opt_cached_result
    else:
        fresh_result = parse_one_file_without_caching(abs_file_path)
        file_parse_cache[abs_file_path] = fresh_result
        return fresh_result


file_parse_cache: t.Dict[str, t.List[ast1.BaseStatement]] = {}


def parse_one_file_without_caching(abs_file_path: str) -> t.List[ast1.BaseStatement]:
    if config.COMPILER_IN_DEBUG_MODE:
        assert os.path.isfile(abs_file_path)

    error_listener = QyErrorListener(abs_file_path)

    antlr_text_stream = antlr.FileStream(abs_file_path)
    antlr_lexer = antlr.QySourceFileLexer(antlr_text_stream)
    antlr_lexer.removeErrorListeners()
    antlr_lexer.addErrorListener(error_listener)

    antlr_token_stream = antlr.CommonTokenStream(antlr_lexer)
    antlr_parser = antlr.QySourceFileParser(antlr_token_stream)
    antlr_parser.removeErrorListeners()
    antlr_parser._interp.predictionMode = antlr.PredictionMode.LL_EXACT_AMBIG_DETECTION
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
            opt_msg=f"Parser error: {message}",
            opt_file_path=self.source_file_path,
            opt_file_region=fb.FilePos(line-1, column)
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


class AstConstructorVisitor(antlr.QySourceFileVisitor):
    def __init__(self, source_file_path: str):
        super().__init__()
        self.source_file_path = source_file_path

    #
    # helpers:
    #

    def loc(self, ctx: antlr.ParserRuleContext):
        # setting the start line and column according to ANTLR:
        start_line_index = ctx.start.line - 1
        start_col_index = ctx.start.column

        # setting the end line and column according to ANTLR:
        if ctx.stop is not None:
            end_line_index = ctx.stop.line - 1
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

    def make_int_expression(self, ctx, raw_text: str, base: int):
        # splitting the number text:
        numeric_text, suffix_text = AstConstructorVisitor.split_number_text(raw_text)

        # parsing the suffix:
        width_in_bits = 32
        is_unsigned = False
        for suffix_character in suffix_text:
            if suffix_character in ('u', 'U'):
                is_unsigned = True
            elif suffix_character in ('l', 'L'):
                width_in_bits = 64
            elif suffix_character in ('s', 'S'):
                width_in_bits = 16
            elif suffix_character in ('b', 'B'):
                width_in_bits = 8
            else:
                raise NotImplementedError(f"Unknown integer suffix char: {repr(suffix_character)}")

        # parsing the numeric text to find the Python value:
        value = int(numeric_text, base)

        # returning the new expression:
        return ast1.IntExpression(self.loc(ctx), raw_text, value, base, is_unsigned, width_in_bits)

    def make_float_expression(self, ctx, raw_text: str):
        # splitting the number text:
        numeric_text, suffix_text = AstConstructorVisitor.split_number_text(raw_text)

        # parsing the suffix:
        width_in_bits = 64
        for suffix_character in suffix_text:
            if suffix_character in ('f', 'F'):
                width_in_bits = 32
            elif suffix_character in ('d', 'D'):
                width_in_bits = 64
            else:
                raise NotImplementedError(f"Unknown float suffix char: {repr(suffix_character)}")

        # parsing the numeric text to find the Python value:
        value = float(numeric_text)

        # returning the new expression:
        return ast1.FloatExpression(self.loc(ctx), raw_text, value, width_in_bits)

    #
    # Files & blocks:
    #

    def visitSourceFile(self, ctx: antlr.QySourceFileParser.SourceFileContext) -> t.List[ast1.BaseStatement]:
        return [self.visit(s) for s in ctx.statements]

    def visitBlock(self, ctx: antlr.QySourceFileParser.BlockContext) -> t.List[ast1.BaseStatement]:
        return self.visit(ctx.unwrapped_block)

    def visitUnwrappedBlock(self, ctx: antlr.QySourceFileParser.UnwrappedBlockContext) -> t.List[ast1.BaseStatement]:
        return [
            self.visit(statement_ctx)
            for statement_ctx in ctx.prefix_statements
        ]

    def visitConstBlock(self, ctx: antlr.QySourceFileParser.ConstBlockContext) -> t.List[ast1.Bind1vStatement]:
        return [
            self.visit(statement_ctx)
            for statement_ctx in ctx.bindings
        ]

    #
    # statement:
    #

    def visitBind1vTerm(self, ctx: antlr.QySourceFileParser.Bind1vTermContext):
        return ast1.Bind1vStatement(self.loc(ctx), ctx.name.text, self.visit(ctx.initializer), False)

    def visitStatement(self, ctx: antlr.QySourceFileParser.StatementContext) -> ast1.BaseStatement:
        if ctx.b1v is not None:
            return self.visit(ctx.b1v)
        elif ctx.b1f is not None:
            return self.visit(ctx.b1f)
        elif ctx.b1t is not None:
            return self.visit(ctx.b1t)
        elif ctx.con is not None:
            return self.visit(ctx.con)
        elif ctx.ret is not None:
            return self.visit(ctx.ret)
        elif ctx.discard is not None:
            return self.visit(ctx.discard)
        elif ctx.loop is not None:
            return self.visit(ctx.loop)
        elif ctx.break_ is not None:
            return self.visit(ctx.break_)
        elif ctx.continue_ is not None:
            return self.visit(ctx.continue_)
        else:
            raise NotImplementedError(f"Unknown statement kind in parser: {ctx.getText()}")

    def visitBind1vStatement(self, ctx: antlr.QySourceFileParser.Bind1vStatementContext) -> ast1.Bind1vStatement:
        return self.visit(ctx.b1v_term)

    def visitBind1fStatement(self, ctx: antlr.QySourceFileParser.Bind1fStatementContext) -> ast1.Bind1fStatement:
        arg_name_list = []
        opt_arg_type_list = []
        for arg_name, opt_arg_type in self.visit(ctx.args):
            arg_name_list.append(arg_name)
            opt_arg_type_list.append(opt_arg_type)
        assert ctx.body_exp is not None
        is_pub = bool(ctx.pub)
        opt_ret_ts = self.visit(ctx.opt_ret_ts) if ctx.opt_ret_ts is not None else None
        ret_exp = self.visit(ctx.body_exp)
        return ast1.Bind1fStatement(
            self.loc(ctx), 
            ctx.name.text, 
            arg_name_list, 
            opt_arg_type_list, 
            ret_exp, 
            opt_ret_ts,
            is_pub
        )

    def visitBind1tStatement(self, ctx: antlr.QySourceFileParser.Bind1tStatementContext) -> ast1.Bind1tStatement:
        return ast1.Bind1tStatement(self.loc(ctx), ctx.name.text, self.visit(ctx.initializer))

    def visitConstStatement(self, ctx: antlr.QySourceFileParser.ConstStatementContext) -> ast1.ConstStatement:
        bind_statements = self.visit(ctx.b)
        for statement in bind_statements:
            statement.is_constant = True
        return ast1.ConstStatement(self.loc(ctx), bind_statements, self.visit(ctx.type_spec))

    def visitReturnStatement(self, ctx: antlr.QySourceFileParser.ReturnStatementContext) -> ast1.ReturnStatement:
        return ast1.ReturnStatement(self.loc(ctx), self.visit(ctx.ret_exp))

    def visitDiscardStatement(self, ctx: antlr.QySourceFileParser.DiscardStatementContext) -> t.List[ast1.BaseStatement]:
        return ast1.DiscardStatement(self.loc(ctx), self.visit(ctx.discarded_exp))

    def visitLoopStatement(self, ctx: antlr.QySourceFileParser.LoopStatementContext) -> ast1.LoopStatement:
        def get_loop_style():
            if ctx.do_while:
                return ast1.LoopStyle.DoWhile
            if ctx.while_do:
                return ast1.LoopStyle.WhileDo
            raise NotImplementedError(f"Unknown `loop` style: {ctx.getText()}")
        
        return ast1.LoopStatement(
            self.loc(ctx), 
            self.visit(ctx.cond), self.visit(ctx.body), 
            get_loop_style()
        )

    #
    # expressions:
    #

    def visitExpression(self, ctx: antlr.QySourceFileParser.ExpressionContext) -> ast1.BaseExpression:
        res = self.visit(ctx.through)
        assert isinstance(res, ast1.BaseExpression)
        return res

    @staticmethod
    def split_number_text(raw_literal_number_text):
        match_obj = re.match(compiled_number_matcher_pattern, raw_literal_number_text)
        numeric_text = match_obj.group(2).replace('_', '')
        suffix_text = match_obj.group(3)
        return numeric_text, suffix_text

    def visitLitBoolean(self, ctx: antlr.QySourceFileParser.LitBooleanContext):
        if ctx.is_true:
            return ast1.IntExpression(self.loc(ctx), text="1", value=1, base=10, is_unsigned=True, width_in_bits=1)
        else:
            return ast1.IntExpression(self.loc(ctx), text="0", value=0, base=10, is_unsigned=True, width_in_bits=1)
    
    def visitLitInteger(self, ctx: antlr.QySourceFileParser.LitIntegerContext) -> ast1.IntExpression:
        raw_text = ctx.getText()
        if ctx.deci is not None:
            return self.make_int_expression(ctx, raw_text, 10)
        elif ctx.hexi is not None:
            return self.make_int_expression(ctx, raw_text, 16)
        else:
            raise NotImplementedError("Unknown integer literal")

    def visitLitFloat(self, ctx: antlr.QySourceFileParser.LitFloatContext) -> ast1.FloatExpression:
        raw_text = ctx.tok.text
        return self.make_float_expression(ctx, raw_text)

    def visitLitString(self, ctx: antlr.QySourceFileParser.LitStringContext):
        piece_text_list = []
        piece_value_list = []
        for piece in ctx.pieces:
            piece_text = piece.text
            value = python_ast.literal_eval(piece_text)
            
            piece_text_list.append(piece_text)
            piece_value_list.append(value)
        
        value = ''.join(piece_value_list)
        return ast1.StringExpression(self.loc(ctx), piece_text_list, value)

    def visitPrevConstPrimaryExpression(self, ctx: antlr.QySourceFileParser.PrevConstPrimaryExpressionContext):
        return ast1.IdRefExpression(self.loc(ctx), "pred!")

    def visitIdPrimaryExpression(self, ctx: antlr.QySourceFileParser.IdPrimaryExpressionContext):
        return ast1.IdRefExpression(self.loc(ctx), ctx.id_tok.text)

    def visitParenPrimaryExpression(self, ctx: antlr.QySourceFileParser.ParenPrimaryExpressionContext):
        return self.visit(ctx.through)

    def visitItePrimaryExpression(self, ctx: antlr.QySourceFileParser.ItePrimaryExpressionContext):
        cond_exp = self.visit(ctx.cond)
        then_exp = self.visit(ctx.then)
        else_exp = self.visit(ctx.else_) if ctx.else_ is not None else None
        return ast1.IfExpression(self.loc(ctx), cond_exp, then_exp, else_exp)

    def visitLambdaPrimaryExpression(self, ctx: antlr.QySourceFileParser.LambdaPrimaryExpressionContext):
        return self.visitLambdaExpression(ctx.lam)
    
    def visitLambdaExpression(self, ctx: antlr.QySourceFileParser.LambdaExpressionContext):
        opt_arg_names = self.visit(ctx.opt_arg_names) if ctx.opt_arg_names is not None else None
        prefix = self.visitUnwrappedBlock(ctx.prefix)
        opt_tail_exp = self.visitExpression(ctx.opt_tail) if ctx.opt_tail is not None else None
        no_closure = ctx.no_closure is not None or ctx.opt_arg_names is None        # default to closure
        return ast1.LambdaExpression(self.loc(ctx), opt_arg_names, prefix, opt_tail_exp, no_closure)

    def visitThroughPostfixExpression(self, ctx: antlr.QySourceFileParser.ThroughPostfixExpressionContext):
        return self.visit(ctx.through)

    def visitProcCallExpression(self, ctx: antlr.QySourceFileParser.ProcCallExpressionContext):
        return ast1.ProcCallExpression(self.loc(ctx), self.visit(ctx.proc), self.visit(ctx.args) if ctx.args else [])

    def visitConstructorExpression(self, ctx: antlr.QySourceFileParser.ConstructorExpressionContext):
        return ast1.ConstructExpression(self.loc(ctx), self.visit(ctx.made_ts), self.visit(ctx.args) if ctx.args else [])

    def visitCopyExpression(self, ctx: antlr.QySourceFileParser.CopyExpressionContext):
        allocator = {
            "push": ast1.CopyExpression.Allocator.Push,
            "heap": ast1.CopyExpression.Allocator.Heap,
        }[ctx.kw.text]
        is_mut = ctx.is_mut is not None
        copied = self.visit(ctx.src)
        return ast1.CopyExpression(self.loc(ctx), copied, allocator, is_mut)

    def visitDotIdExpression(self, ctx: antlr.QySourceFileParser.DotIdExpressionContext):
        return ast1.DotIdExpression(self.loc(ctx), self.visit(ctx.container), ctx.key.text)

    def visitIndexExpression(self, ctx: antlr.QySourceFileParser.IndexExpressionContext):
        return ast1.IndexExpression(self.loc(ctx), self.visit(ctx.container), self.visit(ctx.index), ret_ref=False)

    def visitIndexRefExpression(self, ctx: antlr.QySourceFileParser.IndexRefExpressionContext):
        return ast1.IndexExpression(self.loc(ctx), self.visit(ctx.container), self.visit(ctx.index), ret_ref=True)

    def visitThroughUnaryExpression(self, ctx: antlr.QySourceFileParser.ThroughUnaryExpressionContext):
        return self.visit(ctx.through)

    def visitUnaryOpExpression(self, ctx: antlr.QySourceFileParser.UnaryOpExpressionContext):
        return ast1.UnaryOpExpression(
            self.loc(ctx),
            self.visit(ctx.op),
            self.visit(ctx.e)
        )

    def visitUnaryOperator(self, ctx: antlr.QySourceFileParser.UnaryOperatorContext) -> ast1.UnaryOperator:
        return {
            '*': ast1.UnaryOperator.DeRef,
            'not': ast1.UnaryOperator.LogicalNot,
            '-': ast1.UnaryOperator.Minus,
            '+': ast1.UnaryOperator.Plus,
            'do': ast1.UnaryOperator.Do
        }[ctx.getText()]

    def visitBinaryExpression(self, ctx: antlr.QySourceFileParser.BinaryExpressionContext) -> ast1.BinaryOpExpression:
        return self.visit(ctx.through)

    def visitMultiplicativeExpression(self, ctx: antlr.QySourceFileParser.MultiplicativeExpressionContext):
        if ctx.through is not None:
            return self.visit(ctx.through)
        else:
            return ast1.BinaryOpExpression(
                self.loc(ctx),
                {
                    '*': ast1.BinaryOperator.Mul,
                    '/': ast1.BinaryOperator.Div,
                    '%': ast1.BinaryOperator.Mod
                }[ctx.op.text],
                self.visit(ctx.lt),
                self.visit(ctx.rt)
            )

    def visitAdditiveExpression(self, ctx: antlr.QySourceFileParser.AdditiveExpressionContext):
        if ctx.through is not None:
            return self.visit(ctx.through)
        else:
            return ast1.BinaryOpExpression(
                self.loc(ctx),
                {
                    '+': ast1.BinaryOperator.Add,
                    '-': ast1.BinaryOperator.Sub
                }[ctx.op.text],
                self.visit(ctx.lt),
                self.visit(ctx.rt)
            )

    def visitShiftExpression(self, ctx: antlr.QySourceFileParser.ShiftExpressionContext):
        if ctx.through is not None:
            return self.visit(ctx.through)
        else:
            return ast1.BinaryOpExpression(
                self.loc(ctx),
                {
                    '<<': ast1.BinaryOperator.LSh,
                    '>>': ast1.BinaryOperator.RSh
                }[ctx.op.text],
                self.visit(ctx.lt),
                self.visit(ctx.rt)
            )

    def visitRelationalExpression(self, ctx: antlr.QySourceFileParser.RelationalExpressionContext):
        if ctx.through is not None:
            return self.visit(ctx.through)
        else:
            return ast1.BinaryOpExpression(
                self.loc(ctx),
                {
                    '<': ast1.BinaryOperator.LThan,
                    '>': ast1.BinaryOperator.GThan,
                    '<=': ast1.BinaryOperator.LEq,
                    '>=': ast1.BinaryOperator.GEq
                }[ctx.op.text],
                self.visit(ctx.lt),
                self.visit(ctx.rt),
            )

    def visitEqualityExpression(self, ctx: antlr.QySourceFileParser.EqualityExpressionContext):
        if ctx.through is not None:
            return self.visit(ctx.through)
        else:
            return ast1.BinaryOpExpression(
                self.loc(ctx),
                {
                    '==': ast1.BinaryOperator.Eq,
                    '!=': ast1.BinaryOperator.NEq
                }[ctx.op.text],
                self.visit(ctx.lt),
                self.visit(ctx.rt)
            )

    def visitAndExpression(self, ctx: antlr.QySourceFileParser.AndExpressionContext):
        if ctx.through is not None:
            return self.visit(ctx.through)
        else:
            return ast1.BinaryOpExpression(
                self.loc(ctx),
                ast1.BinaryOperator.BitwiseAnd,
                self.visit(ctx.lt),
                self.visit(ctx.rt)
            )

    def visitXorExpression(self, ctx: antlr.QySourceFileParser.XorExpressionContext):
        if ctx.through is not None:
            return self.visit(ctx.through)
        else:
            return ast1.BinaryOpExpression(
                self.loc(ctx),
                ast1.BinaryOperator.BitwiseXOr,
                self.visit(ctx.lt),
                self.visit(ctx.rt)
            )

    def visitOrExpression(self, ctx: antlr.QySourceFileParser.OrExpressionContext):
        if ctx.through is not None:
            return self.visit(ctx.through)
        else:
            return ast1.BinaryOpExpression(
                self.loc(ctx),
                ast1.BinaryOperator.BitwiseOr,
                self.visit(ctx.lt),
                self.visit(ctx.rt)
            )

    def visitLogicalAndExpression(self, ctx: antlr.QySourceFileParser.LogicalAndExpressionContext):
        if ctx.through is not None:
            return self.visit(ctx.through)
        else:
            return ast1.BinaryOpExpression(
                self.loc(ctx),
                ast1.BinaryOperator.LogicalAnd,
                self.visit(ctx.lt),
                self.visit(ctx.rt)
            )

    def visitLogicalOrExpression(self, ctx: antlr.QySourceFileParser.LogicalOrExpressionContext):
        if ctx.through is not None:
            return self.visit(ctx.through)
        else:
            return ast1.BinaryOpExpression(
                self.loc(ctx),
                ast1.BinaryOperator.LogicalOr,
                self.visit(ctx.lt),
                self.visit(ctx.rt)
            )

    def visitUpdateExpression(self, ctx: antlr.QySourceFileParser.UpdateExpressionContext):
        if ctx.through is not None:
            return self.visit(ctx.through)
        else:
            return ast1.UpdateExpression(self.loc(ctx), store_address=self.visit(ctx.lt), stored_value=self.visit(ctx.rt))

    #
    # TypeSpec:
    #

    def visitTypeSpec(self, ctx: antlr.QySourceFileParser.TypeSpecContext):
        res = self.visit(ctx.through)
        assert isinstance(res, ast1.BaseTypeSpec)
        return res

    def visitPrimaryTypeSpec(self, ctx: antlr.QySourceFileParser.PrimaryTypeSpecContext):
        if ctx.id_tok is not None:
            return ast1.IdRefTypeSpec(self.loc(ctx), ctx.id_tok.text)
        else:
            return ast1.BuiltinPrimitiveTypeSpec(
                self.loc(ctx), {
                    'Float': ast1.BuiltinPrimitiveTypeIdentity.Float32,
                    'Double': ast1.BuiltinPrimitiveTypeIdentity.Float64,
                    'Long': ast1.BuiltinPrimitiveTypeIdentity.Int64,
                    'Int': ast1.BuiltinPrimitiveTypeIdentity.Int32,
                    'Short': ast1.BuiltinPrimitiveTypeIdentity.Int16,
                    'Char': ast1.BuiltinPrimitiveTypeIdentity.Int8,
                    'ULong': ast1.BuiltinPrimitiveTypeIdentity.UInt64,
                    'UInt': ast1.BuiltinPrimitiveTypeIdentity.UInt32,
                    'UShort': ast1.BuiltinPrimitiveTypeIdentity.UInt16,
                    'Byte': ast1.BuiltinPrimitiveTypeIdentity.UInt8,
                    'Bool': ast1.BuiltinPrimitiveTypeIdentity.Bool,
                    'Void': ast1.BuiltinPrimitiveTypeIdentity.Void
                }[ctx.tok.text]
            )

    def visitArrayTypeSpec(self, ctx: antlr.QySourceFileParser.ArrayTypeSpecContext):
        if ctx.through is not None:
            return self.visit(ctx.through)
    
        kw = ctx.tok.text
        elem_ts = self.visit(ctx.elem_ts)
        is_mut = kw.startswith('Mut')

        if kw in ('Array', 'MutArray'):
            count_exp = self.visit(ctx.count)
            return ast1.ArrayTypeSpec(self.loc(ctx), elem_ts, count_exp, is_mut)
        elif kw in ('ArrayBox', 'MutArrayBox'):
            return ast1.ArrayBoxTypeSpec(self.loc(ctx), elem_ts, is_mut)    
        else:
            raise NotImplementedError(f"Unknown keyword in ArrayTypeSpec: {repr(kw)}")

    def visitThroughAdtTypeSpec(self, ctx: antlr.QySourceFileParser.ThroughAdtTypeSpecContext):
        return self.visit(ctx.through)
    
    def visitUnionAdtTypeSpec(self, ctx: antlr.QySourceFileParser.UnionAdtTypeSpecContext):
        return ast1.AdtTypeSpec(self.loc(ctx), ast1.LinearTypeOp.Sum, self.visit(ctx.args) if ctx.args else [])

    def visitTupleAdtTypeSpec(self, ctx: antlr.QySourceFileParser.TupleAdtTypeSpecContext):
        return ast1.AdtTypeSpec(self.loc(ctx), ast1.LinearTypeOp.Product, self.visit(ctx.args) if ctx.args else [])

    def visitPtrTypeSpec(self, ctx: antlr.QySourceFileParser.PtrTypeSpecContext):
        if ctx.through is not None:
            return self.visit(ctx.through)
        else:
            is_mut = {
                "Ptr": False,
                "MutPtr": True
            }[ctx.ptrName.text]
            return ast1.PtrTypeSpec(self.loc(ctx), self.visit(ctx.pointee), is_mut)

    def visitSignatureTypeSpec(self, ctx: antlr.QySourceFileParser.SignatureTypeSpecContext):
        if ctx.through is not None:
            return self.visit(ctx.through)
        else:
            return ast1.ProcSignatureTypeSpec(
                self.loc(ctx),
                self.visit(ctx.args) if ctx.args is not None else None,
                self.visit(ctx.ret),
                ctx.has_closure_slot is not None,
                is_c_variadic=False
            )

    #
    # Misc:
    #
    
    def visitDefArgSpec(self, ctx: antlr.QySourceFileParser.DefArgSpecContext) -> t.Tuple[str, ast1.BaseTypeSpec]:
        name = ctx.name_tok.text
        ts = self.visit(ctx.ts)
        return name, ts

    def visitTypeArgSpec(self, ctx: antlr.QySourceFileParser.TypeArgSpecContext) -> t.Tuple[t.Optional[str], ast1.BaseTypeSpec]:
        opt_name = ctx.name_tok.text if ctx.name_tok is not None else None
        ts = self.visit(ctx.ts)
        return opt_name, ts

    def visitCsIdList(self, ctx: antlr.QySourceFileParser.CsIdListContext) -> t.List[str]:
        return [id_tok.text for id_tok in ctx.ids]

    def visitCsDefArgSpecList(self, ctx: antlr.QySourceFileParser.DefArgSpecContext) -> t.Tuple[t.Optional[str], ast1.BaseTypeSpec]:
        return [self.visit(spec) for spec in ctx.specs]

    def visitCsTypeArgSpecList(self, ctx: antlr.QySourceFileParser.CsTypeArgSpecListContext) -> t.List[t.Tuple[t.Optional[str], ast1.BaseTypeSpec]]:
        return [self.visit(spec) for spec in ctx.specs]

    def visitCsExpressionList(self, ctx: antlr.QySourceFileParser.CsExpressionListContext) -> t.List[ast1.BaseExpression]:
        return [self.visit(e) for e in ctx.exps]


compiled_number_matcher_pattern = re.compile(r"(0[xb])?([0-9_.]+)([a-zA-Z]*)")
