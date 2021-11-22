import os
import os.path
import typing as t
import argparse
import enum

import qcl


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "root_qyp_path", metavar="<any/abs/or/rel/path/to/some.qyp.json>",
        help="The path to the project file which contains a map of all source files in use."
    )
    arg_parser.add_argument(
        "-o", "--output-dir-path", metavar="<output-dir-path>",
        help="The directory to which output is written. If it does not exist, it will be created.",
        default="./qc-build"
    )
    args_obj = arg_parser.parse_args()
    root_qyp_path = args_obj.root_qyp_path
    output_dir_path = args_obj.output_dir_path
    emitter = qcl.cpp_emitter_v1.Emitter(output_dir_path)
    root_qyp = qcl.transpile_one_package_set(root_qyp_path, emitter)
    return root_qyp


def main_wrapper():
    try:
        main()
    except qcl.panic.PanicException as exc:
        pass


if __name__ == "__main__":
    main_wrapper()
