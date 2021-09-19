"""
C++ emitter:
- emits a typed polymorphic AST to C++17
- each project gets translated to a single C++ header/source file pair
    - the header file can be consumed by other C++ projects
    - all definitions are inline, since they aren't guaranteed to be inlined anyway
    - since sub-modules may be templated, each sub-module is compiled to a single C++ `class` with static members.
        - cf `inline static` in C++17
    - the source file (`.qy.cpp`) may also contain the entry-point function and the entry point submod instantiation.
- all output source code is put in a namespace called `qy::`

TODO: alter frontend to load from a JSON file, eliminate 'import' and automatically namespace based on directory
      structure (cf Rust)

TODO: add language feature: unary `const` operator: returns identity, but evaluates expression at compile-time.
    - can fold into PTC checks
    - on backend, reading this allows us to insert call to `AOT` macro that forces compile-time evaluation.
"""

"""
STRUCTURE
* NOTE: we flatten the whole sub-module tree before any of the following processing, which is order-independent.
* NOTE: C++ will extract lambdas for us, so we don't need to explicitly declare them/extract context pointers.
    - for correctness, we can generate our own closure set based on IDs already present
    - note that by spec, closures are always by value ('=' in C++)
* NOTE: we flatten template parameters into each namespace member
    - thus, the same template args are duplicated for each sub-mod member
    - since submodules cannot be nested, there is only one template instantiation per submod-field; just moved.
- first, we emit a shared runtime library
    - define basic types like `Int?`, `UInt?`, and `Float?` 
    - define `Array<T, n>`, `Slice<T>`, `Tuple<...>`, and `Lambda<...>` (even if wrappers of STL)
    - define builtin functions
    - such that we have a DSL of C++
    * might be easier to `include` this from a C++ file
- next, we emit template submodule type declarations for all types
    - we use global types so we can create forward declarations
- next, we emit submodule value declarations. This entails...
    - function declarations
    - value declarations 
- next, we emit submodule member definitions. This entails...
    - type definitions
    - function definitions
    - global constant initialization
        - note that global static functions are mapped to a `const` function pointer when defined by lambda
"""

from qcl.ast.node import SubModExp
from qcl import frontend
from qcl import ast
from qcl import typer
from qcl import type as ty

from . import cpp
import random


def emit_project(project: frontend.Project):
    # zeroth: emit shared library prefix:
    
    # first, compiling a map of SubModExp -> QualifiedNamespaceName
    # where QualifiedNamespaceName is a globally-qualified namespace that can be used to reference output for the 
    # submod.
    sub_mod_namespace_map = {}
    for file_mod_index, file_mod_exp in enumerate(project.file_module_exp_list):
        assert isinstance(file_mod_exp, ast.node.FileModExp)
        for sub_mod_name, sub_mod_exp in file_mod_exp.sub_module_map.items():
            qualified_sub_mod_name = f"qy::f{file_mod_index}_{sub_mod_name}"
            sub_mod_namespace_map[sub_mod_exp] = qualified_sub_mod_name

    # opening output files:
    uid = str(random.randint(0, 1000)).ljust(4, "0")
    cpp_file = cpp.File(f"qy-build/output-{uid}.cpp")
    hpp_file = cpp.File(f"qy-build/output-{uid}.hpp")

    # generating a map of `template_args` for each sub_mod:
    sub_mod_template_args_map = {}
    for sub_mod_exp, sub_mod_namespace_name in sub_mod_namespace_map.items():
        assert isinstance(sub_mod_exp, ast.node.SubModExp)

        # parsing 'template_args' for this module
        assert isinstance(sub_mod_exp, ast.node.SubModExp)
        
        # sorting type and value arg names:
        type_arg_names = []
        value_arg_names = []
        for arg_name in sub_mod_exp.template_arg_names:
            du = typer.names.infer_def_universe_of(arg_name)
            if du == typer.definition.Universe.Type:
                type_arg_names.append(arg_name)
            elif du == typer.definition.Universe.Value:
                value_arg_names.append(arg_name)
        
        value_arg_index = 0
        value_arg_tids = []
        for arg_def in sub_mod_exp.template_def_list_from_typer:
            assert isinstance(arg_def, typer.definition.BaseRecord)
            if arg_def.name == value_arg_names[value_arg_index]:
                value_arg_index += 1
                sub, arg_tid = arg_def.scheme.shallow_instantiate()
                assert sub is typer.substitution.empty
                value_arg_tids.append(arg_tid)

        value_arg_decls = [
            f"{translate_ts(val_arg_tid)} {val_arg_name}"
            for val_arg_name, val_arg_tid in zip(value_arg_names, value_arg_tids)
        ]

        print(sub_mod_namespace_name)
        print(f"- Type arg names = {type_arg_names}")
        print(f"- Value arg names = {value_arg_names}")
        print(f"- Value arg TIDs = [{', '.join(map(lambda tid: repr(ty.spelling.of(tid)), value_arg_tids))}]")
        sub_mod_template_args = cpp.TemplateArgs(
            type_arg_names,
            value_arg_decls,
            has_variadic_suffix=False
        )

        sub_mod_template_args_map[sub_mod_exp] = sub_mod_template_args
        
    # NOTE: prefer to map def_rec_objects 

    # TODO: PHASE 1:
    #   - generate forward declarations for all types
    
    # TODO: PHASE 2
    #   - generate forward declarations for all functions
    #   - generate type bindings/definitions

    # TODO: PHASE 3
    #   - generate function definitions

    # TODO: implement emitters
    # emitting (...)
    for sub_mod_exp, sub_mod_namespace_name in sub_mod_namespace_map.items():
        with cpp.namespace_block(cpp_file, sub_mod_namespace_name):
            sub_mod_template_args = sub_mod_template_args_map[sub_mod_exp]
            assert isinstance(sub_mod_template_args, cpp.TemplateArgs)
            with cpp.define_func_block(
                cpp_file,
                cpp.FuncDeclaration(
                    "hello", "", 
                    arg_decls=["int x"], 
                    opt_func_return_type="int",
                    template_args=sub_mod_template_args,
                    func_kind=cpp.FuncKind.GlobalFunction,
                    is_total=False
                )
            ):
                cpp_file.print("return x;")

    # closing, reporting written files:
    cpp_file.close()
    hpp_file.close()
    print(f"INFO: wrote to {repr(cpp_file.path)} and {repr(hpp_file.path)} successfully")



def translate_ts(tid):
    opt_primitive_ts = ({
        ty.get_int_type(1, is_unsigned=True): "::bool"
    } | {
        ty.get_int_type(bit_width, is_unsigned=True): f"::uint{bit_width}_t"
        for bit_width in (8, 16, 32, 64)
    } | {
        ty.get_int_type(bit_width, is_unsigned=False): f"::int{bit_width}_t"
        for bit_width in (8, 16, 32, 64)
    } | {
        ty.get_float_type(32): "float",
        ty.get_float_type(64): "long double"
    }).get(tid, None)
    if opt_primitive_ts is not None:
        return opt_primitive_ts
    
    raise NotImplementedError(f"Unknown TS: do not know how to translate TID {tid}")
