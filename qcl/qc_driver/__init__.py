import os
import os.path as path
import argparse
import traceback

from qcl import ast
from qcl import excepts
from qcl import frontend
from qcl import typer


def main():
    project = frontend.Project(os.getcwd())

    args_obj = parse_args()
    if not validate_args(args_obj):
        print_detailed_help()
        return 1

    in_s_mode = args_obj.s_mode_cwd is not None
    in_c_mode = args_obj.c_mode_entry_point is not None

    if in_c_mode:
        # build frontend: run dependency dispatch by recursively parsing and dispatching:
        try:
            file_module_exp_list = frontend.load_project(project, args_obj.c_mode_entry_point)
        except (excepts.DependencyDispatchCompilationError, excepts.ParserCompilationError) as e:
            # TODO: fold exception data into feedback, print, and exit elegantly.
            raise e from e
        else:
            # DEBUG:
            print(f"LOADED {len(file_module_exp_list)} modules:")
            print(f"* CWD: {project.abs_working_dir_path}")
            for file_module_exp in file_module_exp_list:
                assert isinstance(file_module_exp, ast.node.FileModExp)
                print(f"- {file_module_exp.source.file_path_rel_cwd}")

        # run typer on the frontend:
        try:
            typer.type_project(project, file_module_exp_list)
        except excepts.TyperCompilationError as e:
            # TODO: fold exception data into feedback, print, and exit elegantly.
            raise e from e
        else:
            # DEBUG:
            print(f"INFO: Typer successful.")

        # todo: perform 'basic' checks: side-effect-specs respected, existence of initialization order
        print("WARNING: skipping basic checks")

        # todo: perform SMT analysis: no de-referencing `nullptr`, pointer escape analysis with `push`
        #   - using Z3 library
        print("WARNING: skipping SMT checks")

        # todo: emit LLVM IR from Qy and C/C++ source code in `frontend` (using `libclang`).
        print("WARNING: skipping emitting output")

        return 0

    elif in_s_mode:
        raise NotImplementedError("Compiler driver for S-mode")

    else:
        raise NotImplementedError("Unknown compiler mode.")


def parse_args():
    arg_parser.add_argument(
        '-s', '--server-mode', type=str,
        dest='s_mode_cwd', action='store',
        help="Run an LSP server using the parameter path as the working directory"
    )
    arg_parser.add_argument(
        '-c', '--compiler-mode', type=str,
        dest='c_mode_entry_point', action='store',
        help="Compile a source tree using the parameter path as the entry point, and its container directory as the "
             "working directory"
    )

    args_obj = arg_parser.parse_args()

    return args_obj


def validate_args(args_obj):
    in_s_mode = args_obj.s_mode_cwd is not None
    in_c_mode = args_obj.c_mode_entry_point is not None

    if in_s_mode and in_c_mode:
        eprint("must enable either `server-mode` or `compiler-mode`, but not both")
        return False

    if not in_s_mode and not in_c_mode:
        eprint("must enable either `server-mode` or `compiler-mode` (but not both)")
        return False

    if in_s_mode:
        if not path.isdir(args_obj.s_mode_cwd):
            eprint(f"inaccessible/non-existent working dir: {args_obj.s_mode_cwd}")
            return False
    elif in_c_mode:
        if not path.isfile(args_obj.c_mode_entry_point):
            eprint(f"inaccessible/non-existent entry point file path: {args_obj.c_mode_entry_point}")

    return True


def print_detailed_help():
    arg_parser.print_help()


def eprint(message):
    print(f"CLI-ERROR: {message}")


arg_parser_desc = """
The Command-line QC Tool

- run in either `compiler-mode` or `server-mode` (see below)
- can 'abbreviate' long command line flags, so `--comp` and `--server` are also valid, unambiguous flags

- COMPILER MODE
    - transforms a tree of input files into a tree of output files, then exits
    - input files include: 
        1. Qy source code, 
        2. C source code (via static or dynamically loadable extensions) (via `extern`), 
        3. misc. text and binary files 
    - output files include:
        1. executable and linkable files (executable applications, libraries, and DLLs)
        2. copied misc. text and binary files
    - locations of output files 
"""
arg_parser = argparse.ArgumentParser(
    description=arg_parser_desc.strip(),
    allow_abbrev=True,
    add_help=True
)
