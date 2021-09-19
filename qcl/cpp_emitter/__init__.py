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
- first, we emit a shared runtime library
    - define basic types like `Int?`, `UInt?`, and `Float?` 
    - define `Array<T, n>`, `Slice<T>`, `Tuple<...>`, and `Lambda<...>` (even if wrappers of STL)
    - define builtin functions
    - such that we have a DSL of C++
    * might be easier to `include` this from a C++ file
- next, we emit template declarations for each submodule
- next, we emit submodule definitions. This entails...
    - function declarations
    - value declarations 
    - type definitions
        - each type definition is mapped to a class
- next, we emit submodule member definitions. This entails...
    - function definitions
    - global constant initialization
        - note that global static functions are mapped to a `const` function pointer when defined by lambda
"""

from . import cpp


def emit_project(project):
    # TODO: actually emit the project

    f_cpp = cpp.File("qy-build/output-1.cpp")

    f_cpp.print("#include <iostream>")

    with cpp.namespace_block(f_cpp, "qy"):
        fib_mod_template_args = cpp.TemplateArgs(["T"], [])
        class_name = "fibonacci"

        # TODO: maybe constructors are better off as a separate class?
        constructor_declaration_obj = cpp.FuncDeclaration(
            class_name,
            f"{class_name}{fib_mod_template_args.default_instantiation_string}",
            [],
            None,
            cpp.FuncKind.Constructor,
            is_total=True
        )
        fib_declaration_obj = cpp.FuncDeclaration(
            "fib",
            f"{class_name}{fib_mod_template_args.default_instantiation_string}",
            ["T x"],
            "T",
            cpp.FuncKind.Static,
            is_total=True
        )

        with cpp.poly_submod_block(f_cpp, class_name, fib_mod_template_args):
            constructor_declaration_obj.print_declaration_line_to_file(f_cpp)
            fib_declaration_obj.print_declaration_line_to_file(f_cpp)

        with cpp.define_func_block(f_cpp, constructor_declaration_obj, fib_mod_template_args):
            pass

        with cpp.define_func_block(f_cpp, fib_declaration_obj, fib_mod_template_args):
            with cpp.block(f_cpp, "if (x == 0 || x == 1)"):
                f_cpp.print("return x;")
            with cpp.block(f_cpp, "else"):
                f_cpp.print("return fib(x-1) + fib(x-2);")

    #
    # Entry point:
    #

    f_cpp.print("using namespace qy;")

    with cpp.block(f_cpp, "int main()"):
        f_cpp.print('std::cout << "Hello, world!" << std::endl;')
        f_cpp.print('std::cout << "Fibonacci (26) = " << fibonacci<int>::fib(26) << std::endl;')
        f_cpp.print('return 0;')
        
    print(">- Cpp Tests complete -<")
    print(f"    see: output C++ file: `{f_cpp.path}`")
