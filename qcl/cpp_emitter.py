# FIXME: 'translate' functions should return the type as well as a string translation-- allows us to dispatch when 
#        emitting.
# TODO: emit 2 more headers: `.forward.hpp` and `.types.hpp`
#   - `.forward.hpp` performs forward declarations/type aliasing
#   - `.types.hpp` contains type definitions, including as C++ classes
#   - this allows us to write to all 4 streams in parallel, inserting includes to glue this together.

import abc
import os
import os.path
import re
import typing as t
import enum
import json
from . import ast1
from . import ast2
from . import config
from . import types
from . import typer
from . import base_emitter

#
# Interface:
#

class Emitter(base_emitter.BaseEmitter):
    def __init__(self, rel_output_dir_path: str) -> None:
        super().__init__()
        self.rel_output_dir_path = rel_output_dir_path
        self.abs_output_dir_path = os.path.abspath(rel_output_dir_path)

    def emit_qyp_set(self, qyp_set: ast2.QypSet):
        os.makedirs(self.abs_output_dir_path, exist_ok=True)
        for qyp_name, qyp in qyp_set.qyp_name_map.items():
            self.emit_single_qyp(qyp_name, qyp)
        # for qyp_name, src_file_path, source_file in qyp_set.iter_source_files():
        #     self.emit_single_file(qyp_set, qyp_name, src_file_path, source_file)

    def emit_single_qyp(self, qyp_name: str, qyp: ast2.Qyp):
        output_file_stem = os.path.join(self.abs_output_dir_path, qyp_name)
        cpp_file = CppFile(CppFileType.MainSource, f"{output_file_stem}.cpp")
        hpp_file = CppFile(CppFileType.MainHeader, f"{output_file_stem}.hpp")
        print(f"INFO: Generating C/C++ file pair:\n\t{cpp_file.path}\n\t{hpp_file.path}")
        
        # emitting declarations
        for src_file_path, src_obj in qyp.src_map.items():
            assert isinstance(src_obj, ast2.QySourceFile)
            for stmt in src_obj.stmt_list:
                self.emit_stmt(hpp_file, stmt, is_top_level=True)
                self.emit_stmt(cpp_file, stmt, is_top_level=True)

        # TODO: emitting type definitions
        #   - must order types, so can use DFS-like approach with a 'visited' set

        # TODO: emitting function definitions

        cpp_file.close()
        hpp_file.close()

    def emit_stmt(self, p: "BasePrinter", stmt: ast1.BaseStatement, is_top_level: bool):
        if isinstance(stmt, ast1.Bind1vStatement):
            if p.type == CppFileType.MainSource:
                def_obj = stmt.lookup_def_obj()
                assert isinstance(def_obj, typer.BaseDefinition)
                assert not def_obj.scheme.vars
                _, def_type = def_obj.scheme.instantiate()
                bind_cpp_fragments = []
                if not def_obj.is_public:
                    bind_cpp_fragments.append('static')
                bind_cpp_fragments.append(self.translate_type(def_type))
                bind_cpp_fragments.append(def_obj.name)
                p.print(f"// bind {stmt.name} = {stmt.initializer.desc}")
                p.print(' '.join(bind_cpp_fragments))
                with Block(p, closing_brace="};") as b:
                    self.emit_expression(b, stmt.initializer)
                p.print()
        elif isinstance(stmt, ast1.Bind1fStatement):
            if p.type == CppFileType.MainSource:
                def_obj = stmt.lookup_def_obj()
                assert isinstance(def_obj, typer.BaseDefinition)
                assert not def_obj.scheme.vars
                _, def_type = def_obj.scheme.instantiate()
                assert isinstance(def_type, types.ProcedureType)
                left_half_signature_fragments = []
                arg_fragments = []
                for arg_type, arg_name in zip(def_type.arg_types, stmt.args):
                    arg_fragments.append(f"{self.translate_type(arg_type)} {arg_name}")
                
                p.print(f"// bind {stmt.name} = {{...}}")
                if not def_obj.is_public:
                    p.print('static')
                p.print(self.translate_type(def_type.ret_type))
                p.print(def_obj.name)
                with Block(p, opening_brace='(', closing_brace=')') as b:
                    b.print(',\n'.join(arg_fragments))
                with Block(p) as b:
                    self.emit_block(b, stmt.body)
                p.print()
        elif isinstance(stmt, ast1.Bind1tStatement):
            pass
        elif isinstance(stmt, ast1.Type1vStatement):
            if p.type == CppFileType.MainHeader:
                def_obj = stmt.lookup_def_obj()
                if def_obj.is_public:
                    _, def_type = def_obj.scheme.instantiate()
                    p.print(f"// extern {stmt.name}")
                    p.print(f"extern {self.translate_type(def_type)} {stmt.name};")
                    p.print()
        elif isinstance(stmt, ast1.ConstStatement):
            pass
        elif isinstance(stmt, ast1.ReturnStatement):
            p.print(f"return {self.translate_expression(stmt.returned_exp)};")
        elif isinstance(stmt, ast1.IteStatement):
            p.print(f"if ({self.translate_expression(stmt.cond)})")
            with Block(p) as b:
                self.emit_block(b, stmt.then_block)
            p.print("else")
            with Block(p) as b:
                self.emit_block(b, stmt.else_block)
        else:
            raise NotImplementedError(f"emit_declarations_for_stmt: {stmt}")

    def emit_expression(self, p: "BasePrinter", exp: ast1.BaseExpression):
        p.print(self.translate_expression(exp))

    def emit_block(self, p: "BasePrinter", block: t.List[ast1.BaseStatement]):
        for stmt in block:
            self.emit_stmt(p, stmt, is_top_level=False)

    def translate_type(self, qy_type: types.BaseType) -> str:
        if isinstance(qy_type, types.VoidType):
            return "void"
        elif isinstance(qy_type, types.IntType):
            if qy_type.width_in_bits == 1:
                assert not qy_type.is_signed
                return "bool"
            else:
                assert qy_type.width_in_bits in (8, 16, 32, 64)
                sign_prefix = '' if qy_type.is_signed else 'u'
                size_str = str(qy_type.width_in_bits)
                return sign_prefix + "int" + size_str + "_t"
        elif isinstance(qy_type, types.FloatType):
            if qy_type.width_in_bits == 32:
                return "float"
            elif qy_type.width_in_bits == 64:
                return "double"
            else:
                raise NotImplementedError(f"Unknown float width in bits: {qy_type.width_in_bits}")
        elif isinstance(qy_type, types.StringType):
            return "std::string";
        else:
            # raise NotImplementedError(f"Don't know how to translate type to C++: {qy_type}")
            print(f"WARNING: Don't know how to translate type to C++: {qy_type}")
            return f"<NotImplemented:{qy_type}>"

    def translate_expression(self, exp: ast1.BaseExpression) -> str:
        ret_str, ret_type = self.translate_expression_with_type(exp)
        assert isinstance(ret_str, str)
        # assert isinstance(ret_type, types.BaseType)
        assert isinstance(ret_type, types.BaseType) or ret_type is None
        return ret_str

    def translate_expression_with_type(self, exp: ast1.BaseExpression) -> t.Tuple[str, types.BaseConcreteType]:
        if isinstance(exp, ast1.IdRefExpression):
            def_obj = exp.lookup_def_obj()
            assert isinstance(def_obj, typer.BaseDefinition)
            s, def_type = def_obj.scheme.instantiate()
            assert s is typer.Substitution.empty
            return exp.name, def_type

        elif isinstance(exp, ast1.IntExpression):
            if exp.width_in_bits == 1:
                assert exp.is_unsigned
                return ['false', 'true'][exp.value], types.IntType.get(1, is_signed=False)
            else:
                fragments = []
                
                if exp.text_base == 16:
                    fragments.append('0x')
                elif exp.text_base == 8:
                    fragments.append('0')
                elif exp.text_base == 2:
                    fragments.append('0b')
                
                fragments.append(str(exp.value))

                if exp.is_unsigned:
                    fragments.append('u')
                
                if exp.width_in_bits == 64:
                    fragments.append('LL')
                elif exp.width_in_bits == 16:
                    fragments.append('S')
                elif exp.width_in_bits == 8:
                    fragments.insert(0, '(uint8_t)' if exp.is_unsigned else '(int8_t)')
            
            return ''.join(fragments), types.IntType.get(exp.width_in_bits, is_signed=not exp.is_unsigned)

        elif isinstance(exp, ast1.FloatExpression):
            fragments = []
            fragments.append(str(exp.value))
            if exp.width_in_bits == 32:
                fragments.append('f')
            elif exp.width_in_bits == 64:
                # default precision
                pass
            else:
                raise NotImplementedError("Unknown float exp width in bits")
            return ''.join(fragments), types.FloatType.get(exp.width_in_bits)

        elif isinstance(exp, ast1.StringExpression):
            return json.dumps(exp.value), types.StringType.singleton

        elif isinstance(exp, ast1.UnaryOpExpression):
            operator_str = {
                ast1.UnaryOperator.DeRef: "*",
                ast1.UnaryOperator.LogicalNot: "!",
                ast1.UnaryOperator.Minus: "-",
                ast1.UnaryOperator.Plus: "+"
            }[exp.operator]
            operand_type, operand_str = self.translate_expression_with_type(exp.operand)

            # dispatch based on `operand_type` to select the right operator and return type:
            # for now, Qy's builtin unary operators are a subset of C++'s builtin unary operators.            
            if exp.operator == ast1.UnaryOperator.DeRef:
                operand_ptr_type = operand_type
                assert isinstance(operand_ptr_type, types.PointerType)
                ret_type = operand_ptr_type.pointee_type
                assert isinstance(ret_type, types.BaseConcreteType)
            elif exp.operator == ast1.UnaryOperator.LogicalNot:
                operand_type = operand_type
                assert operand_type is types.IntType.get(1, is_signed=False)
                ret_type = operand_type
            elif exp.operator in (ast1.UnaryOperator.Minus, ast1.UnaryOperator.Plus):
                if isinstance(operand_type, types.IntType):
                    ret_type = types.IntType.get(operand_type.width_in_bits, is_signed=True)
                elif isinstance(operand_type, types.FloatType):
                    ret_type = operand_type
                else:
                    raise NotImplementedError(f"Unknown argument types in unary operator emitter")
            else:
                raise NotImplementedError("Unknown operator")
            
            return f"({operator_str} {operand_str})", ret_type

        elif isinstance(exp, ast1.BinaryOpExpression):
            # FIXME: hacky; does not work for fmod, though type-checks
            operator_str = {
                ast1.BinaryOperator.Mul: "*",
                ast1.BinaryOperator.Div: "/",
                ast1.BinaryOperator.Mod: "%",
                ast1.BinaryOperator.Add: "+",
                ast1.BinaryOperator.Sub: "-",
                ast1.BinaryOperator.BitwiseAnd: "&",
                ast1.BinaryOperator.BitwiseXOr: "^",
                ast1.BinaryOperator.BitwiseOr: "|",
                ast1.BinaryOperator.LogicalAnd: "&&",
                ast1.BinaryOperator.LogicalOr: "||",
                ast1.BinaryOperator.Eq: "==",
                ast1.BinaryOperator.NEq: "!=",
                ast1.BinaryOperator.LSh: "<<",
                ast1.BinaryOperator.RSh: ">>"
            }[exp.operator]
            lt_operand_str, lt_operand_type = self.translate_expression_with_type(exp.lt_operand)
            rt_operand_str, rt_operand_type = self.translate_expression_with_type(exp.rt_operand)
            if exp.operator in typer.BinaryOpDTO.arithmetic_binary_operator_set:
                if isinstance(lt_operand_type, types.IntType):
                    assert isinstance(rt_operand_type, types.IntType)
                    assert lt_operand_type.is_signed == rt_operand_type.is_signed
                    width_in_bits = max(lt_operand_type.width_in_bits, rt_operand_type.width_in_bits)
                    ret_type = types.IntType.get(width_in_bits, is_signed=lt_operand_type.is_signed)
                elif isinstance(lt_operand_type, types.FloatType):
                    assert isinstance(rt_operand_type, types.FloatType)
                    width_in_bits = max(lt_operand_type.width_in_bits, rt_operand_type.width_in_bits)
                    ret_type = types.FloatType.get(width_in_bits)
                else:
                    raise NotImplementedError("Unknown operand types to binary arithmetic operator")
            elif exp.operator in typer.BinaryOpDTO.comparison_binary_operator_set:
                ret_type = types.IntType.get(1, is_signed=False)
            elif exp.operator in typer.BinaryOpDTO.logical_binary_operator_set:
                ret_type = types.IntType.get(1, is_signed=False)
            else:
                raise NotImplementedError(f"Unknown operator when typing in binary operator emitter: {exp.operator}")
            return "(" + lt_operand_str + operator_str + rt_operand_str + ")", ret_type

        elif isinstance(exp, ast1.ProcCallExpression):
            proc_str, proc_type = self.translate_expression_with_type(exp.proc)
            assert isinstance(proc_type, types.ProcedureType)
            ret_type = proc_type.ret_type
            ret_str = (
                proc_str + 
                '(' + 
                ', '.join((
                    self.translate_expression(arg_exp)
                    for arg_exp in exp.arg_exps
                )) + 
                ')'
            )
            return ret_str, ret_type
        else:
            print(f"WARNING: Don't know how to translate expression to C++: {exp}")
            return f"<NotImplemented:{exp.desc}>", None


