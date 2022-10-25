import argparse
import cProfile as profile
import pstats

from ..core import panic
from . import settings
from . import parser


def main_impl():
    args_obj = parse_args()
    compiler_settings = settings.CompilerSettings(
        tmp_root_module_path=args_obj.tmp_root_qy_module_path,
        output_dir_path=args_obj.output_dir_path
    )
    
    # TODO: parse a project file, acquire list of source files by scanning a specified source
    # directory, cf Cargo.toml
    # This is just a debug routine.
    res = parser.qy.parse_file(compiler_settings.tmp_root_module_path)

    # emitter = cpp_emitter.Emitter(output_dir_path)
    # root_qyp = qcl.transpile_one_package_set(root_qyp_path, emitter, transpile_opts)
    # del root_qyp

    return 0


def parse_args():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "tmp_root_qy_module_path", metavar="<DEBUG:path-to-module.qy>",
        help="The path to the project file which contains a map of all source files in use."
    )
    arg_parser.add_argument(
        "-o", "--output-dir-path", metavar="<output-dir-path>",
        help="The directory to which output is written. If it does not exist, it will be created.",
        default="./qc-build"
    )
    arg_parser.add_argument(
        "-v", "--verbose", action="count",
        help="If 'verbose' mode is specified, the compiler prints a bunch of information about compiled files to STDOUT. Good for debugging the compiler.",
        default=0
    )
    return arg_parser.parse_args()


def main(profiling: bool):
    try:
        if profiling:
            with profile.Profile() as pr:
                ec = main_impl()

            ps = pstats.Stats(pr)
            ps.dump_stats("qc_profile_data.pstats")
            return ec
        else:
            return main_impl()
        
    except panic.Exception as exc:
        return exc.exit_code.value
