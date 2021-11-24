# FIXME: this module is currently being rewritten.
#   - each 'translate' function now invokes 'visit' as well, which scans for types and defines them in files
#   - each ADT gets emitted to a separate file so that type dependencies are 'linked' by the preprocessor
#       - type dependencies are encoded by 'include's
#       - later, this will also enable implementing interfaces and methods very easily.
#       - NOTE: only public types get pushed into their own header; private types are defined in the main source.
#   - 

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
from . import panic

#
# Interface:
#

class Emitter(base_emitter.BaseEmitter):
    """
    Emitter compiles a QypSet into C++ code and a CMakeLists.txt file.
        - each Qyp is compiled into a '.hpp/.cpp' pair
        - each type definition is compiled into its own header file in the `types/` subdirectory
    """

    def __init__(self, rel_output_dir_path: str) -> None:
        super().__init__()
        self.root_rel_output_dir_path = rel_output_dir_path
        self.root_abs_output_dir_path = os.path.abspath(rel_output_dir_path)
        self.types_rel_output_dir_path = os.path.join(self.root_rel_output_dir_path, "types")
        self.types_abs_output_dir_path = os.path.abspath(self.types_rel_output_dir_path)
        self.pub_type_to_header_name_map = {}

    def emit_qyp_set(self, qyp_set: ast2.QypSet):
        os.makedirs(self.root_abs_output_dir_path, exist_ok=True)
        os.makedirs(self.types_abs_output_dir_path, exist_ok=True)

        for qyp_name, qyp in qyp_set.qyp_name_map.items():
            self.emit_per_type_headers(qyp_name, qyp)

        for qyp_name, qyp in qyp_set.qyp_name_map.items():
            self.emit_module_body(qyp_name, qyp)
        # for qyp_name, src_file_path, source_file in qyp_set.iter_source_files():
        #     self.emit_single_file(qyp_set, qyp_name, src_file_path, source_file)

    #
    # part 1: emitting type headers.
    #

    def emit_per_type_headers(self, qyp_name: str, qyp: ast2.Qyp):
        for src_file_path, src_obj in qyp.src_map.items():
            self.collect_pub_named_types(src_obj.stmt_list)

        # TODO: emit type definitions in a file
        #   - emit declaration and definition headers
        #       - can use `typedef <anonymous-type> TId` syntax to handle a wide variety of type definitions
        #       - some types have only a declaration and not a definition-- atomic aliases
        #   - include types' headers based on whether they are required via direct or indirect reference
        for qy_type, type_name in self.pub_type_to_header_name_map.items():
            type_files_stem = f"{self.types_abs_output_dir_path}/{type_name}"
            type_decl_file = CppFile(CppFileType.TypeDeclHeader, type_files_stem)
            type_def_file = CppFile(CppFileType.TypeDefHeader, type_files_stem)
            self.emit_one_per_type_header_pair(qy_type, type_name, type_decl_file, type_def_file)
            type_decl_file.close()
            type_def_file.close()

    def collect_pub_named_types(self, stmt_list):
        for stmt in stmt_list:
            if isinstance(stmt, ast1.Bind1tStatement):
                def_obj = stmt.lookup_def_obj()
                assert isinstance(def_obj, typer.TypeDefinition)
                assert not def_obj.scheme.vars
                
                # NOTE: type definitions are always public by default
                _, def_type = def_obj.scheme.instantiate()
                if def_type in self.pub_type_to_header_name_map:
                    panic.because(
                        panic.ExitCode.ScopingError,
                        f"Public type symbol {stmt.name} re-defined across different packages."
                    )
                self.pub_type_to_header_name_map[def_type] = stmt.name

    def emit_one_per_type_header_pair(self, qy_type, type_name, type_decl_file, type_def_file):
        # TODO: add common includes to type_decl_file
        # TODO: add include to type_decl_file in type_def_file
        
        # emitting a forward declaration
        if qy_type.is_atomic:
            type_decl_file.print(f"typedef {self.translate_type(qy_type)} {type_name};")
            type_decl_file.print()
        elif qy_type.is_composite:
            if qy_type.kind() == types.TypeKind.Struct:
                type_decl_file.print(f"struct {type_name};")
            elif qy_type.kind() == types.TypeKind.Union:
                type_decl_file.print(f"union {type_name};")
            elif qy_type.kind() == types.TypeKind.Procedure:
                assert isinstance(qy_type, types.ProcedureType)
                cs_arg_str = ', '.join(map(self.translate_type, qy_type.arg_types))
                type_decl_file.print(f"typedef {qy_type.ret_type}(*{type_name})({cs_arg_str})")
            else:
                raise NotImplementedError(f"Unknown composite def_type in emitter for Bind1tStatement:forward: {qy_type}")
        else:
            raise NotImplementedError("Unknown def type in emitter for Bind1tStatement")
        
        # linking definition to declaration:
        type_def_file.include_paths.append((False, type_decl_file.file_name))

        # TODO: emit definitions
        # TODO: insert 'include' to declaration (if indirect reference) or definition (if direct reference) header 
        #       files-- can also check for cycles here.

    #
    # part 2: emitting module body
    #

    def emit_module_body(self, qyp_name: str, qyp: ast2.Qyp):
        output_file_stem = os.path.join(self.root_abs_output_dir_path, qyp_name)
        hpp_file = CppFile(CppFileType.MainHeader, output_file_stem)
        cpp_file = CppFile(CppFileType.MainSource, output_file_stem)
        
        print(f"INFO: Generating C/C++ file pair:\n\t{cpp_file.path}\n\t{hpp_file.path}")
        
        for src_file_path, src_obj in qyp.src_map.items():
            assert isinstance(src_obj, ast2.QySourceFile)
            for stmt in src_obj.stmt_list:
                self.emit_module_body_stmt(cpp_file, hpp_file, stmt, is_top_level=True)

        cpp_file.close()
        hpp_file.close()

    def emit_module_body_stmt(self, c: "CppFile", h: "CppFile", stmt: ast1.BaseStatement, is_top_level: bool):
        assert c.type == CppFileType.MainSource
        assert h.type == CppFileType.MainHeader
        if isinstance(stmt, ast1.Bind1vStatement):
            def_obj = stmt.lookup_def_obj()
            assert isinstance(def_obj, typer.BaseDefinition)
            assert not def_obj.scheme.vars
            _, def_type = def_obj.scheme.instantiate()
            bind_cpp_fragments = []
            if not def_obj.is_public:
                bind_cpp_fragments.append('static')
            bind_cpp_fragments.append(self.translate_type(def_type))
            bind_cpp_fragments.append(def_obj.name)
            c.print(f"// bind {stmt.name} = {stmt.initializer.desc}")
            c.print(' '.join(bind_cpp_fragments))
            with Block(c, closing_brace="};") as b:
                self.emit_expression(c, stmt.initializer)
            c.print()
        elif isinstance(stmt, ast1.Bind1fStatement):
            assert is_top_level
            def_obj = stmt.lookup_def_obj()
            assert isinstance(def_obj, typer.BaseDefinition)
            assert not def_obj.scheme.vars
            _, def_type = def_obj.scheme.instantiate()
            assert isinstance(def_type, types.ProcedureType)
            arg_fragments = [
                f"{self.translate_type(arg_type)} {arg_name}"
                for arg_type, arg_name in zip(def_type.arg_types, stmt.args)
            ]
            c.print(f"// bind {stmt.name} = {{...}}")
            if not def_obj.is_public:
                c.print('static')
            c.print(self.translate_type(def_type.ret_type))
            c.print(def_obj.name)
            with Block(c, opening_brace='(', closing_brace=')') as b:
                c.print(',\n'.join(arg_fragments))
            with Block(c) as b:
                self.emit_block(c, h, stmt.body)
            c.print()
        elif isinstance(stmt, ast1.Bind1tStatement):
            assert is_top_level
            def_obj = stmt.lookup_def_obj()
            assert def_obj is not None
            assert not def_obj.scheme.vars
            _, def_type = def_obj.scheme.instantiate()
            assert isinstance(def_type, types.BaseType)
            c.print(f"// bind {stmt.name} = {{...}}")
            c.print()
        elif isinstance(stmt, ast1.Type1vStatement):
            def_obj = stmt.lookup_def_obj()
            if def_obj.is_public:
                _, def_type = def_obj.scheme.instantiate()
                h.print(f"// pub {stmt.name}")
                if isinstance(def_type, types.ProcedureType):
                    args_list = ', '.join(map(self.translate_type, def_type.arg_types))
                    h.print(f"extern {self.translate_type(def_type.ret_type)} {stmt.name}({args_list});")
                else:
                    h.print(f"extern {self.translate_type(def_type)} {stmt.name};")
                h.print()
        elif isinstance(stmt, ast1.ConstStatement):
            pass
        elif isinstance(stmt, ast1.ReturnStatement):
            c.print(f"return {self.translate_expression(stmt.returned_exp)};")
        elif isinstance(stmt, ast1.IteStatement):
            c.print(f"if ({self.translate_expression(stmt.cond)})")
            with Block(c):
                self.emit_block(c, h, stmt.then_block)
            c.print("else")
            with Block(c):
                self.emit_block(c, h, stmt.else_block)
        else:
            raise NotImplementedError(f"emit_declarations_for_stmt: {stmt}")

    def emit_expression(self, f: "CppFile", exp: ast1.BaseExpression):
        f.print(self.translate_expression(exp))

    def emit_block(self, c: "CppFile", h: "CppFile", block: t.List[ast1.BaseStatement]):
        for stmt in block:
            self.emit_module_body_stmt(c, h, stmt, is_top_level=False)

    def translate_type(self, qy_type: types.BaseType) -> str:
        opt_named_pub_type = self.pub_type_to_header_name_map.get(qy_type, None)
        if opt_named_pub_type is not None:
            return opt_named_pub_type
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
        elif isinstance(qy_type, types.BaseCompositeType):
            opt_existing_name = self.pub_type_to_header_name_map.get(qy_type)
            if opt_existing_name is not None:
                return opt_existing_name
            else:
                if isinstance(qy_type, (types.StructType, types.UnionType)):
                    field_str_fragments = [
                        f"{self.translate_type(field_type)} {field_name};" 
                        for field_name, field_type in qy_type.fields
                    ]
                    fields_str = ' '.join(field_str_fragments)
                    if isinstance(qy_type, types.StructType):
                        return f"struct {{ {fields_str} }}"
                    else:
                        assert isinstance(qy_type, types.UnionType)
                        return f"union {{ {fields_str} }}"
                elif isinstance(qy_type, (types.ProcedureType)):
                    args_str = ', '.join((
                        self.translate_type(arg_type)
                        for arg_type in qy_type.arg_types
                    ))
                    return f"std::function<{self.translate_type(qy_type.ret_type)}({args_str})>"
                else:
                    raise NotImplementedError("Unknown compound type in 'translate_type'")
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
        
        elif isinstance(exp, ast1.DotIdExpression):
            container_str, container_type = self.translate_expression_with_type(exp.container)
            ret_str = f"{container_str}.{exp.key}"
            ret_type = None
            assert isinstance(container_type, types.BaseAlgebraicType)
            for field_name, field_type in container_type.fields:
                if field_name == exp.key:
                    ret_type = field_type
                    break
            assert ret_type is not None
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
    TypeDefHeader = enum.auto()
    TypeDeclHeader = enum.auto()


