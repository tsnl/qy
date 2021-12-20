# TODO:
#   - read https://libclang.readthedocs.io/en/latest/_modules/clang/cindex.html
#   - read https://github.com/llvm-mirror/clang/blob/master/bindings/python/examples/cindex/cindex-dump.py
#   - GOALS:
#       1.  translate select global definitions (with their types) from C to Qy
#       2.  link existing C code with final output
#   - load each header, and expose defined symbols in Qy space
#       - these synthetic Qy definitions are used to type-check.
#       - easiest option (and hence chosen one): generate a Qy AST
#           - ignore forward declarations
#   - load each source, and only translate type definitions to Qy space
#       - thus, ignore function definitions since they are compiled and linked by the backend
#       - use type definitions to expose even forward-declared types
#       - NOTE: clang.cindex only loads files in a platform-dependent way
#   - when emitting,
#       - ensure each used header is included by C++ in an 'extern' block
#       - ensure each of 'sources' are forwarded to final compiler

import typing as t
import itertools

import clang.cindex

from qcl.pair import List

from . import ast1
from . import panic
from . import feedback

index = clang.cindex.Index.create()


def parse_one_file(source_file_path, rem_provided_symbol_list: t.List[str]) -> t.Tuple[t.List[ast1.BaseStatement], t.List[str]]:
    tu = index.parse(
        source_file_path,
        options=clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
    )
    print(f"Parsed C TranslationUnit (TU): {tu.spelling}")
    # dbg_print_visit(tu, tu.cursor)

    if rem_provided_symbol_list:
        res = translate_tu(tu, rem_provided_symbol_list)


    # DEBUG:
    # exit(0)

    return [], []


def translate_tu(tu, rem_provided_symbol_list) -> t.List[ast1.BaseStatement]:
    # FIXME: change iter_list into an iterable when `itertools.chain` is used correctly.
    iter_list = [
        list(translate_tu_top_level_stmt(tu, child_node, rem_provided_symbol_list))
        for child_node in tu.cursor.get_children()
    ]
    return list(itertools.chain(iter_list))


def translate_tu_top_level_stmt(tu, node, rem_provided_symbol_list) -> t.Iterable[ast1.BaseStatement]:
    CursorKind = clang.cindex.CursorKind

    if node.kind == CursorKind.INCLUSION_DIRECTIVE:
        yield from translate_inclusion_directive(tu, node, rem_provided_symbol_list)
    elif node.kind == CursorKind.MACRO_DEFINITION:
        yield from translate_macro_definition(tu, node, rem_provided_symbol_list)

    elif node.kind == CursorKind.STRUCT_DECL:
        yield from translate_struct_decl(tu, node, rem_provided_symbol_list)
    elif node.kind == CursorKind.ENUM_DECL:
        yield from translate_enum_decl(tu, node, rem_provided_symbol_list)
    elif node.kind == CursorKind.FUNCTION_DECL:
        yield from translate_function_decl(tu, node, rem_provided_symbol_list)

    else:
        # ignore this statement
        pass


def translate_inclusion_directive(tu, node, rem_provided_symbol_list):
    # TODO: recursively search for more symbols in the mentioned TU
    return iter(())


def translate_macro_definition(tu, node, rem_provided_symbol_list):
    tokens = list(clang.cindex.TokenGroup.get_tokens(tu, node.extent))
    macro_name = tokens[0].spelling
    if macro_name in rem_provided_symbol_list:
        panic.because(
            panic.ExitCode.UnsupportedExternCFeature,
            "C macros cannot be exported (please re-bind as an inline function, constant, or type if possible)",
            opt_loc=loc(tu.spelling, node)
        )
    return iter(())


def translate_struct_decl(tu, node, rem_provided_symbol_list):
    raise NotImplementedError("Translating a `struct` declaration/definition")


def translate_enum_decl(tu, node, rem_provided_symbol_list):
    raise NotImplementedError("Translating an `enum` declaration/definition")


def translate_function_decl(tu, node, rem_provided_symbol_list):
    node.get_result()
    node.get_arguments()
    raise NotImplementedError("Translating a procedure declaration/definition")


def loc(file_path, node):
    return feedback.FileLoc(file_path, feedback.FilePos(node.location.line-1, node.location.column-1))

    
def dbg_print_visit(tu, node, indent_count=1, tab_w=2):
    CursorKind = clang.cindex.CursorKind

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
