# TODO:
#   - read https://libclang.readthedocs.io/en/latest/_modules/clang/cindex.html
#   - read https://github.com/llvm-mirror/clang/blob/master/bindings/python/examples/cindex/cindex-dump.py
#   - GOALS:
#       1.  translate select global definitions (with their types) from C to Qy
#       2.  link existing C code with final output
#   - load each header, and expose defined symbols in Qy space
#       - these synthetic Qy definitions are used to type-check.
#       - easiest option (and hence chosen one): generate a Qy AST
#           - ~~ignore forward declarations~~
#       - model opaque structs and enums: it's pretty straightforward
#   - ~~load each source, and only translate type definitions to Qy space~~
#       - thus, ignore function definitions since they are compiled and linked by the backend
#       - use type definitions to expose even forward-declared types
#       - NOTE: clang.cindex only loads files in a platform-dependent way
#   - when emitting,
#       - ensure each used header is included by C++ in an 'extern' block
#       - ensure each of 'sources' are forwarded to final compiler

# misc useful:
#   - node.type.get_canonical()
#   - node.type.get_pointee()

import typing as t
import itertools

import clang.cindex

from . import ast1
from . import panic
from . import feedback
from . import types

index = clang.cindex.Index.create()
CursorKind = clang.cindex.CursorKind
TypeKind = clang.cindex.TypeKind


def parse_one_file(source_file_path, all_provided_symbols: t.Set[str], is_header: bool) -> t.Tuple[t.List[ast1.BaseStatement], t.Set[str]]:
    print(f"\t{source_file_path}")
    
    tu = index.parse(
        source_file_path,
        # options=clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
    )
    # dbg_print_visit(tu, tu.cursor)

    # making a copy of 'provided_symbols', then popping as symbols are discovered:
    rem_provided_symbols = set(all_provided_symbols)
    if rem_provided_symbols:
        stmt_list = translate_tu(tu, rem_provided_symbols)
    else:
        stmt_list = []

    # finding which symbols were discovered:
    exposed_symbols = all_provided_symbols - rem_provided_symbols
    return stmt_list, exposed_symbols


def translate_tu(tu, rem_provided_symbols) -> t.List[ast1.BaseStatement]:
    iter_list = []
    for child_node in tu.cursor.get_children():
        iter_list += list(translate_tu_top_level_stmt(tu, child_node, rem_provided_symbols))
    return list(itertools.chain(iter_list))


def translate_tu_top_level_stmt(tu, node, rem_provided_symbols) -> t.Iterable[ast1.BaseStatement]:
    CursorKind = clang.cindex.CursorKind

    if node.kind == CursorKind.INCLUSION_DIRECTIVE:
        yield from translate_inclusion_directive(tu, node, rem_provided_symbols)
    elif node.kind == CursorKind.MACRO_DEFINITION:
        yield from translate_macro_definition(tu, node, rem_provided_symbols)

    elif node.kind in (CursorKind.STRUCT_DECL, CursorKind.UNION_DECL):
        yield from translate_adt_decl(tu, node, rem_provided_symbols)
    elif node.kind == CursorKind.ENUM_DECL:
        yield from translate_enum_decl(tu, node, rem_provided_symbols)
    elif node.kind == CursorKind.FUNCTION_DECL:
        yield from translate_function_decl(tu, node, rem_provided_symbols)
    elif node.kind == CursorKind.VAR_DECL:
        yield from translate_variable_decl(tu, node, rem_provided_symbols)
    elif node.kind == CursorKind.TYPEDEF_DECL:
        yield from translate_typedef_decl(tu, node, rem_provided_symbols)

    elif node.kind in (CursorKind.STATIC_ASSERT,):
        # do nothing
        yield from iter(())

    else:
        # ignore this statement
        raise NotImplementedError(f"Compiler error: unknown statement in extern C code: {node.kind}")


def translate_inclusion_directive(tu, node, rem_provided_symbols):
    # TODO: recursively search for more symbols in the mentioned TU
    return iter(())


def translate_macro_definition(tu, node, rem_provided_symbols):
    tokens = list(clang.cindex.TokenGroup.get_tokens(tu, node.extent))
    macro_name = tokens[0].spelling
    if macro_name in rem_provided_symbols:
        panic.because(
            panic.ExitCode.UnsupportedExternCFeature,
            "C macros cannot be exported (please re-bind as an inline function, constant, or type if possible)",
            opt_loc=loc(node)
        )
    return iter(())