#
# C++ generator:
# adapted from https://www.codeproject.com/script/Articles/ViewDownloads.aspx?aid=571645
#

# CodeFragment: t.TypeAlias = t.Union[str, t.List[str]]
CodeFragment = t.Union[str, t.List[str]]


class CppFileType(enum.Enum):
    MainSource = enum.auto()
    MainHeader = enum.auto()
    ForwardHeader = enum.auto()
    TypesHeader = enum.auto()


class BasePrinter(abc.ABC):
    @abc.abstractmethod
    def print(self, code_fragment: CodeFragment = ""):
        pass

    @abc.abstractmethod
    def inc_indent(self):
        pass

    @abc.abstractmethod
    def dec_indent(self):
        pass

    @property
    @abc.abstractmethod
    def type(self):
        pass


class CppFile(BasePrinter):
    def __init__(
        self, 
        file_type: CppFileType,
        file_path: str,
        # indent_str: str='\t'
    ) -> None:
        super().__init__()
        self._type = file_type
        self.path = file_path
        self.os_file_handle = open(self.path, 'w', buffering=4*1024)
        self.indent_count = 0
        self.indent_str = '\t'

        #
        # Post-constructor, but constructor-time:
        #

        # emitting preamble:
        if self.type == CppFileType.MainHeader:
            self.print("#pragma once")
            self.print()
            self.print_common_stdlib_header_includes()
            self.print()
        elif self.type == CppFileType.MainSource:
            self.print(f"#include \"{os.path.basename(self.path)[:-len('.cpp')]}.hpp\"")
            self.print()
            self.print_common_stdlib_header_includes()
            self.print()

    @property
    def type(self):
        return self._type

    def close(self):
        assert self.os_file_handle is not None
        self.os_file_handle.close()
        self.os_file_handle = None

    def print(self, code_fragment: CodeFragment = ""):
        if isinstance(code_fragment, str):
            lines = code_fragment.split('\n')
        elif isinstance(code_fragment, list):
            if __debug__:
                for line in code_fragment:
                    assert '\n' not in line
            lines = code_fragment
        else:
            raise ValueError(f"Invalid CodeFragment: {code_fragment}")
        
        for line in lines:
            for _ in range(self.indent_count):
                print(self.indent_str, end='', file=self.os_file_handle)

            print(line, file=self.os_file_handle)
        
        # print(file=self.os_file_handle)
    
    def print_common_stdlib_header_includes(self):
        self.print("#include <cstdint>")
        self.print("#include <string>")

    def inc_indent(self):
        self.indent_count += 1
    
    def dec_indent(self):
        self.indent_count -= 1


class Block(BasePrinter):
    def __init__(
        self, 
        printer: BasePrinter, 
        prefix: str = "", 
        suffix: str = "", 
        opening_brace: str = "{",
        closing_brace: str = "}"
) -> None:
        super().__init__()
        self.printer: "BasePrinter" = printer
        self.prefix: str = prefix
        self.suffix: str = suffix
        self.opening_brace = opening_brace
        self.closing_brace = closing_brace

    def type(self):
        return self.printer.type

    def __enter__(self):
        if self.prefix:
            self.printer.print(self.prefix)
        self.printer.print(self.opening_brace)
        self.printer.inc_indent()
        return self

    def __exit__(self, *_):
        self.printer.dec_indent()
        self.printer.print(self.closing_brace)
        if self.suffix:
            self.printer.print(self.suffix)

    def print(self, *args, **kwargs):
        self.printer.print(*args, **kwargs)

    def inc_indent(self):
        self.printer.inc_indent()
    
    def dec_indent(self):
        self.printer.dec_indent()


# Ooh; is this file-level hiding in Python?		
# __all__ = ["CppFile", "CodeFile"]
