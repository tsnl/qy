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

index = clang.cindex.Index.create()
CursorKind = clang.cindex.CursorKind
TypeKind = clang.cindex.TypeKind


def parse_one_file(source_file_path, rem_provided_symbols: t.Set[str], is_header: bool) -> t.Tuple[t.List[ast1.BaseStatement], t.Set[str]]:
    tu = index.parse(
        source_file_path,
        # options=clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
    )
    print(f"Parsed C TranslationUnit (TU): {tu.spelling}")
    dbg_print_visit(tu, tu.cursor)

    all_provided_symbols = set(rem_provided_symbols)
    if rem_provided_symbols:
        stmt_list = translate_tu(tu, rem_provided_symbols)
    exposed_symbols = all_provided_symbols - rem_provided_symbols

    return stmt_list, exposed_symbols


def translate_tu(tu, rem_provided_symbols) -> t.List[ast1.BaseStatement]:
    # FIXME: change iter_list into an iterable when `itertools.chain` is used correctly.
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

    else:
        # ignore this statement
        pass


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
        adt_ts = ast1.AdtTypeSpec(
            loc(node),
            lto_map[node.kind],
            [
                (field_node.spelling, translate_adt_field_decl_to_ts(tu, field_node, rem_provided_symbols))
                for field_node in node.get_children()
            ]
        )
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
            bind1v_stmt = ast1.Bind1vStatement(loc(entry), entry.spelling, init_exp)
            body.append(bind1v_stmt)
        yield ast1.ConstStatement(loc(node), body, const_ts)


def translate_adt_field_decl_to_ts(tu, node, rem_provided_symbols):
    assert node.kind == CursorKind.FIELD_DECL
    return translate_clang_type_to_ts(node.type)


def translate_function_decl(tu, node, rem_provided_symbols):
    func_name = node.spelling
    func_ret_type = node.type.get_result()
    func_arg_types = node.type.argument_types()
    func_arg_names = map(lambda x: x.spelling, node.get_arguments())
    func_args = zip(func_arg_names, func_arg_types)
    if func_name in rem_provided_symbols:
        rem_provided_symbols.remove(func_name)
        fn_str = func_ret_type.spelling + "(*)" + "(" + ', '.join((t.spelling for n, t in func_args)) + ")"
        raise NotImplementedError(f"Translating a function forward declaration: {fn_str}")
        # print()
    # exit()
    return iter(())


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


def translate_clang_type_to_ts(c_type):
    c_type = c_type.get_canonical()
    size_in_bytes = c_type.get_size()
    is_const_qualified = c_type.is_const_qualified()
    if size_in_bytes <= 0:
        # error: indirect type def used directly
        panic.because(
            panic.ExitCode.ExternCompileFailed,
            f"Compilation failed for C type '{c_type.spelling}': could not determine size: undefined data-type used directly?",
            opt_file_path=c_type.translation_unit.spelling
        )

    if c_type.kind == TypeKind.VOID:
        return ast1.BuiltinPrimitiveTypeSpec(ast1.BuiltinPrimitiveTypeIdentity.Void)
    elif c_type.kind == TypeKind.BOOL:
        return ast1.BuiltinPrimitiveTypeSpec(ast1.BuiltinPrimitiveTypeIdentity.Bool)
    elif c_type.kind == TypeKind.CHAR_S:
        return ast1.BuiltinPrimitiveTypeSpec(ast1.BuiltinPrimitiveTypeIdentity.Int8)
    elif c_type.kind in (TypeKind.CHAR_S, TypeKind.INT, TypeKind.LONG, TypeKind.LONGLONG):
        builtin_primitive_type_id = {
            1: ast1.BuiltinPrimitiveTypeIdentity.Int8,
            2: ast1.BuiltinPrimitiveTypeIdentity.Int16,
            4: ast1.BuiltinPrimitiveTypeIdentity.Int32,
            8: ast1.BuiltinPrimitiveTypeIdentity.Int64
        }[size_in_bytes]
        return ast1.BuiltinPrimitiveTypeSpec(c_type_loc(c_type), builtin_primitive_type_id)
    elif c_type.kind in (TypeKind.UCHAR, TypeKind.UINT, TypeKind.ULONG, TypeKind.ULONGLONG):
        builtin_primitive_type_id = {
            1: ast1.BuiltinPrimitiveTypeIdentity.UInt8,
            2: ast1.BuiltinPrimitiveTypeIdentity.UInt16,
            4: ast1.BuiltinPrimitiveTypeIdentity.UInt32,
            8: ast1.BuiltinPrimitiveTypeIdentity.UInt64
        }[size_in_bytes]
        return ast1.BuiltinPrimitiveTypeSpec(c_type_loc(c_type), builtin_primitive_type_id)
    elif c_type.kind in (TypeKind.FLOAT, TypeKind.DOUBLE):
        builtin_primitive_type_id = {
            4: ast1.BuiltinPrimitiveTypeIdentity.Float32,
            8: ast1.BuiltinPrimitiveTypeIdentity.Float64
        }[size_in_bytes]
        return ast1.BuiltinPrimitiveTypeSpec(c_type_loc(c_type), builtin_primitive_type_id)
    elif c_type.kind == TypeKind.RECORD:
        # struct or union: must recurse
        declaration = c_type.get_declaration()
        fields = [(it.spelling, translate_clang_type_to_ts(it.type)) for it in c_type.get_fields()]
        return ast1.AdtTypeSpec(
            c_type_loc(c_type),
            lto_map[declaration.kind],
            fields    
        )
    elif c_type.kind == TypeKind.POINTER:
        pointee_ts = translate_clang_type_to_ts(c_type.get_pointee())
        contents_is_mut = not pointee_ts.is_const_qualified()
        return ast1.PtrTypeSpec(
            c_type_loc(c_type),
            pointee_ts,
            contents_is_mut
        )
    elif c_type.kind == TypeKind.ENUM:
        return translate_clang_type_to_ts(c_type.get_declaration().enum_type)
    elif c_type.kind == TypeKind.FUNCTIONPROTO:
        args = [(None, translate_clang_type_to_ts(arg_type)) for arg_type in c_type.argument_types()]
        ret_ts = translate_clang_type_to_ts(c_type.get_result())
        is_func_variadic = c_type.is_function_variadic()
        return ast1.ProcSignatureTypeSpec(c_type_loc(c_type), args, ret_ts)
    else:
        raise NotImplementedError(f"Unknown Clang canonical type kind for type: '{c_type.spelling}'")


lto_map = {
    CursorKind.STRUCT_DECL: ast1.LinearTypeOp.Product,
    CursorKind.UNION_DECL: ast1.LinearTypeOp.Sum
}
