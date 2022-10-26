import os.path
import argparse
import cProfile as profile
import pstats

from ..core import panic
from ..core import const
from .. import package

from . import settings
from . import parser


def main_impl():
    args_obj = parse_args()
    compiler_settings = settings.CompilerSettings(
        root_package_dir=args_obj.root_package_dir
    )

    root_package = package.parse(compiler_settings.root_package_dir)
    
    # emitter = cpp_emitter.Emitter(output_dir_path)
    # root_qyp = qcl.transpile_one_package_set(root_qyp_path, emitter, transpile_opts)
    # del root_qyp

    return 0


def parse_args():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "-d", "--dir", metavar="<root-package-dirpath>", dest='root_package_dir',
        help="The path to the directory containing the package to build.",
        default="."
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