def translate_adt_decl(tu, node, rem_provided_symbols):
    assert node.kind in (CursorKind.UNION_DECL, CursorKind.STRUCT_DECL)
    adt_name = node.spelling
    if adt_name in rem_provided_symbols:
        rem_provided_symbols.remove(adt_name)
        adt_ts = translate_clang_type_to_ts(node.type, is_direct_use=False)
        assert adt_ts.wb_type is not None
        yield ast1.Bind1tStatement(loc(node), adt_name, adt_ts)


def translate_enum_decl(tu, node, rem_provided_symbols):
    enum_name = node.spelling
    if enum_name in rem_provided_symbols:
        rem_provided_symbols.remove(enum_name)
        const_ts = translate_clang_type_to_ts(node.enum_type)
        body = []
        for entry in node.get_children():
            assert entry.kind == CursorKind.ENUM_CONSTANT_DECL
            enum_entry_value = entry.enum_value
            init_exp = ast1.IntExpression(
                loc(entry),
                str(enum_entry_value),
                enum_entry_value,
                10,
                is_unsigned=const_ts.is_unsigned_int,
                width_in_bits=const_ts.int_width_in_bits
            )
            bind1v_stmt = ast1.Bind1vStatement(loc(entry), entry.spelling, init_exp, is_constant=True)
            body.append(bind1v_stmt)
        yield ast1.ConstStatement(loc(node), body, const_ts)


def translate_adt_field_decl_to_ts(tu, node, rem_provided_symbols):
    assert node.kind == CursorKind.FIELD_DECL
    return translate_clang_type_to_ts(node.type)


def translate_function_decl(tu, node, rem_provided_symbols):
    func_name = node.spelling
    if func_name in rem_provided_symbols:
        rem_provided_symbols.remove(func_name)
        clang_func_ret_type = node.type.get_result()
        arg_names = [arg_node.spelling for arg_node in node.get_arguments()]
        arg_typespecs = [
            translate_clang_type_to_ts(clang_arg_type, False) 
            for clang_arg_type in node.type.argument_types()
        ]
        ret_ts = translate_clang_type_to_ts(node.type.get_result())
        fn_str = (
            clang_func_ret_type.spelling + " " + 
            node.spelling + 
            "(" + ', '.join((t.spelling for t in node.type.argument_types())) + ")"
        )
        yield ast1.Extern1fStatement(loc(node), func_name, arg_names, arg_typespecs, ret_ts, fn_str)
        
    # exit()


def translate_variable_decl(tu, node, rem_provided_symbols):
    var_name = node.spelling
    if var_name in rem_provided_symbols:
        rem_provided_symbols.remove(var_name)
        var_ts = translate_clang_type_to_ts(node.type, True)
        var_str = node.type.spelling + " " + node.spelling
        # is_mut = var_ts.wb_type.is_mut
        yield ast1.Extern1vStatement(loc(node), var_name, var_ts, var_str)


def translate_typedef_decl(tu, node, rem_provided_symbols):
    type_name = node.spelling
    if type_name in rem_provided_symbols:
        rem_provided_symbols.remove(type_name)
        stmt = ast1.Bind1tStatement(loc(node), type_name, translate_clang_type_to_ts(node.type, False))
        yield stmt


def loc(node):
    return feedback.FileLoc(node.translation_unit.spelling, feedback.FilePos(node.location.line-1, node.location.column-1))


def c_type_loc(c_type):
    return loc(c_type.get_declaration())

    
