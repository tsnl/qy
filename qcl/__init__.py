from dataclasses import dataclass
import json

from . import config
from . import panic
from . import feedback as fb
from . import ast2
from . import typer
from . import cpp_emitter
from . import base_emitter
from . import types
from . import platform
from . import main


@dataclass
class TranspileOptions:
    print_summary_after_run: bool = config.COMPILER_IN_DEBUG_MODE
    run_debug_routine_after_compilation: bool = config.COMPILER_IN_DEBUG_MODE


def transpile_one_package_set(path_to_input_root_qyp_file: str, emitter: base_emitter.BaseEmitter, transpile_opts: TranspileOptions):
    assert isinstance(path_to_input_root_qyp_file, str)
    assert isinstance(emitter, base_emitter.BaseEmitter)

    # FIXME: auto-detect target platform
    target_platform = platform.core_linux_amd64
    # target_platform = platform.core_windows_amd64
    # target_platform = platform.core_macos_amd64

    qyp_set = ast2.QypSet.load(path_to_input_root_qyp_file, target_platform)
    if qyp_set is None:
        panic.because(
            panic.ExitCode.BadProjectFile,
            "Failed to load project files: please see above errors"
        )

    caught_exc = None

    # compilation:
    try:    
        # basic checks

        # TODO: perform basic checks on AST structure
        #   - only certain statements allowed in top-level, function bodies, etc.
        #       - 'return', 'ite' not allowed except inside a function
        #       - 'const', 'bind1f' only globally allowed
        #   - `iota` expression only allowed inside a 'const' initializer
        # NOTE: this is happening during 'seeding' in the typer instead... clean up typer if this changes.

        # typing native source files:
        # - two distinct passes: seeding and modelling
        typer.type_one_qyp_set(qyp_set)

        # TODO: run post-typing checks
        # - e.g. check that 'main' has the correct signature.

        # compile-time evaluation:
        
        # emitting:
        emitter.emit_qyp_set(qyp_set)
    except panic.PanicException as exc:
        caught_exc = exc
    
    # (post-compilation) print types:
    if transpile_opts.print_summary_after_run:
        print("(POST-MORTEM)")
        print_qyp_set_summary(qyp_set)
        print_contexts(qyp_set)

    # (post-compilation) debug routine:
    if transpile_opts.run_debug_routine_after_compilation:
        print("(POST-MORTEM)")
        debug_routine_after_compilation(qyp_set)

    if caught_exc is not None:
        raise caught_exc


def debug_routine_after_compilation(qyp_set):
    print("INFO: Post-compilation Debug Dump")
    print_types_test()
    print_schemes_test()
    print_unification_subs_test()


def print_qyp_set_summary(qyp_set):
    print("... Module summary:")
    for qyp_name, qyp in qyp_set.qyp_name_map.items():
        print(f"- qyp {repr(qyp_name)} @ path({repr(qyp.file_path)})")
        for src_file in qyp.iter_native_src_paths():
            print(f"  - Qy source file @ path({repr(src_file)})")


def print_types_test():
    vec2 = types.StructType([('x', types.FloatType(32)), ('y', types.FloatType(32))])
    vec3 = types.StructType([('x', types.FloatType(32)), ('y', types.FloatType(32)), ('z', types.FloatType(32))])
    print("... Types print-test:")
    print('\t' + '\n\t'.join(map(str, [
    types.IntType.get(8, True),
        types.IntType.get(16, True),
        types.IntType.get(32, True),
        types.IntType.get(64, True),
        types.IntType.get(8, False),
        types.IntType.get(16, False),
        types.IntType.get(32, False),
        types.IntType.get(64, False),
        vec2,
        vec3,
        types.UnionType([('v3', vec3), ('v2', vec2)]),
    ])))


def print_schemes_test():
    h_a = types.VarType('a')
    h_b = types.VarType('b')
    scm = typer.Scheme([h_a, h_b], types.StructType([('x', h_a), ('y', h_b)]))
    instantiate_sub, instantiated_type = scm.instantiate([types.IntType.get(32, True), types.IntType.get(64, True)])
    print("... Scheme print-test:")
    print('\tScheme:            ' + str(scm))
    print('\tInstantiation sub: ' + str(instantiate_sub))
    print('\tInstantiated type: ' + str(instantiated_type))


def print_unification_subs_test():
    print("... Unifier print-test:")

    # unifying an atomic type to a single variable (simple)
    t1 = types.VarType("a")
    t2 = types.IntType.get(32, True)
    verbose_unify(t1, t2)

    # unifying structs:
    t3 = types.VarType("b")
    t4 = types.StructType([
        ('field1', t1), 
        ('field2', t2)
    ])
    t5 = types.StructType([
        ('field1', t2),
        ('field2', t2)
    ])
    verbose_unify(t3, t4)
    verbose_unify(t4, t3)
    verbose_unify(t4, t5)
    verbose_unify(t5, t4)

    # unifying procedures:
    # attempting to unify one var to two matching types:
    t6 = types.ProcedureType.new([t2, t2, t5], t2, True)
    t7 = types.ProcedureType.new([t2, t3, t4], t1, True)
    verbose_unify(t6, t7)

    # attempting to unify one var to two conflicting types:
    ft = types.FloatType.get(32)
    t8 = types.ProcedureType.new([ft], t2)
    t9 = types.ProcedureType.new([t1], t1)
    verbose_unify(t8, t9)


def verbose_unify(t, u, annotation=""):
    print('\tinput1: ' + str(t))
    print('\tinput2: ' + str(u))
    
    output_str = "<UNKNOWN_ERROR>"
    try:
        output_str = str(typer.unify(t, u))
    except panic.PanicException as pe:
        if pe.exit_code == panic.ExitCode.TyperUnificationError:
            output_str = "<UNIFICATION_ERROR>"

    print('\toutput: ' + output_str)
    if annotation:
        print(f"\t*** {annotation}")


def print_contexts(qyp_set):
    print("... Contexts output")
    for _, _, source_file in qyp_set.iter_src_paths():
        if source_file.wb_typer_ctx is not None:
            source_file.wb_typer_ctx.print(indent_count=1)
