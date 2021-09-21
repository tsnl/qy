# A C++ code generation library
#   - cf https://www.codeproject.com/Articles/571645/Really-simple-Cplusplus-code-generation-in-Python

import string
import functools
import typing as t
import enum

from qcl import excepts

# enable_runtime_checks controls whether arguments to functions are checked for correctness.
# it should be used in debug mode, not production.
enable_runtime_checks = True


class FileType(enum.Enum):
    Cpp = enum.auto()
    Hpp = enum.auto()


class File(object):
    def __init__(
        self, 
        file_path: str,
        indent_str='\t',
        opt_builtin_header_names=None,
        opt_client_header_names=None
    ):
        is_source = file_path.endswith(".cpp")
        is_header = file_path.endswith(".hpp")
        if not (is_source or is_header):
            raise excepts.CompilerError("cpp_emitter can only generate `*.cpp` or `*.hpp` files.")
        elif is_source:
            file_type = FileType.Cpp
        else:
            file_type = FileType.Hpp

        super().__init__()
        self.type = file_type
        self.path = file_path
        self.file = open(self.path, "w")
        self.indent_count = 0
        self.indent_str = indent_str
        self.builtin_header_names = get_opt_iterable(opt_builtin_header_names)
        self.client_header_names = get_opt_iterable(opt_client_header_names)

        self.builtin_header_names.append("type_traits")
        self.builtin_header_names.append("cstddef")
        self.builtin_header_names.append("cstdint")
        self.builtin_header_names.append("cmath")

        #
        # Post-initialization setup:
        #

        self.print("// General setup:")
        
        for builtin_header_name in self.builtin_header_names:
            self.print(f"#include <{builtin_header_name}>")
        for client_header_name in self.client_header_names:
            self.print(f"#include \"{client_header_name}\"")

        self.print("#define SUB struct")
        self.print("#define AOT(e) (std::integral_constant<decltype(e), e>::value)")

        self.print("")
        self.print("// Project output:")

    def close(self):
        self.file.close()

    def print(self, msg_obj, end='\n'):
        if isinstance(msg_obj, str):
            msg = msg_obj
        else:
            msg = str(msg_obj)

        lines = msg.split('\n')
        net_indent = self.indent_str * self.indent_count
        lines = [net_indent + line for line in lines]
        msg = '\n'.join(lines)
        print(msg, end=end, file=self.file)


class Block(object):
    def __init__(self, cpp_file: File, intro_line, outro_str="") -> None:
        super().__init__()
        self.cpp_file = cpp_file
        self.intro_line = intro_line
        self.outro_str = outro_str

    def __enter__(self):
        self.cpp_file.print(self.intro_line)
        self.cpp_file.print("{")
        self.cpp_file.indent_count += 1
        
    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.cpp_file.indent_count -= 1
        self.cpp_file.print(f"}}{self.outro_str}")


class TemplateArgs(object):
    def __init__(
        self,
        opt_template_type_arg_names: t.Optional[str] = None,
        opt_template_value_arg_decls: t.Optional[str] = None,
        has_variadic_suffix: bool = False,
    ) -> None:
        super().__init__()

        # conversions and checks:
        template_type_arg_names = get_opt_iterable(opt_template_type_arg_names)
        template_value_arg_decls = get_opt_iterable(opt_template_value_arg_decls)
        self.help_check_str_iterable(template_type_arg_names, check_id)
        self.help_check_str_iterable(template_value_arg_decls, check_decl)

        self.template_type_arg_names = template_type_arg_names
        self.template_value_arg_decls = template_value_arg_decls
        self.has_variadic_suffix = has_variadic_suffix
        self.default_instantiation_string = (
            "<" + ", ".join(
                self.template_type_arg_names + 
                [split_decl(decl)[1] for decl in self.template_value_arg_decls]
            ) + ">"
            if len(self.template_type_arg_names) + len(self.template_value_arg_decls) else
            ""
        )

    def __bool__(self):
        return bool(len(self.template_type_arg_names) + len(self.template_value_arg_decls))
    
    @classmethod
    def help_check_str_iterable(cls, arg_str_iterable, check_fn):
        if enable_runtime_checks:
            for arg_str in arg_str_iterable:
                check_fn(arg_str, cls.__name__)
        
    @property
    def declaration_string(self):
        type_args_str = (
            ", ".join(f"typename {t}" for t in self.template_type_arg_names)
            if self.template_type_arg_names else
            ""
        )
        val_args_str = (
            ", ".join(val_arg_spec for val_arg_spec in self.template_value_arg_decls)
        )

        empty_declaration_string = False
        if type_args_str and val_args_str:
            args_str = type_args_str + ", " + val_args_str
        elif type_args_str:
            args_str = type_args_str
        elif val_args_str:
            args_str = val_args_str
        else:
            empty_declaration_string = True

        if not empty_declaration_string:
            return f"template <{args_str}>"
        else:
            return ""

    def print_declaration_line_to_file(self, f: File):
        f.print(self.declaration_string)
    

class FuncKind(enum.Enum):
    GlobalFunction = enum.auto()
    StaticMethod = enum.auto()
    VirtualMethod = enum.auto()
    PureVirtualMethod = enum.auto()
    OverrideMethod = enum.auto()
    ConstructorMethod = enum.auto()


