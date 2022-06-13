import abc
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
from . import interp
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
        self.impl_abs_output_dir_path = os.path.join(self.root_abs_output_dir_path, "impl")
        self.pub_type_to_header_name_map = {}
        
        # v-- used by 'check_global_definition'
        self.global_symbol_loc_map = {}

        # v-- used by emit_statement
        self.active_c_file = None
        self.active_h_file = None
    
        # v-- used by emit_exp
        self.tmp_var_id_counter = 0
        self.cached_builtin_string_type = None

    def emit_qyp_set(self, qyp_set: ast2.QypSet):
        # caching builtin bindings from Qyp context:
        builtin_string_type_def = qyp_set.wb_root_ctx.try_lookup("String")
        assert isinstance(builtin_string_type_def, typer.TypeDefinition)
        self.cached_builtin_string_type = builtin_string_type_def.scheme.instantiate_monomorphically()

        # cleaning old directories:
        # on macOS, Windows, with case-insensitive paths, renaming symbols with different case 
        # results in stale files being used instead.
        if os.path.isdir(self.root_abs_output_dir_path):
            shutil.rmtree(self.root_abs_output_dir_path)

        # creating fresh directories:
        os.makedirs(self.root_abs_output_dir_path, exist_ok=False)
        os.makedirs(self.types_abs_output_dir_path, exist_ok=False)
        os.makedirs(self.impl_abs_output_dir_path, exist_ok=False)

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

        # emitting the 'impl' subdirectory of build:
        for qyp_name, qyp in qyp_set.qyp_name_map.items():
            if isinstance(qyp, ast2.NativeQyp):
                self.emit_native_qyp_impl(qyp_name, qyp, extern_header_source_files)
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
            type_decl_file = CppFileWriter(DocType.TypeDeclHeader, type_files_stem)
            type_def_file = CppFileWriter(DocType.TypeDefHeader, type_files_stem)
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
            else:
                # NOTE: forcing 'anonymous' representation to avoid just using the name
                # we are trying to define.
                rhs_t = self.translate_type(qy_type, anonymous_form=True)
                type_decl_file.print(f"using {type_name} = {rhs_t};")
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
                type_def_file.print(f"using {type_name} = {self.translate_type(qy_type)};")

    def insert_type_ref_includes(self, print_file: "CppFileWriter", qy_type: types.BaseType, direct_ref: bool):
        # NOTE: every compound just includes dependencies required to write the type.
        
        # first, checking if this type has a name: just include it directly.
        opt_existing_name = self.pub_type_to_header_name_map.get(qy_type, None)
        if opt_existing_name:
            if direct_ref:
                extension = CppFileWriter.doc_file_path_suffix[DocType.TypeDefHeader]
            else:
                extension = CppFileWriter.doc_file_path_suffix[DocType.TypeDeclHeader]
            print_file.include_specs.append(IncludeSpec(use_angle_brackets=False, include_path=f"{opt_existing_name}.{extension}"))

        # otherwise, this is an anonymous type.
        # we must include all types used to write this type.
        # WARNING: this output depends heavily on 'translate_type'-- it could be merged.
        if qy_type.is_atomic:
            # do nothing-- all atomic types are built-in.
            pass
        elif qy_type.is_composite:
            if isinstance(qy_type, types.PointerType):
                self.insert_type_ref_includes(print_file, qy_type.pointee_type, direct_ref=False)
            else:
                for field_type in qy_type.field_types:
                    self.insert_type_ref_includes(print_file, field_type, direct_ref=direct_ref)

    def check_global_definition(self, name: str, loc: feedback.ILoc, is_public: bool):
        opt_existing_loc = self.global_symbol_loc_map.get(name, None)
        if opt_existing_loc is not None:
            if opt_existing_loc != loc:
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
            else:
                self.global_symbol_loc_map[name] = loc

    #
    # part 2: emitting module body
    #

    def emit_native_qyp_impl(self, qyp_name: str, qyp: ast2.NativeQyp, extern_header_source_files: t.List[ast2.BaseSourceFile]):
        # creating output files, adding external project headers to all includes:
        output_file_stem = os.path.join(self.impl_abs_output_dir_path, qyp_name)
        self.active_h_file = CppFileWriter(DocType.MainHeader, output_file_stem)
        self.active_c_file = CppFileWriter(DocType.MainSource, output_file_stem)

        for source_file in extern_header_source_files:
            abs_extern_header_path = source_file.file_path
            self.active_h_file.include_specs.append(IncludeSpec(abs_extern_header_path, use_angle_brackets=False, extern_str=source_file.extern_str))
            self.active_h_file.include_specs.append(IncludeSpec(abs_extern_header_path, use_angle_brackets=False, extern_str=source_file.extern_str))
        
        print(f"INFO: Generating C/C++ file pair:\n\t{self.active_c_file.path}\n\t{self.active_h_file.path}")
        
        for src_file_path, src_obj in qyp.src_map.items():
            assert isinstance(src_obj, ast2.QySourceFile)
            for stmt in src_obj.stmt_list:
                self.emit_statement_impl(self.active_c_file, stmt, is_top_level=True, decl_print_pass=True)
                self.emit_statement_impl(self.active_h_file, stmt, is_top_level=True, decl_print_pass=True)
                self.emit_statement_impl(self.active_c_file, stmt, is_top_level=True, decl_print_pass=False)
                self.emit_statement_impl(self.active_h_file, stmt, is_top_level=True, decl_print_pass=False)

        self.active_c_file.close()
        self.active_h_file.close()
        self.active_c_file = None
        self.active_h_file = None

    def emit_statement_impl(self, s, stmt: ast1.BaseStatement, is_top_level: bool, decl_print_pass: bool = False):
        self.translate_statement_impl(s, stmt, is_top_level, decl_print_pass)
        
    def translate_statement_impl(self, s: "StringWriter", stmt: ast1.BaseStatement, is_top_level: bool, decl_print_pass: bool):
        target = s.doc_type
        assert target in (DocType.MainSource, DocType.MainHeader, DocType.ChainFragment)
        
        if isinstance(stmt, ast1.Bind1vStatement) and target in (DocType.MainSource, DocType.ChainFragment) and not decl_print_pass:
            def_obj = stmt.lookup_def_obj()
            if stmt.wb_ctx.kind == typer.ContextKind.TopLevelOfQypSet:
                self.check_global_definition(stmt.name, stmt.loc, def_obj.is_public)

            assert isinstance(def_obj, typer.BaseDefinition)
            assert not def_obj.scheme.vars
            _, def_type = def_obj.scheme.instantiate()
        
            s.print(f"// bind {stmt.name} = {stmt.initializer.desc}")
            if def_type is types.VoidType.singleton:
                s.print("// binding elided for 'void' type variable.")
            else:
                bind_cpp_fragments = []
                # if not def_obj.is_public:
                #     bind_cpp_fragments.append('static')
                if def_obj.is_compile_time_constant:
                    bind_cpp_fragments.append('constexpr')
                bind_cpp_fragments.append(self.translate_type(def_type))
                bind_cpp_fragments.append(def_obj.name)
                bind_cpp_fragments.append("=")
            
                s.print(' '.join(bind_cpp_fragments))
            
            # regardless of return-type, evaluating the RHS in case there are any side-effects:
            with Block(s, opening_brace='(', closing_brace=")", close_with_semicolon=True):
                self.emit_expression(s, stmt.initializer)
            s.print()
        
        elif isinstance(stmt, ast1.DiscardStatement) and target in (DocType.MainSource, DocType.ChainFragment) and not decl_print_pass:
            with Block(s, opening_brace='(', closing_brace=")", close_with_semicolon=True):
                self.emit_expression(s, stmt.discarded_exp)
            s.print()
        
        elif isinstance(stmt, ast1.Bind1fStatement) and target == DocType.MainSource and not decl_print_pass:
            assert is_top_level

            def_obj = stmt.lookup_def_obj()
            if stmt.wb_ctx.kind == typer.ContextKind.TopLevelOfQypSet:
                self.check_global_definition(stmt.name, stmt.loc, def_obj.is_public)
        
            assert isinstance(def_obj, typer.BaseDefinition)
            assert not def_obj.scheme.vars
            _, def_type = def_obj.scheme.instantiate()
            assert isinstance(def_type, types.ProcedureType)
            
            s.print(f"// bind {stmt.name} = {{...}}")
            # if not def_obj.is_public and stmt.name != 'main':
            #     s.print('static')
            s.print(self.translate_type(def_type.ret_type))
            if not stmt.args_names:
                s.print(f"{def_obj.name}()")
            else:
                s.print(def_obj.name)
                with Block(s, opening_brace='(', closing_brace=')'):
                    s.print(',\n'.join((
                        f"{self.translate_type(arg_type)} {arg_name}"
                        for arg_type, arg_name in zip(def_type.arg_types, stmt.args_names)
                    )))
            with Block(s):
                s.print("return")
                with Block(s, opening_brace='(', closing_brace=');'):
                    self.emit_expression(s, stmt.body_exp)
            s.print()
        
        elif isinstance(stmt, ast1.Bind1tStatement) and not decl_print_pass:    # branch based on target below...
            assert is_top_level
            
            s.print(f"// bind {stmt.name} = {{...}}")

            # pulling up this definition's info:
            def_obj = stmt.lookup_def_obj()
            if stmt.wb_ctx.kind == typer.ContextKind.TopLevelOfQypSet:
                self.check_global_definition(stmt.name, stmt.loc, def_obj.is_public)
            assert def_obj is not None
            assert not def_obj.scheme.vars
            _, def_type = def_obj.scheme.instantiate()
            
            # public type => it has its own header pair => include this in the main header here
            if target == DocType.MainHeader and def_type in self.pub_type_to_header_name_map:
                type_def_extension = CppFileWriter.doc_file_path_suffix[DocType.TypeDefHeader]
                s.include_specs.append(IncludeSpec(use_angle_brackets=False, include_path=f"types/{stmt.name}.{type_def_extension}"))
            
            # private type => define in 'c' file
            if target in (DocType.MainSource, DocType.ChainFragment):
                assert isinstance(def_type, types.BaseType)
                s.print(f"using {stmt.name} = {self.translate_type(def_type)};")
            
            s.print()

        elif isinstance(stmt, ast1.Type1vStatement) and target in (DocType.MainHeader, DocType.MainSource) and decl_print_pass:
            def_obj = stmt.lookup_def_obj()
            write_pub = def_obj.is_public and target == DocType.MainHeader
            write_pvt = not def_obj.is_public and target == DocType.MainSource
            if write_pub or write_pvt:
                qy_visibility_prefix, decl_prefix = ("pub ", "extern ") if def_obj.is_public else ("pvt ", "")
                _, def_type = def_obj.scheme.instantiate()
                s.print(f"// {qy_visibility_prefix}{stmt.name}")
                if isinstance(def_type, types.ProcedureType) and not def_type.has_closure_slot:
                    if is_top_level:
                        args_list = ', '.join(map(self.translate_type, def_type.arg_types))
                        s.print(f"{decl_prefix}{self.translate_type(def_type.ret_type)} {stmt.name}({args_list});")
                    else:
                        raise NotImplementedError("Cannot type a function in a non-global context")
                else:
                    s.print(f"{decl_prefix}{self.translate_type(def_type)} {stmt.name};", target_section=DocumentSectionId.Prefix)
                s.print()

        elif isinstance(stmt, ast1.ConstStatement) and target in (DocType.MainSource, DocType.ChainFragment) and not decl_print_pass:
            for stmt in stmt.body:
                self.emit_statement_impl(s, stmt, is_top_level=is_top_level)
            
        elif isinstance(stmt, ast1.ReturnStatement) and target in (DocType.MainSource, DocType.ChainFragment) and not decl_print_pass:
            s.print(f"return {self.translate_expression(stmt.returned_exp)};")

        elif isinstance(stmt, ast1.LoopStatement) and target in (DocType.MainSource, DocType.ChainFragment) and not decl_print_pass:
            s.print("for (;;)")
            
            with Block(s):
                if stmt.loop_style == ast1.LoopStyle.WhileDo:
                    cond_str = self.translate_expression(stmt.cond)
                    s.print("// `while (cond) do ...` termination check:")
                    s.print(f"if (!{cond_str}) {{ break; }}")

                self.emit_block(s, stmt.body)

                if stmt.loop_style == ast1.LoopStyle.DoWhile:
                    cond_str = self.translate_expression(stmt.cond)
                    s.print("// `do ... while (cond)` termination check:")
                    s.print(f"if (!{cond_str}) {{ break; }}")

        else:
            pass

    def emit_expression(self, f: "StringWriter", exp: ast1.BaseExpression):
        f.print(self.translate_expression(exp))

    def emit_block(self, s: "StringWriter", block: t.List[ast1.BaseStatement]):
        for stmt in block:
            self.emit_statement_impl(s, stmt, is_top_level=False)

    def translate_type(self, qy_type: types.BaseType, anonymous_form=False) -> str:
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

        if not anonymous_form:
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
        elif isinstance(qy_type, types.BaseCompositeType):
            if isinstance(qy_type, (types.StructType, types.UnionType)):
                if qy_type.opt_name is not None:
                    assert isinstance(qy_type.opt_name, str)
                    return qy_type.opt_name

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
                ret_type = self.translate_type(qy_type.ret_type)
                cs_arg_str = ', '.join(map(self.translate_type, qy_type.arg_types))
                if qy_type.has_closure_slot:
                    assert isinstance(qy_type, types.ProcedureType)
                    if qy_type.has_closure_slot:
                        return f"std::function<{ret_type}({cs_arg_str})>"
                    else:
                        return f"{ret_type}(*)({cs_arg_str})"
                else:
                    return f"{self.translate_type(ret_type)}(*)({cs_arg_str})"
            elif isinstance(qy_type, types.PointerType):
                return f"{self.translate_type(qy_type.pointee_type)}*"
            elif isinstance(qy_type, types.ArrayType):
                return f"std::array< {self.translate_type(qy_type.element_type)}, {qy_type.count} >"
            elif isinstance(qy_type, types.ArrayBoxType):
                # FIXME: ArrayBox should be immutable in size?
                # Maybe 'ArrayBox' should map to 'std::vector'
                # And 'Vector' should map to 'struct<T> { size_t len; T* data; }
                return f"std::vector< {self.translate_type(qy_type.element_type)} >"
            else:
                raise NotImplementedError(f"Unknown compound type in 'translate_type': {qy_type}")
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
            def_obj = exp.lookup_def_obj()
            assert isinstance(def_obj, typer.BaseDefinition)
            s, def_type = def_obj.scheme.instantiate()
            assert s is typer.Substitution.empty
            
            if exp.name.endswith('!'):
                if exp.name == "pred!":
                    res = interp.evaluate_constant(def_obj.binder.initializer)
                    if res is None:
                        panic.because(
                            panic.ExitCode.CompileTimeEvaluationError,
                            "Tried to evaluate 'pred!', but failed: this is most likely caused by a prior error.",
                            opt_loc=exp.loc
                        )
                    return repr(res), def_type
                else:
                    raise NotImplementedError(f"Unknown builtin macro: {exp.name}")
            else:
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
            c_string_literal = json.dumps(exp.value)
            c_string_length = len(exp.value.encode("utf-8"))
            output_constructor = f"new_permanent_literal_string({c_string_literal}, {int(c_string_length)})"
            return output_constructor, self.cached_builtin_string_type

        elif isinstance(exp, ast1.UnaryOpExpression):
            operand_str, operand_type = self.translate_expression_with_type(exp.operand)

            if exp.operator == ast1.UnaryOperator.Do:
                assert isinstance(operand_type, types.ProcedureType)
                assert operand_type.arg_count == 0
                return f"{operand_str}()", operand_type.ret_type
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
                ast1.BinaryOperator.RSh: ">>",
                ast1.BinaryOperator.LThan: "<",
                ast1.BinaryOperator.GThan: ">",
                ast1.BinaryOperator.LEq: "<=",
                ast1.BinaryOperator.GEq: ">=",
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
            container_str, raw_container_type = self.translate_expression_with_type(exp.container)
            
            if isinstance(raw_container_type, types.BaseAlgebraicType):
                container_type = raw_container_type
            elif isinstance(raw_container_type, types.PointerType) and isinstance(raw_container_type.pointee_type, types.BaseAlgebraicType):
                container_type = raw_container_type.pointee_type
                container_str = f"(*{container_str})"
            else:
                raise NotImplementedError(f"Unknown container type when emitting DotIdExpression C++ code: {raw_container_type}")

            ret_str = f"{container_str}.{exp.key}"
            ret_type = None
            for field_name, field_type in container_type.fields:
                if field_name == exp.key:
                    ret_type = field_type
                    break
            else:
                raise RuntimeError("Expected field checks to resolve in typer, but could not lookup field in emitter.")
        
            assert ret_type is not None
            return ret_str, ret_type

        elif isinstance(exp, ast1.ConstructExpression):
            if exp.wb_type.is_atomic and len(exp.initializer_list) == 1:
                # 'cast' expressions
                target_type_str = self.translate_type(exp.wb_type)
                arg_str = self.translate_expression(exp.initializer_list[0])
                return f"static_cast<{target_type_str}>({arg_str})", exp.wb_type
            else:
                # constructor invocation
                res_type = exp.wb_type
                initializer_exp_strs = [self.translate_expression(exp) for exp in exp.initializer_list]
                initializer_list_str = ','.join(initializer_exp_strs)
                
                def make_constructor_str(made_type):
                    made_ts_str = self.translate_type(made_type)
                    use_initializer_list = not isinstance(res_type, types.ArrayBoxType)
                    return made_ts_str, (
                        f"{made_ts_str}{{{initializer_list_str}}}"
                        if use_initializer_list else
                        f"{made_ts_str}({initializer_list_str})"
                    )

                _, constructor_str = make_constructor_str(res_type)
                return constructor_str, exp.made_ts.wb_type

        elif isinstance(exp, ast1.CopyExpression):
            res_type = exp.wb_type
            assert isinstance(res_type, types.PointerType)
            
            copied_type = res_type.pointee_type
            copied_type_str = self.translate_type(copied_type)
            ptr_type_str = self.translate_type(res_type)

            if exp.allocator == ast1.CopyExpression.Allocator.Push:
                address_str = f"alloca(sizeof({copied_type_str}))"
            else:
                assert exp.allocator == ast1.CopyExpression.Allocator.Heap
                address_str = f"malloc(sizeof({copied_type_str}))"
            
            copied_val_str = self.translate_expression(exp.copied_val)

            constructor_str = (
                f"([] ({ptr_type_str} p, {copied_type_str} v) -> {ptr_type_str} " "{ "
                    f"*p = v; "
                    f"return p; "
                "} " f"(({ptr_type_str})({address_str}), {copied_val_str}))"
            )
            return constructor_str, res_type
    
        elif isinstance(exp, ast1.IfExpression):
            # NOTE: If expressions are regular functions in this language, and must invoke their 'then' or 'else' branches 
            # based on the result of 'cond'.

            cond_str = self.translate_expression(exp.cond_exp)
            then_str = f"(({self.translate_expression(exp.then_exp)})())"
            if exp.else_exp is not None:
                else_str = f"(({self.translate_expression(exp.else_exp)})())"
            else:
                then_str = f"(({then_str}), 0)"
                else_str = "0"
            ite_str = f"({cond_str} ? ({then_str}) : ({else_str}))"
            return ite_str, exp.wb_type

        elif isinstance(exp, ast1.LambdaExpression):
            # TODO: review if '&' is a viable strategy to clone: would be safe, but costly: prefer '&', but then need to solve closure lifetimes...
            # FIXME: issue with LambdaExpression's wb_type: see 'if exp.opt_body_tail is not None' guard

            s = StringWriter()
            with Block(s, opening_brace='(', closing_brace=')'):
                s.print('[=]' if exp.no_closure else '[]')
                
                p_type = exp.wb_type
                assert isinstance(p_type, types.ProcedureType)
                arg_types = p_type.arg_types
                ret_type = p_type.ret_type
                if exp.arg_names:
                    with Block(s, opening_brace='(', closing_brace=')'):
                        s.print(", ".join(f"{self.translate_type(arg_type)} {arg_name}" for arg_name, arg_type in zip(exp.arg_names, arg_types)))
                else:
                    s.print('()')
                ret_str = self.translate_type(p_type.ret_type) if exp.opt_body_tail is not None else "void"
                s.print(f"-> {ret_str} ")

                with Block(s, opening_brace='{', closing_brace='}'):
                    self.emit_block(s, exp.body_prefix)
                    if exp.opt_body_tail is not None:
                        s.print(f"return {self.translate_expression(exp.opt_body_tail)};")
                    else:
                        s.print("return;")
            
            return s.close(), p_type

        elif isinstance(exp, ast1.UpdateExpression):
            store_address_str = self.translate_expression(exp.store_address)
            stored_value_str = self.translate_expression(exp.stored_value)
            
            lvalue_str = f"*{store_address_str}"
            rvalue_str = stored_value_str
            res_str = lvalue_str + " = " + rvalue_str

            return res_str, exp.wb_type

        elif isinstance(exp, ast1.IndexExpression):
            container_str = self.translate_expression(exp.container)
            final_prefix = "&" if exp.ret_ref else ""

            res_str = f"({final_prefix}{container_str}[{self.translate_expression(exp.index)}])"

            return res_str, exp.wb_type

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
            cml_print(f"set(CMAKE_C_STANDARD 11)")
            cml_print()
            cml_print(f"if (NOT MSVC)")
            cml_print(f"    set(CMAKE_CXX_FLAGS -Wno-parentheses-equality)")
            cml_print(f"endif()")
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

                    native_source_file_paths.append(f"impl/{qyp_name}.{CppFileWriter.doc_file_path_suffix[DocType.MainHeader]}")
                    native_source_file_paths.append(f"impl/{qyp_name}.{CppFileWriter.doc_file_path_suffix[DocType.MainSource]}")

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