class CppFile(object):
    file_type_suffix = {
        CppFileType.MainHeader: ".hpp",
        CppFileType.MainSource: ".cpp",
        CppFileType.TypeDefHeader: ".def.hpp",
        CppFileType.TypeDeclHeader: ".decl.hpp"
    }

    def __init__(
        self, 
        file_type: CppFileType,
        file_stem: str,
        # indent_str: str='\t'
    ) -> None:
        super().__init__()
        self._type = file_type
        self.stem = file_stem
        self.stem_base = os.path.basename(self.stem)
        self.path = f"{self.stem}{CppFile.file_type_suffix[self._type]}"
        self.os_file_handle = open(self.path, 'w', buffering=4*1024)
        self.indent_count = 0
        self.indent_str = '\t'
        self.include_paths: t.List[bool, str] = []
        self.document_sections = {
            "prefix": [],
            "body": []
        }
        
        #
        # Post-constructor, but constructor-time:
        #

        # emitting preamble:
        if self.type == CppFileType.MainHeader:
            self.print("#pragma once", target='prefix')
            self.print(target='prefix')
            self.add_common_stdlib_header_includes()
        elif self.type == CppFileType.MainSource:
            self.include_paths.append((False, self.stem_base + CppFile.file_type_suffix[CppFileType.MainHeader]))
        elif self.type == CppFileType.TypeDeclHeader:
            self.print("#pragma once", target='prefix')
            self.print(target='prefix')
            self.add_common_stdlib_header_includes()
        elif self.type == CppFileType.TypeDefHeader:
            self.print("#pragma once", target='prefix')
            self.print(target='prefix')

    @property
    def file_name(self):
        return os.path.basename(self.path)

    @property
    def type(self):
        return self._type

    def close(self):
        assert self.os_file_handle is not None

        #
        # writing all data in a deferred way:
        #

        # prefix:
        prefix_lines = self.document_sections['prefix']
        for prefix_line in prefix_lines:
            print(prefix_line, file=self.os_file_handle)

        # includes:
        for is_abs, include_path in self.include_paths:
            if is_abs:
                print(f"#include <{include_path}>", file=self.os_file_handle)
            else:
                print(f"#include \"{include_path}\"", file=self.os_file_handle)
        print(file=self.os_file_handle)

        # body lines:
        body_lines = self.document_sections['body']
        for body_line in body_lines:
            print(body_line, file=self.os_file_handle)

        self.os_file_handle.close()
        self.os_file_handle = None

    def print(self, code_fragment: CodeFragment = "", target="body"):
        if isinstance(code_fragment, str):
            lines = code_fragment.split('\n')
        elif isinstance(code_fragment, list):
            if __debug__:
                for line in code_fragment:
                    assert '\n' not in line
            lines = code_fragment
        else:
            raise ValueError(f"Invalid CodeFragment: {code_fragment}")
        
        target_lines_list = self.document_sections[target]
        for line in lines:
            target_lines_list.append(f"{self.indent_str*self.indent_count}{line}")
            
        # print(file=self.os_file_handle)
    
    def add_common_stdlib_header_includes(self):
        self.include_paths.append((True, "cstdint"))
        self.include_paths.append((True, "string"))
        self.include_paths.append((True, "functional"))

    def inc_indent(self):
        self.indent_count += 1
    
    def dec_indent(self):
        self.indent_count -= 1


class Block(object):
    def __init__(
        self, 
        cpp_file: "CppFile", 
        prefix: str = "", 
        suffix: str = "", 
        opening_brace: str = "{",
        closing_brace: str = "}"
) -> None:
        super().__init__()
        self.cpp_file: "CppFile" = cpp_file
        self.prefix: str = prefix
        self.suffix: str = suffix
        self.opening_brace = opening_brace
        self.closing_brace = closing_brace

    def type(self):
        return self.printer.type

    def __enter__(self):
        if self.prefix:
            self.cpp_file.print(self.prefix)
        self.cpp_file.print(self.opening_brace)
        self.cpp_file.inc_indent()
        return self

    def __exit__(self, *_):
        self.cpp_file.dec_indent()
        self.cpp_file.print(self.closing_brace)
        if self.suffix:
            self.cpp_file.print(self.suffix)


# Ooh; is this file-level hiding in Python?		
# __all__ = ["CppFile", "CodeFile"]