class FuncDeclaration(object):
    def __init__(
        self,
        func_name: str,
        func_fully_qualified_name_prefix: str,
        arg_decls: t.Iterable[str],
        opt_func_return_type: t.Optional[str],
        func_kind: FuncKind,
        template_args: TemplateArgs,
        is_total: bool,
        explicit_this_ptr_is_const=False,
    ):
        if enable_runtime_checks and opt_func_return_type is not None:
            check_ts(opt_func_return_type, self.__class__.__name__)
        for decl in arg_decls:
            check_decl(decl, self.__class__.__name__)
    
        super().__init__()
        self.func_name = func_name
        self.func_fully_qualified_name_prefix = func_fully_qualified_name_prefix
        self.arg_decls = arg_decls
        self.opt_func_return_type = opt_func_return_type
        self.func_kind = func_kind
        self.template_args = template_args
        self.explicit_this_ptr_is_const = explicit_this_ptr_is_const
        self.is_total = is_total

    @property
    def func_fully_qualified_name(self):
        if self.func_fully_qualified_name_prefix:
            return f"{self.func_fully_qualified_name_prefix}::{self.func_name}"
        else:
            return self.func_name

    def to_string(self, not_for_decl: bool):
        # header:
        header_list = []
        if self.is_total:
            header_list.append("constexpr")
        if self.template_args:
            header_list.append(self.template_args.declaration_string)
        header = " ".join(header_list)

        # prefix:
        prefix_list = []
        if not not_for_decl and self.func_kind == FuncKind.StaticMethod:
            prefix_list.append('static')
        elif not not_for_decl and self.func_kind in (FuncKind.VirtualMethod, FuncKind.PureVirtualMethod, FuncKind.OverrideMethod):
            prefix_list.append('virtual')
        prefix = " ".join(prefix_list)

        # main: main part of declaration
        arg_str = ", ".join(self.arg_decls)
        name = self.func_fully_qualified_name if not_for_decl else self.func_name
        if self.opt_func_return_type:
            main = f"{self.opt_func_return_type} {name}({arg_str})"
        else:
            main = f"{name}({arg_str})"

        # suffix:
        suffix_list = []
        if self.explicit_this_ptr_is_const:
            suffix_list.append('const')
        if self.func_kind == FuncKind.OverrideMethod:
            suffix_list.append('override')
        elif self.func_kind == FuncKind.PureVirtualMethod:
            suffix_list.append('= 0')
        suffix = " ".join(suffix_list)

        # pulling together:
        total_list = []
        if header:
            total_list.append(header)
        if prefix:
            total_list.append(prefix)
        total_list.append(main)
        if suffix:
            total_list.append(suffix)
        return " ".join(total_list)

    def print_declaration_line_to_file(self, f: File):
        f.print(self.to_string(not_for_decl=False) + ";")


class ConstructorDeclaration(FuncDeclaration):
    def __init__(self, class_name, template_args: TemplateArgs, is_total: bool):
        super().__init__(
            class_name,
            f"{class_name}<{template_args.default_instantiation_string}>",
            [], None,
            FuncKind.ConstructorMethod,
            is_total=is_total
        )


# TODO: add a ValueDeclaration


#
# Block functions:
#


def block(cpp_file, introduction_str):
    return Block(cpp_file, introduction_str)


def namespace_block(cpp_file, *namespace_seq):
    return Block(cpp_file, f"namespace {'::'.join(namespace_seq)}")


def submod_block(cpp_file, cls_name, opt_immediate_instance_names=None):
    """
    Print a monomorphic (untemplated) class block for a submodule.
    Note that this block may still admit a template prefix that may be printed out prior to it 
        - (cf `poly_submod_block`)
    Note that we use the `struct` keyword since it is just `class` with the default visibility specifier set to 
    `public`.
    @param cpp_file: the file to which output is printed
    @param cls_name: the name of the class whose block to begin
    @param immediate_instance_names: an optional list of immediate instances of this class to declare.
    """
    immediate_instance_names = get_opt_iterable(opt_immediate_instance_names)
    immediate_instance_names_str = ', '.join(immediate_instance_names)

    return Block(
        cpp_file, 
        f"SUB {cls_name}", 
        outro_str=f"{immediate_instance_names_str};"
    )


def poly_submod_block(cpp_file: File, cls_name: str, template_args: TemplateArgs):
    """
    Print a polymorphic (templated) class block for a submodule.
    @param cpp_file: the file to which output is printed
    @param cls_name: the name of the class whose block to begin
    @param template_args: a `TemplateArgs` instance describing formal template arguments.
    """

    template_args.print_declaration_line_to_file(cpp_file)
    return submod_block(cpp_file, cls_name)


def define_func_block(
    cpp_file: File, 
    func_decl: FuncDeclaration
):
    return block(cpp_file, func_decl.to_string(not_for_decl=True))


#
# Check functions
#

def raise_check_error(msg: str):
    raise ValueError(msg)


def check_id(s: str, context_desc: str):
    ok = all(map(lambda c: c.isalpha() or c == '_', s))
    if not ok:
        raise raise_check_error(f"invalid ID in {context_desc}")


def split_decl(s):
    last_space_index = s.rfind(' ')
    if last_space_index < 0:
        raise_check_error(f"invalid decl in {context_desc}: must contain at least 1 space before declared ID.")
    
    ts = s[:last_space_index]
    id = s[1+last_space_index:]
    return ts, id


def check_decl(s: str, context_desc: str):
    ts, id = split_decl(s)
    check_ts(ts, context_desc)
    check_id(id, context_desc)


def check_ts(s: str, context_desc: str):
    # ignore this; too complicated, since we'd start parsing C++ TSes.
    # maybe recognize some valid strings, print warnings for suspicious ones?
    pass


#
# Shared helpers:
#

def get_opt_iterable(opt_iterable):
    if opt_iterable is None:
        return []
    else:
        return list(opt_iterable)
