"""
FIXME: need to update this backend to deal with lambdas, 'do' expressions.
"""

import dataclasses
import os
import os.path
import typing as t
import enum
import json
import itertools
import shutil

from . import feedback
from . import ast1
from . import ast2
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
        self.types_abs_output_dir_path = os.path.join(self.root_abs_output_dir_path, "types")
        self.modules_abs_output_dir_path = os.path.join(self.root_abs_output_dir_path, "modules")
        self.pub_type_to_header_name_map = {}
        
        # v-- used by 'check_global_definition'
        self.global_symbol_loc_map = {}

    def emit_qyp_set(self, qyp_set: ast2.QypSet):
        # cleaning old directories:
        # on macOS, Windows, with case-insensitive paths, renaming symbols with different case 
        # results in stale files being used instead.
        if os.path.isdir(self.root_abs_output_dir_path):
            shutil.rmtree(self.root_abs_output_dir_path)

        # creating fresh directories:
        os.makedirs(self.root_abs_output_dir_path, exist_ok=False)
        os.makedirs(self.types_abs_output_dir_path, exist_ok=False)
        os.makedirs(self.modules_abs_output_dir_path, exist_ok=False)

        # collecting all extern headers:
        extern_header_source_files = []
        for qyp_name, qyp in qyp_set.qyp_name_map.items():
            if isinstance(qyp, ast2.CQyx):
                for c_source_file in qyp.c_source_files:
                    if c_source_file.is_header:
                        assert os.path.isabs(c_source_file.file_path)
                        extern_header_source_files.append(c_source_file)

        # emitting the 'types' subdirectory of build:
        for qyp_name, qyp in qyp_set.qyp_name_map.items():
            if isinstance(qyp, ast2.NativeQyp):
                self.emit_native_qyp_per_type_headers(qyp_name, qyp, extern_header_source_files)
            # else:
            #     raise NotImplementedError(f"'emit_per_type_headers' for Qyp of type '{qyp.__class__.__name__}'")

        # emitting the 'modules' subdirectory of build:
        for qyp_name, qyp in qyp_set.qyp_name_map.items():
            if isinstance(qyp, ast2.NativeQyp):
                self.emit_native_qyp_module_body(qyp_name, qyp, extern_header_source_files)
            # else:
            #     raise NotImplementedError(f"'emit_module_body' for Qyp of type '{qyp.__class__.__name__}'")
        
        # emitting any CMake files used to build the whole project:
        self.emit_cmake_lists(qyp_set)

    #
    # part 1: emitting type headers.
    #

    def emit_native_qyp_per_type_headers(self, qyp_name: str, qyp: ast2.NativeQyp, extern_header_source_files: t.List[ast2.BaseSourceFile]):
        for src_file_path, src_obj in qyp.src_map.items():
            self.collect_pub_named_types(src_obj.stmt_list)

        # emit type definitions in a file unique to this type
        #   - emit declaration and definition headers
        #       - can use `typedef <anonymous-type> TId` syntax to handle a wide variety of type definitions
        #       - some types have only a declaration and not a definition-- atomic aliases
        #   - include types' headers based on whether they are required via direct or indirect reference
        for qy_type, type_name in self.pub_type_to_header_name_map.items():
            # creating file writers, adding all extern source paths as headers:
            type_files_stem = f"{self.types_abs_output_dir_path}/{type_name}"
            type_decl_file = CppFileWriter(CppFileType.TypeDeclHeader, type_files_stem)
            type_def_file = CppFileWriter(CppFileType.TypeDefHeader, type_files_stem)
            for source_file in extern_header_source_files:
                abs_extern_header_path = source_file.file_path
                type_decl_file.include_specs.append(IncludeSpec(abs_extern_header_path, use_angle_brackets=False, extern_str=source_file.extern_str))
                type_def_file.include_specs.append(IncludeSpec(abs_extern_header_path, use_angle_brackets=False, extern_str=source_file.extern_str))
            
            # emitting:
            self.emit_one_per_type_header_pair(qy_type, type_name, type_decl_file, type_def_file)
            
            # finalizing:
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
                ret_type = self.translate_type(qy_type.ret_type)
                cs_arg_str = ', '.join(map(self.translate_type, qy_type.arg_types))
                if qy_type.has_closure_slot:
                    type_decl_file.print(f"using {type_name} = std::function<{ret_type}({cs_arg_str})>")
                else:
                    type_decl_file.print(f"typedef {ret_type}(*{type_name})({cs_arg_str})")
            else:
                raise NotImplementedError(f"Unknown composite def_type in emitter for Bind1tStatement:forward: {qy_type}")
        else:
            raise NotImplementedError("Unknown def type in emitter for Bind1tStatement")
        
        # linking definition to declaration:
        type_def_file.include_specs.append(IncludeSpec(use_angle_brackets=False, include_path=type_decl_file.file_name))

        # emitting definitions:
        if qy_type.is_composite:
            if qy_type.kind() in (types.TypeKind.Struct, types.TypeKind.Union):
                if qy_type.kind() == types.TypeKind.Struct:
                    type_def_file.print(f"struct {type_name}")
                else:
                    assert qy_type.kind() == types.TypeKind.Union
                    type_def_file.print(f"union {type_name}")
                with Block(type_def_file, closing_brace="}", close_with_semicolon=True):
                    for field_name, field_type in qy_type.fields:
                        # printing the field type:
                        type_def_file.print(f"{self.translate_type(field_type)} {field_name};")
                        # adding an 'include' to all used types:
                        self.insert_type_ref_includes(type_def_file, field_type, direct_ref=True)
            elif qy_type.kind() == types.TypeKind.Procedure:
                return_type = qy_type.ret_type
                args_str = ', '.join((
                    f"{self.translate_type(arg_type)}"
                    for arg_type in qy_type.arg_types()
                ))
                type_def_file.print(f"using {type_name} = {return_type}(*)({args_str});")

    def insert_type_ref_includes(self, print_file: "CppFileWriter", qy_type: types.BaseType, direct_ref: bool):
        # NOTE: every compound just includes dependencies required to write the type.
        
        # first, checking if this type has a name: just include it directly.
        opt_existing_name = self.pub_type_to_header_name_map.get(qy_type, None)
        if opt_existing_name:
            if direct_ref:
                extension = CppFileWriter.file_type_suffix[CppFileType.TypeDefHeader]
            else:
                extension = CppFileWriter.file_type_suffix[CppFileType.TypeDeclHeader]
            print_file.include_specs.append(IncludeSpec(use_angle_brackets=False, include_path=f"{opt_existing_name}{extension}"))

        # otherwise, this is an anonymous type.
        # we must include all types used to write this type.
        # WARNING: this output depends heavily on 'translate_type'-- it could be merged.
        if qy_type.is_atomic:
            # do nothing-- all atomic types are built-in.
            pass
        elif qy_type.is_composite:
            if isinstance(qy_type, types.UnsafeCPointerType):
                self.insert_type_ref_includes(print_file, qy_type.pointee_type, direct_ref=False)
            else:
                for field_type in qy_type.field_types:
                    self.insert_type_ref_includes(print_file, field_type, direct_ref=direct_ref)

    def check_global_definition(self, name: str, loc: feedback.ILoc, is_public: bool):
        opt_existing_loc = self.global_symbol_loc_map.get(name, None)
        if opt_existing_loc is not None:
            headline = (
                f"Public global symbol `{name}` found in two or more `Qyp`s. Cannot resolve ambiguity."
                if is_public else
                f"Private global symbol `{name}` reused across different modules. Cannot generate C++ code."
            )
            panic.because(
                panic.ExitCode.EmitterError,
                f"{headline}\n"
                f"\tfirst: {opt_existing_loc}\n"
                f"\tlater: {loc}"
            )
        self.global_symbol_loc_map[name] = loc

    #
    # part 2: emitting module body
    #

    def emit_native_qyp_module_body(self, qyp_name: str, qyp: ast2.NativeQyp, extern_header_source_files: t.List[ast2.BaseSourceFile]):
        # creating output files, adding external project headers to all includes:
        output_file_stem = os.path.join(self.modules_abs_output_dir_path, qyp_name)
        hpp_file = CppFileWriter(CppFileType.MainHeader, output_file_stem)
        cpp_file = CppFileWriter(CppFileType.MainSource, output_file_stem)
        for source_file in extern_header_source_files:
            abs_extern_header_path = source_file.file_path
            hpp_file.include_specs.append(IncludeSpec(abs_extern_header_path, use_angle_brackets=False, extern_str=source_file.extern_str))
            cpp_file.include_specs.append(IncludeSpec(abs_extern_header_path, use_angle_brackets=False, extern_str=source_file.extern_str))
        
        print(f"INFO: Generating C/C++ file pair:\n\t{cpp_file.path}\n\t{hpp_file.path}")
        
        for src_file_path, src_obj in qyp.src_map.items():
            assert isinstance(src_obj, ast2.QySourceFile)
            for stmt in src_obj.stmt_list:
                self.emit_module_body_stmt(cpp_file, hpp_file, stmt, is_top_level=True)

        cpp_file.close()
        hpp_file.close()

    def emit_module_body_stmt(self, c: "CppFileWriter", h: "CppFileWriter", stmt: ast1.BaseStatement, is_top_level: bool):
        assert c.type == CppFileType.MainSource
        assert h.type == CppFileType.MainHeader
        
        if isinstance(stmt, ast1.Bind1vStatement):
            def_obj = stmt.lookup_def_obj()
            if stmt.wb_ctx.kind == typer.ContextKind.TopLevelOfQypSet:
                self.check_global_definition(stmt.name, stmt.loc, def_obj.is_public)
        
            assert isinstance(def_obj, typer.BaseDefinition)
            assert not def_obj.scheme.vars
            _, def_type = def_obj.scheme.instantiate()
        
            c.print(f"// bind {stmt.name} = {stmt.initializer.desc}")
            if def_type is types.VoidType.singleton:
                c.print("// binding elided for 'void' type variable.")
            else:
                bind_cpp_fragments = []
                if not def_obj.is_public:
                    bind_cpp_fragments.append('static')
                bind_cpp_fragments.append(self.translate_type(def_type))
                bind_cpp_fragments.append(def_obj.name)
                bind_cpp_fragments.append("=")
            
                c.print(' '.join(bind_cpp_fragments))
            
            # regardless of return-type, evaluating the RHS in case there are any side-effects:
            with Block(c, opening_brace='(', closing_brace=")", close_with_semicolon=True):
                self.emit_expression(c, stmt.initializer)
            c.print()
        
        elif isinstance(stmt, ast1.DiscardStatement):
            with Block(c, opening_brace='(', closing_brace=")", close_with_semicolon=True):
                self.emit_expression(c, stmt.discarded_exp)
            c.print()
        
        elif isinstance(stmt, ast1.Bind1fStatement):
            assert is_top_level

            def_obj = stmt.lookup_def_obj()
            if stmt.wb_ctx.kind == typer.ContextKind.TopLevelOfQypSet:
                self.check_global_definition(stmt.name, stmt.loc, def_obj.is_public)
        
            assert isinstance(def_obj, typer.BaseDefinition)
            assert not def_obj.scheme.vars
            _, def_type = def_obj.scheme.instantiate()
            assert isinstance(def_type, types.ProcedureType)
            
            c.print(f"// bind {stmt.name} = {{...}}")
            if not def_obj.is_public and stmt.name != 'main':
                c.print('static')
            c.print(self.translate_type(def_type.ret_type))
            if not stmt.args:
                c.print(f"{def_obj.name}()")
            else:
                c.print(def_obj.name)
                with Block(c, opening_brace='(', closing_brace=')') as b:
                    c.print(',\n'.join((
                        f"{self.translate_type(arg_type)} {arg_name}"
                        for arg_type, arg_name in zip(def_type.arg_types, stmt.args)
                    )))
            with Block(c) as b:
                self.emit_expression(c, stmt.body_exp)
            c.print()
        
        elif isinstance(stmt, ast1.Bind1tStatement):
            assert is_top_level
            
            c.print(f"// bind {stmt.name} = {{...}}")

            def_obj = stmt.lookup_def_obj()
            if stmt.wb_ctx.kind == typer.ContextKind.TopLevelOfQypSet:
                self.check_global_definition(stmt.name, stmt.loc, def_obj.is_public)
        
            assert def_obj is not None
            assert not def_obj.scheme.vars
            _, def_type = def_obj.scheme.instantiate()
            if def_type in self.pub_type_to_header_name_map:
                # public type => it has its own header pair => include this in the header
                type_def_extension = CppFileWriter.file_type_suffix[CppFileType.TypeDefHeader]
                h.include_specs.append(IncludeSpec(use_angle_brackets=False, include_path=f"types/{stmt.name}{type_def_extension}"))
            else:
                # private type => define in 'c' file
                assert isinstance(def_type, types.BaseType)
                c.print(f"using {stmt.name} = {self.translate_type(def_type)}")
            
            c.print()
        elif isinstance(stmt, ast1.Type1vStatement):
            def_obj = stmt.lookup_def_obj()
            if def_obj.is_public:
                _, def_type = def_obj.scheme.instantiate()
                h.print(f"// pub {stmt.name}")
                if isinstance(def_type, types.ProcedureType):
                    if is_top_level:
                        args_list = ', '.join(map(self.translate_type, def_type.arg_types))
                        h.print(f"extern {self.translate_type(def_type.ret_type)} {stmt.name}({args_list});")
                    else:
                        raise NotImplementedError("Cannot type a function in a non-global context")
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

        elif isinstance(stmt, ast1.ForStatement):
            c.print("for (;;)")
            with Block(c):
                self.emit_block(c, h, stmt.body)

        elif isinstance(stmt, ast1.BreakStatement):
            c.print("break;")

        elif isinstance(stmt, ast1.ContinueStatement):
            c.print("continue;")

        else:
            raise NotImplementedError(f"emit_declarations_for_stmt: {stmt}")

    def emit_expression(self, f: "CppFileWriter", exp: ast1.BaseExpression):
        f.print(self.translate_expression(exp))

    def emit_block(self, c: "CppFileWriter", h: "CppFileWriter", block: t.List[ast1.BaseStatement]):
        for stmt in block:
            self.emit_module_body_stmt(c, h, stmt, is_top_level=False)

    def translate_type(self, qy_type: types.BaseType) -> str:
        """
        Emits the C++ translation of a given Qy type.
        NOTE: only usable in the context of defining a _single_ variable.
            - cf pointer type
        """

        if qy_type.is_var:
            panic.because(
                panic.ExitCode.EmitterError,
                f"Typer failed: residual type variables found in emitter: {qy_type}"
            )

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
                    return f"{self.translate_type(qy_type.ret_type)}(*)({args_str})"
                elif isinstance(qy_type, (types.UnsafeCPointerType)):
                    return f"{self.translate_type(qy_type.pointee_type)}*"
                else:
                    raise NotImplementedError("Unknown compound type in 'translate_type'")
        else:
            raise NotImplementedError(f"Don't know how to translate type to C++: {qy_type}")
            # print(f"WARNING: Don't know how to translate type to C++: {qy_type}")
            # return f"<NotImplemented:{qy_type}>"

    def translate_expression(self, exp: ast1.BaseExpression) -> str:
        # FIXME: can 'translate_expression_with_type' be replaced by looking up 'exp.wb_type'?
        ret_str, ret_type = self.translate_expression_with_type(exp)
        assert isinstance(ret_str, str)
        # assert isinstance(ret_type, types.BaseType)
        assert isinstance(ret_type, types.BaseType) or ret_type is None
        return ret_str

    def translate_expression_with_type(self, exp: ast1.BaseExpression) -> t.Tuple[str, types.BaseConcreteType]:
        if isinstance(exp, ast1.IdRefExpression):
            # FIXME: what if lookup type is 'void'? Must elide/default somehow.
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
            operand_type, operand_str = self.translate_expression_with_type(exp.operand)

            if exp.operator == ast1.UnaryOperator.Do:
                return f"{operand_str}()"
            else:
                operator_str = {
                    ast1.UnaryOperator.DeRef: "*",
                    ast1.UnaryOperator.LogicalNot: "!",
                    ast1.UnaryOperator.Minus: "-",
                    ast1.UnaryOperator.Plus: "+"
                }[exp.operator]
                
                # dispatch based on `operand_type` to select the right operator and return type:
                # for now, Qy's builtin unary operators are a subset of C++'s builtin unary operators.            
                if exp.operator == ast1.UnaryOperator.DeRef:
                    operand_ptr_type = operand_type
                    assert isinstance(operand_ptr_type, types.UnsafeCPointerType)
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
                ast1.BinaryOperator.RSh: ">>",
                ast1.BinaryOperator.LThan: "<",
                ast1.BinaryOperator.GThan: ">",
                ast1.BinaryOperator.LThan: "<=",
                ast1.BinaryOperator.GThan: ">=",
            }[exp.operator]
            lt_operand_str, lt_operand_type = self.translate_expression_with_type(exp.lt_operand_exp)
            rt_operand_str, rt_operand_type = self.translate_expression_with_type(exp.rt_operand_exp)
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

        elif isinstance(exp, ast1.MakeExpression):
            if exp.wb_type.is_atomic and len(exp.initializer_list) == 1:
                # 'cast' expressions
                target_type_str = self.translate_type(exp.wb_type)
                arg_str = self.translate_expression(exp.initializer_list[0])
                return f"static_cast<{target_type_str}>({arg_str})", exp.wb_type
            else:
                # constructor invocation
                constructor_ts = self.translate_type(exp.wb_type)
                initializer_exps = [self.translate_expression(exp) for exp in exp.initializer_list]
                constructor_str = f"{constructor_ts}{{{','.join(initializer_exps)}}}"
                return constructor_str, exp.made_ts.wb_type
        
        elif isinstance(exp, ast1.IfExpression):
            cond_str = self.translate_expression(exp.cond_exp)
            then_str = self.translate_expression(exp.then_exp)
            else_str = self.translate_expression(exp.else_exp)
            ite_str = f"({cond_str} ? ({then_str}) : ({else_str}))"
            return ite_str, exp.wb_type

        elif isinstance(exp, ast1.LambdaExpression):
            closure_prefix_str = '[=]' if exp.no_closure else '[]'
            arg_names_str = '(' + f", ".join(f"auto {arg_name}" for arg_name in exp.arg_names) + ')'
            # FIXME: need a way to translate blocks!
            raise NotImplementedError("emitting a LambdaExpression")
            return lambda_str, exp.wb_type

        else:
            raise NotImplementedError(f"Don't know how to translate expression to C++: {exp}")
            # print(f"WARNING: Don't know how to translate expression to C++: {exp}")
            # return f"<NotImplemented:{exp.desc}>", None

    #
    # part 3: generating CMakeLists.txt files
    #

    def emit_cmake_lists(self, qyp_set: ast2.QypSet):
        cml_file_path = f"{self.root_abs_output_dir_path}/CMakeLists.txt"
        output_path = normalize_backslash_path(self.root_abs_output_dir_path)
            
        with open(cml_file_path, 'w') as cml_file:
            def cml_print(*args, **kwargs):
                assert 'file' not in kwargs
                print(*args, **kwargs, file=cml_file)
            
            # configuring CMake:
            cml_print(f"cmake_minimum_required(VERSION 3.0.0)")
            cml_print(f"project({qyp_set.root_qyp.js_name})")
            cml_print()
            cml_print(f"include_directories({output_path})")
            cml_print()
            cml_print(f"set(CMAKE_CXX_STANDARD 17)")
            cml_print()
            cml_print(f"set(CMAKE_CXX_FLAGS -Wno-parentheses-equality)")
            cml_print()

            # all source files go into one 'add_executable' for now.
            # more granular package-by-package control will require inter-package dependency analysis, which can get hairy.
            
            # first, visiting all qyps and gathering a list of files:
            main_target_name = None
            extern_source_file_paths = []
            native_source_file_paths = []
            for qyp_name, qyp in qyp_set.qyp_name_map.items():
                if isinstance(qyp, ast2.NativeQyp):
                    if qyp is qyp_set.root_qyp:
                        # expect only one root per project:
                        assert main_target_name is None
                        main_target_name = qyp_name

                    native_source_file_paths.append(f"modules/{qyp_name}{CppFileWriter.file_type_suffix[CppFileType.MainHeader]}")
                    native_source_file_paths.append(f"modules/{qyp_name}{CppFileWriter.file_type_suffix[CppFileType.MainSource]}")
                elif isinstance(qyp, ast2.CQyx):
                    for c_source_file in qyp.c_source_files:
                        if not c_source_file.is_header:
                            file_path = self.relpath(c_source_file.file_path)
                            extern_source_file_paths.append(file_path)
                else:
                    raise NotImplementedError(f"emit_cmake_lists: Unknown Qyp of type {qyp.__class__.__name__}")

            # emitting 'add_executable' call to tie everything together:
            assert main_target_name is not None
            cml_print(f"add_executable({main_target_name}")
            for source_file_path in itertools.chain(extern_source_file_paths, native_source_file_paths):
                cml_print(f"\t{source_file_path}")
            cml_print(")")

    def relpath(self, input_path):
        return normalize_backslash_path(os.path.relpath(input_path, self.root_abs_output_dir_path))


