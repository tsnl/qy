import os.path
import typing as t
import argparse
import enum

import qcl


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "root_qyp_path", metavar="<any/abs/or/rel/path.qyp.json>",
        help="The path to the project file which contains a map of all source files in use."
    )
    args_obj = arg_parser.parse_args()

    root_qyp_path = args_obj.root_qyp_path
    if not root_qyp_path.endswith(qcl.config.PROJECT_FILE_EXTENSION):
        qcl.panic.because(
            qcl.panic.ExitCode.BadCliArgs, 
            f"expected project file path to end with '{qcl.config.PROJECT_FILE_EXTENSION}', got:", 
            root_qyp_path
        )
    if not os.path.isfile(root_qyp_path):
        qcl.panic.because(
            qcl.panic.ExitCode.BadProjectFile,
            f"project file path does not refer to a file:",
            root_qyp_path
        )

    root_qyp = qcl.transpile_one_package_set(root_qyp_path)
    return root_qyp


if __name__ == "__main__":
    main()