def dbg_print_visit(tu, node, indent_count=1, tab_w=2):
    dash_str = '-'.ljust(tab_w, ' ')
    spacer_str = ' ' * tab_w * indent_count
    indent_str = ' ' * tab_w * (indent_count-1) + dash_str

    tags = []
    if node.kind.is_reference():
        tags.append("is_reference")
    if node.kind.is_declaration():
        tags.append("is_declaration")
        if node.kind == CursorKind.FUNCTION_DECL:
            tags.append("fn_decl")
        elif node.kind == CursorKind.STRUCT_DECL:
            tags.append("struct_decl")
        elif node.kind == CursorKind.ENUM_DECL:
            tags.append("enum_decl")
        elif node.kind == CursorKind.VAR_DECL:
            tags.append("var_decl")
        else:
            # raise NotImplementedError(f"CQyx: Unknown declaration: {node.kind}")
            pass
    if node.kind.is_expression():
        tags.append("is_expression")
    if node.kind.is_statement():
        tags.append("is_statement")
    if node.kind.is_attribute():
        tags.append("is_attribute")
    if node.kind.is_invalid():
        tags.append("is_invalid")
    if node.kind.is_translation_unit():
        tags.append("is_translation_unit")
    if node.kind.is_preprocessing():
        tags.append("is_preprocessing")
    if node.kind.is_unexposed():
        tags.append("is_unexposed")
        
    print(
        f"{indent_str}{node.spelling}: {node.kind} :: {','.join(tags)} @ "
        f"[{tu.spelling}:{node.location.line}:{node.location.column}]"
    )
    if node.kind.is_preprocessing():
        tokens = ' '.join((repr(token.spelling) for token in clang.cindex.TokenGroup.get_tokens(tu, node.extent)))
        print(f"{spacer_str}{dash_str}{tokens}")
    if node.kind == clang.cindex.CursorKind.FUNCTION_DECL:
        print(f"{spacer_str}returns: {node.result_type.spelling}")

    # recurse on each child:
    for child in node.get_children():
        dbg_print_visit(tu, child, 1 + indent_count)


def translate_clang_type_to_ts(c_type: clang.cindex.Type, is_direct_use=True) -> ast1.BaseTypeSpec:
    ts = help_translate_clang_type_to_ts(c_type.get_canonical(), is_direct_use=is_direct_use)
    ts.wb_type.is_mut = not c_type.is_const_qualified()
    return ts