class DocType(enum.Enum):
    MainSource = enum.auto()
    MainHeader = enum.auto()
    TypeDefHeader = enum.auto()
    TypeDeclHeader = enum.auto()
    ChainFragment = enum.auto()


class DocumentSectionId(enum.Enum):
    Prefix = enum.auto()
    Body = enum.auto()


class StringWriter(object):
    def __init__(self, document_type=DocType.ChainFragment, indent_str='\t') -> None:
        super().__init__()
        self.private_doc_type = document_type
        self.indent_count = 0
        self.indent_str = indent_str
        self.include_specs: t.List[IncludeSpec] = []
        self.document_sections = {DocumentSectionId.Prefix: [], DocumentSectionId.Body: []}
        
    @property
    def file_name(self):
        return os.path.basename(self.path)

    @property
    def doc_type(self):
        return self.private_doc_type
    
    def close(self) -> str:
        # first assembling a list of string chunks, then printing:
        chunks = []

        # prefix:
        prefix_lines = self.document_sections[DocumentSectionId.Prefix]
        chunks.append('\n'.join(prefix_lines))

        # sorting includes, then 'printing' to chunk list in order:
        cpp_include_specs = [include_spec for include_spec in self.include_specs if include_spec.extern_str is None]
        c_include_specs = [include_spec for include_spec in self.include_specs if include_spec.extern_str == "C"]
        assert len(cpp_include_specs) + len(c_include_specs) == len(self.include_specs)
        abs_cpp_include_specs = [it.include_path for it in cpp_include_specs if it.use_angle_brackets]
        rel_cpp_include_specs = [it.include_path for it in cpp_include_specs if not it.use_angle_brackets]
        abs_extern_c_include_specs = [it.include_path for it in c_include_specs if it.use_angle_brackets]
        rel_extern_c_include_specs = [it.include_path for it in c_include_specs if not it.use_angle_brackets]
        if abs_cpp_include_specs:
            chunks.append(self.print_includes(abs_cpp_include_specs, True))
        if rel_cpp_include_specs:
            chunks.append(self.print_includes(rel_cpp_include_specs, False))
        if abs_extern_c_include_specs:
            chunks.append(self.print_includes(abs_extern_c_include_specs, True, "C"))
        if rel_extern_c_include_specs:
            chunks.append(self.print_includes(rel_extern_c_include_specs, False, "C"))

        # body lines:
        chunks.append('\n'.join(self.document_sections[DocumentSectionId.Body]))

        # returning chunk text:
        text = '\n'.join(chunks) + '\n'
        
        assert isinstance(text, str)
        return text
        
    def print(self, code_fragment: CodeFragment = "", target_section=DocumentSectionId.Body):
        if isinstance(code_fragment, str):
            lines = code_fragment.split('\n')
        elif isinstance(code_fragment, list):
            if __debug__:
                for line in code_fragment:
                    assert '\n' not in line
            lines = code_fragment
        else:
            raise ValueError(f"Invalid CodeFragment: {code_fragment}")
        
        target_lines_list = self.document_sections[target_section]
        for line in lines:
            target_lines_list.append(f"{self.indent_str*self.indent_count}{line}")

    def print_includes(self, include_specs, use_angle_brackets, opt_extern_str=None):
        open_quote, close_quote = ('<', '>') if use_angle_brackets else ('"', '"')
        
        output = []

        if opt_extern_str:
            indent_str = '\t'
            output.append(f"extern \"{opt_extern_str}\" {{")
        else:
            indent_str = ''

        for include_path in include_specs:
            sep_normalized_include_path = normalize_backslash_path(include_path)
            clean_include_path = sep_normalized_include_path
            output.append(f"{indent_str}#include {open_quote}{clean_include_path}{close_quote}")
        
        if opt_extern_str:
            output.append(f"}}")
        
        output.append('')
        return '\n'.join(output)

    def add_common_stdlib_header_includes(self):
        # C/C++ stdlib:
        self.include_specs.append(IncludeSpec(use_angle_brackets=True, include_path="functional"))
        self.include_specs.append(IncludeSpec(use_angle_brackets=True, include_path="array"))
        self.include_specs.append(IncludeSpec(use_angle_brackets=True, include_path="cstdint"))
        self.include_specs.append(IncludeSpec(use_angle_brackets=True, include_path="cstdlib"))

    def inject_manual_main_preamble(self):
        # FIXME: allow cross-compilation via args, not current platform
        if os.name == 'nt':
            self.print("#define alloca _alloca", target_section=DocumentSectionId.Prefix)

    def inc_indent(self):
        self.indent_count += 1
    
    def dec_indent(self):
        self.indent_count -= 1