#
# C++ generator:
# adapted from https://www.codeproject.com/script/Articles/ViewDownloads.aspx?aid=571645
#

# CodeFragment: t.TypeAlias = t.Union[str, t.List[str]]
CodeFragment = t.Union[str, t.List[str]]

@dataclasses.dataclass
class IncludeSpec:
    include_path: str
    use_angle_brackets: bool
    extern_str: t.Optional[str] = None


class CppFileType(enum.Enum):
    MainSource = enum.auto()
    MainHeader = enum.auto()
    TypeDefHeader = enum.auto()
    TypeDeclHeader = enum.auto()


class CppFileWriter(object):
    file_type_suffix = {
        CppFileType.MainHeader: ".hpp",
        CppFileType.MainSource: ".cpp",
        CppFileType.TypeDefHeader: ".def.hpp",
        CppFileType.TypeDeclHeader: ".decl.hpp"
    }

    def __init__(
        self, 
        file_type: CppFileType,
        file_stem: str
        # indent_str: str='\t'
    ) -> None:
        super().__init__()
        self._type = file_type
        self.stem = file_stem
        self.stem_base = os.path.basename(self.stem)
        self.path = f"{self.stem}{CppFileWriter.file_type_suffix[self._type]}"
        self.os_file_handle = open(self.path, 'w', buffering=4*1024)
        self.indent_count = 0
        self.indent_str = '\t'
        self.include_specs: t.List[IncludeSpec] = []
        self.document_sections = {"prefix": [], "body": []}
        
        #
        # Post-constructor, but constructor-time:
        #

        # emitting preamble:
        if self.type == CppFileType.MainHeader:
            self.print("#pragma once", target='prefix')
            self.print(target='prefix')
            self.add_common_stdlib_header_includes()
        elif self.type == CppFileType.MainSource:
            # including the header file, as is customary for implementation files:
            include_spec = IncludeSpec(use_angle_brackets=False, include_path=self.stem_base + CppFileWriter.file_type_suffix[CppFileType.MainHeader])
            self.include_specs.append(include_spec)
            self.add_common_stdlib_header_includes()
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
        cpp_include_specs = [include_spec for include_spec in self.include_specs if include_spec.extern_str is None]
        c_include_specs = [include_spec for include_spec in self.include_specs if include_spec.extern_str == "C"]
        assert len(cpp_include_specs) + len(c_include_specs) == len(self.include_specs)
        abs_cpp_include_specs = [it.include_path for it in cpp_include_specs if it.use_angle_brackets]
        rel_cpp_include_specs = [it.include_path for it in cpp_include_specs if not it.use_angle_brackets]
        abs_extern_c_include_specs = [it.include_path for it in c_include_specs if it.use_angle_brackets]
        rel_extern_c_include_specs = [it.include_path for it in c_include_specs if not it.use_angle_brackets]

        if abs_cpp_include_specs:
            self.print_includes(abs_cpp_include_specs, True)
        if rel_cpp_include_specs:
            self.print_includes(rel_cpp_include_specs, False)
        if abs_extern_c_include_specs:
            self.print_includes(abs_extern_c_include_specs, True, "C")
        if rel_extern_c_include_specs:
            self.print_includes(rel_extern_c_include_specs, False, "C")

        # body lines:
        body_lines = self.document_sections['body']
        for body_line in body_lines:
            print(body_line, file=self.os_file_handle)

        self.os_file_handle.close()
        self.os_file_handle = None

    def print_includes(self, include_specs, use_angle_brackets, opt_extern_str=None):
        open_quote, close_quote = ('<', '>') if use_angle_brackets else ('"', '"')
        
        if opt_extern_str:
            indent_str = '\t'
            print(f"extern \"{opt_extern_str}\" {{", file=self.os_file_handle)
        else:
            indent_str = ''

        for include_path in include_specs:
            sep_normalized_include_path = normalize_backslash_path(include_path)
            clean_include_path = sep_normalized_include_path
            print(f"{indent_str}#include {open_quote}{clean_include_path}{close_quote}", file=self.os_file_handle)
        
        if opt_extern_str:
            print(f"}}", file=self.os_file_handle)
        
        print(file=self.os_file_handle)

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
        self.include_specs.append(IncludeSpec(use_angle_brackets=True, include_path="cstdint"))
        self.include_specs.append(IncludeSpec(use_angle_brackets=True, include_path="string"))
        self.include_specs.append(IncludeSpec(use_angle_brackets=True, include_path="functional"))
        
    def inc_indent(self):
        self.indent_count += 1
    
    def dec_indent(self):
        self.indent_count -= 1


class Block(object):
    def __init__(
        self, 
        cpp_file: "CppFileWriter", 
        prefix: str = "", 
        suffix: str = "", 
        opening_brace: str = "{",
        closing_brace: str = "}",
        close_with_semicolon: bool = False
) -> None:
        super().__init__()
        self.cpp_file: "CppFileWriter" = cpp_file
        self.prefix: str = prefix
        self.suffix: str = suffix
        self.opening_brace = opening_brace
        self.closing_brace = closing_brace
        self.close_with_semicolon = close_with_semicolon

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
        if self.close_with_semicolon:
            self.cpp_file.print(f"{self.closing_brace};")
        else:
            self.cpp_file.print(self.closing_brace)
        if self.suffix:
            self.cpp_file.print(self.suffix)


#
# Helpers
#

def normalize_backslash_path(raw_path):
    clean_path = os.path.normpath(raw_path)
    if os.sep == '/':
        return clean_path
    else:
        return clean_path.replace(os.sep, '/') 


# Ooh; is this file-level hiding in Python?		
# __all__ = ["CppFile", "CodeFile"]