def help_translate_clang_type_to_ts(c_type, is_direct_use) -> ast1.BaseTypeSpec:
    size_in_bytes = c_type.get_size()
    if is_direct_use and size_in_bytes <= 0 and c_type.kind != TypeKind.VOID:
        # error: indirect type def used directly
        panic.because(
            panic.ExitCode.ExternCompileFailed,
            f"Compilation failed for C type '{c_type.spelling}': could not determine size: undefined data-type used directly?",
            opt_file_path=c_type.translation_unit.spelling
        )
    if c_type.kind == TypeKind.VOID:
        ts = ast1.BuiltinPrimitiveTypeSpec(c_type_loc(c_type), ast1.BuiltinPrimitiveTypeIdentity.Void)
        ts.wb_type = types.VoidType.singleton
        return ts
    elif c_type.kind == TypeKind.BOOL:
        ts = ast1.BuiltinPrimitiveTypeSpec(c_type_loc(c_type), ast1.BuiltinPrimitiveTypeIdentity.Bool)
        ts.wb_type = types.IntType.get(8, is_signed=False)
        return ts
    elif c_type.kind in (TypeKind.CHAR_S, TypeKind.SCHAR, TypeKind.SHORT, TypeKind.INT, TypeKind.LONG, TypeKind.LONGLONG):
        builtin_primitive_type_id = {
            1: ast1.BuiltinPrimitiveTypeIdentity.Int8,
            2: ast1.BuiltinPrimitiveTypeIdentity.Int16,
            4: ast1.BuiltinPrimitiveTypeIdentity.Int32,
            8: ast1.BuiltinPrimitiveTypeIdentity.Int64
        }[size_in_bytes]
        ts = ast1.BuiltinPrimitiveTypeSpec(c_type_loc(c_type), builtin_primitive_type_id)
        ts.wb_type = types.IntType.get(8 * size_in_bytes, is_signed=True)
        return ts
    elif c_type.kind in (TypeKind.UCHAR, TypeKind.USHORT, TypeKind.UINT, TypeKind.ULONG, TypeKind.ULONGLONG):
        builtin_primitive_type_id = {
            1: ast1.BuiltinPrimitiveTypeIdentity.UInt8,
            2: ast1.BuiltinPrimitiveTypeIdentity.UInt16,
            4: ast1.BuiltinPrimitiveTypeIdentity.UInt32,
            8: ast1.BuiltinPrimitiveTypeIdentity.UInt64
        }[size_in_bytes]
        ts = ast1.BuiltinPrimitiveTypeSpec(c_type_loc(c_type), builtin_primitive_type_id)
        ts.wb_type = types.IntType.get(8 * size_in_bytes, is_signed=False)
        return ts
    elif c_type.kind in (TypeKind.FLOAT, TypeKind.DOUBLE, TypeKind.LONGDOUBLE):
        builtin_primitive_type_id = {
            4: ast1.BuiltinPrimitiveTypeIdentity.Float32,
            8: ast1.BuiltinPrimitiveTypeIdentity.Float64,
            16: ast1.BuiltinPrimitiveTypeIdentity.Float128
        }[size_in_bytes]
        ts = ast1.BuiltinPrimitiveTypeSpec(c_type_loc(c_type), builtin_primitive_type_id)
        ts.wb_type = types.FloatType(8 * size_in_bytes)
        return ts
    elif c_type.kind == TypeKind.RECORD:
        # struct or union: must recurse
        declaration = c_type.get_declaration()
        type_name = declaration.spelling
        opt_cached_ts = declaration_cache_map.get(type_name, None)
        type_ctor = {
            ast1.LinearTypeOp.Product: types.StructType,
            ast1.LinearTypeOp.Sum: types.UnionType
        }[lto_map[declaration.kind]]
        if opt_cached_ts is not None:
            assert opt_cached_ts.wb_type is not None
            ts = ast1.IdRefTypeSpec(c_type_loc(c_type), type_name)
            ts.wb_type = opt_cached_ts.wb_type
            return ts
        else:
            # NOTE: must declare this TS (with no fields, say) before translating
            # child types.
            # This way, any 'nested' references (which MUST be indirect uses) can
            # refer to this instance with no fields, and we can retroactively
            # push the fields into this instance.
            fields = []
            ts = ast1.AdtTypeSpec(c_type_loc(c_type), lto_map[declaration.kind], fields)
            ts.wb_type = type_ctor([], opt_name=type_name)  # temporary wb_type

            declaration_cache_map[type_name] = ts

            for it in c_type.get_fields():
                field_key = (
                    it.spelling, 
                    translate_clang_type_to_ts(it.type, is_direct_use=is_direct_use)
                )
                fields.append(field_key)
                ts.push_field(field_key)
            ts.wb_type = type_ctor(
                [
                    (field_name, field_ts.wb_type)
                    for field_name, field_ts in fields
                ],
                opt_name=type_name
            )
            return ts
    elif c_type.kind == TypeKind.POINTER:
        clang_pointee_ts = c_type.get_pointee()
        pointee_ts = translate_clang_type_to_ts(clang_pointee_ts, False)
        contents_is_mut = not clang_pointee_ts.is_const_qualified()
        ts = ast1.PtrTypeSpec(c_type_loc(c_type), pointee_ts, contents_is_mut)
        ts.wb_type = types.PointerType.new(pointee_ts.wb_type, contents_is_mut)
        return ts
    elif c_type.kind == TypeKind.ENUM:
        ts = translate_clang_type_to_ts(c_type.get_declaration().enum_type)
        assert ts.wb_type is not None
        return ts
    elif c_type.kind == TypeKind.FUNCTIONPROTO:
        arg_types = [translate_clang_type_to_ts(arg_type, is_direct_use=False).wb_type for arg_type in c_type.argument_types()]
        ret_ts = translate_clang_type_to_ts(c_type.get_result(), is_direct_use=False)
        is_func_variadic = c_type.is_function_variadic()
        if is_func_variadic:
            raise NotImplementedError("Exposing variadic function type.")
        ts = ast1.ProcSignatureTypeSpec(c_type_loc(c_type), arg_types, ret_ts, takes_closure=False, is_c_variadic=is_func_variadic)
        ts.wb_type = types.ProcedureType.new(arg_types, ret_ts.wb_type, has_closure_slot=False, is_c_variadic=is_func_variadic)
        return ts
    elif c_type.kind == TypeKind.CONSTANTARRAY:
        element_type_spec = translate_clang_type_to_ts(c_type.element_type, is_direct_use=False)
        element_count = c_type.element_count
        is_mut = c_type.element_type.is_const_qualified()
        ts = ast1.ArrayTypeSpec(c_type_loc(c_type), element_type_spec, element_count, is_mut)
        ts.wb_type = types.ArrayType.new(element_type_spec.wb_type, types.UniqueValueType(element_count), is_mut)
        return ts
    else:
        raise NotImplementedError(f"Unknown Clang canonical type kind for type: '{c_type.spelling}' with kind={c_type.kind}")


declaration_cache_map = {}
lto_map = {
    CursorKind.STRUCT_DECL: ast1.LinearTypeOp.Product,
    CursorKind.UNION_DECL: ast1.LinearTypeOp.Sum
}