class CppFileWriter(StringWriter):
    doc_file_path_suffix = {
        DocType.MainHeader: "hpp",
        DocType.MainSource: "cpp",
        DocType.TypeDefHeader: "def.hpp",
        DocType.TypeDeclHeader: "decl.hpp"
    }

    def __init__(self, doc_type: DocType, file_stem: str, indent_str='\t') -> None:
        super().__init__(doc_type, indent_str=indent_str)
        assert doc_type in CppFileWriter.doc_file_path_suffix
        self.stem = file_stem
        self.stem_base = os.path.basename(self.stem)
        self.path = f"{self.stem}.{CppFileWriter.doc_file_path_suffix[self.doc_type]}"
        self.file_stem = file_stem

        #
        # Post-constructor, but constructor-time:
        #

        # emitting preamble:
        if self.doc_type == DocType.MainHeader:
            self.print("#pragma once", target_section=DocumentSectionId.Prefix)
            self.print(target_section=DocumentSectionId.Prefix)
            self.add_common_stdlib_header_includes()
        elif self.doc_type == DocType.MainSource:
            # including the header file, as is customary for implementation files:
            include_spec = IncludeSpec(use_angle_brackets=False, include_path=self.stem_base+"."+CppFileWriter.doc_file_path_suffix[DocType.MainHeader])
            self.include_specs.append(include_spec)
            self.add_common_stdlib_header_includes()
            # writing some text
            self.inject_manual_main_preamble()
        elif self.doc_type == DocType.TypeDeclHeader:
            self.print("#pragma once", target_section=DocumentSectionId.Prefix)
            self.print(target_section=DocumentSectionId.Prefix)
            self.add_common_stdlib_header_includes()
        elif self.doc_type == DocType.TypeDefHeader:
            self.print("#pragma once", target_section=DocumentSectionId.Prefix)
            self.print(target_section=DocumentSectionId.Prefix)
        
    def close(self) -> str:
        chunk_text = super().close()

        # printing to the file in a single system call:
        with open(self.path, 'w', buffering=len(chunk_text)) as os_file_handle:
            print(chunk_text, file=os_file_handle, end='')

        return chunk_text



class Block(object):
    def __init__(
        self, 
        sw: "StringWriter", 
        prefix: str = "", 
        suffix: str = "", 
        opening_brace: str = "{",
        closing_brace: str = "}",
        close_with_semicolon: bool = False
) -> None:
        super().__init__()
        self.sw: "StringWriter" = sw
        self.prefix: str = prefix
        self.suffix: str = suffix
        self.opening_brace = opening_brace
        self.closing_brace = closing_brace
        self.close_with_semicolon = close_with_semicolon

    def type(self):
        return self.printer.type

    def __enter__(self):
        if self.prefix:
            self.sw.print(self.prefix)
        self.sw.print(self.opening_brace)
        self.sw.inc_indent()
        return self

    def __exit__(self, *_):
        self.sw.dec_indent()
        if self.close_with_semicolon:
            self.sw.print(f"{self.closing_brace};")
        else:
            self.sw.print(self.closing_brace)
        if self.suffix:
            self.sw.print(self.suffix)


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
