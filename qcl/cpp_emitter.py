import abc
import os
import os.path
import re
import typing as t
import enum
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
        cpp_file = CppFile(CppFileType.Source, f"{output_file_stem}.cpp")
        hpp_file = CppFile(CppFileType.Header, f"{output_file_stem}.hpp")
        print(f"INFO: Generating C/C++ file pair:\n\t{cpp_file.path}\n\t{hpp_file.path}")
        
        # emitting declarations
        for src_file_path, src_obj in qyp.src_map.items():
            assert isinstance(src_obj, ast2.QySourceFile)
            for stmt in src_obj.stmt_list:
                self.emit_declarations_for_stmt(hpp_file, stmt, is_top_level=True)
                self.emit_declarations_for_stmt(cpp_file, stmt, is_top_level=True)

        # TODO: emitting type definitions
        #   - must order types, so can use DFS-like approach with a 'visited' set

        # TODO: emitting function definitions

        cpp_file.close()
        hpp_file.close()

    def emit_declarations_for_stmt(self, p: "BasePrinter", stmt: ast1.BaseStatement, is_top_level: bool):
        if isinstance(stmt, ast1.Bind1vStatement):
            if p.type == CppFileType.Source:
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
                with Block(p) as b:
                    self.emit_expression(b, stmt.initializer)
                p.print()
        elif isinstance(stmt, ast1.Bind1fStatement):
            pass
        elif isinstance(stmt, ast1.Bind1tStatement):
            pass
        elif isinstance(stmt, ast1.Type1vStatement):
            if p.type == CppFileType.Header:
                def_obj = stmt.lookup_def_obj()
                if def_obj.is_public:
                    _, def_type = def_obj.scheme.instantiate()
                    p.print(f"// extern {stmt.name}")
                    p.print(f"extern {self.translate_type(def_type)} {stmt.name};")
                    p.print()
        elif isinstance(stmt, ast1.ConstStatement):
            pass
        else:
            raise NotImplementedError(f"emit_declarations_for_stmt: {stmt}")

    def emit_expression(self, p: "BasePrinter", exp: ast1.BaseExpression):
        p.print(self.translate_expression(exp))

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

    def translate_expression(self, exp: ast1.BaseExpression):
        if isinstance(exp, ast1.IntExpression):
            if exp.width_in_bits == 1:
                return ['false', 'true'][exp.value]
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
            
            return ''.join(fragments)
        else:
            return f"<NotImplemented:{exp.desc}>"


#
# C++ generator:
# adapted from https://www.codeproject.com/script/Articles/ViewDownloads.aspx?aid=571645
#

# CodeFragment: t.TypeAlias = t.Union[str, t.List[str]]
CodeFragment = t.Union[str, t.List[str]]


class CppFileType(enum.Enum):
    Source = enum.auto()
    Header = enum.auto()


class BasePrinter(abc.ABC):
    @abc.abstractmethod
    def print(self, code_fragment: CodeFragment = ""):
        pass


class CppFile(BasePrinter):
    def __init__(
        self, 
        file_type: CppFileType,
        file_path: str,
        # indent_str: str='\t'
    ) -> None:
        super().__init__()
        self.type = file_type
        self.path = file_path
        self.os_file_handle = open(self.path, 'w')
        self.indent_count = 0
        self.indent_str = '\t'

        #
        # Post-constructor, but constructor-time:
        #

        # emitting preamble:
        if self.type == CppFileType.Header:
            self.print("#pragma once")
            self.print()
            self.print_common_stdlib_header_includes()
            self.print()
        elif self.type == CppFileType.Source:
            self.print(f"#include \"{os.path.basename(self.path)[:-len('.cpp')]}.hpp\"")
            self.print()
            self.print_common_stdlib_header_includes()
            self.print()

    def close(self):
        assert self.os_file_handle is not None
        self.os_file_handle.close()
        self.os_file_handle = None

    def print(self, code_fragment: CodeFragment = ""):
        if isinstance(code_fragment, str):
            lines = code_fragment.split('\n')
        else:
            assert isinstance(code_fragment, list)
            if __debug__:
                for line in code_fragment:
                    assert '\n' not in line
            lines = code_fragment
        
        for line in lines:
            for _ in range(self.indent_count):
                print(self.indent_str, end='', file=self.os_file_handle)

            print(line, file=self.os_file_handle)
        
        # print(file=self.os_file_handle)
    
    def print_common_stdlib_header_includes(self):
        self.print("#include <cstdint>")
        self.print("#include <string>")


class Block(BasePrinter):
    def __init__(self, cpp_file: CppFile, prefix: str = "", suffix: str = "") -> None:
        super().__init__()
        self.cpp_file: "CppFile" = cpp_file
        self.prefix: str = prefix
        self.suffix: str = suffix

    def __enter__(self):
        if self.prefix:
            self.cpp_file.print(self.prefix)
        self.cpp_file.print("{")
        self.cpp_file.indent_count += 1
        return self

    def __exit__(self, *_):
        self.cpp_file.indent_count -= 1
        self.cpp_file.print("}")
        if self.suffix:
            self.cpp_file.print(self.suffix)

    def print(self, *args, **kwargs):
        self.cpp_file.print(*args, **kwargs)


# Ooh; is this file-level hiding in Python?		
# __all__ = ["CppFile", "CodeFile"]
