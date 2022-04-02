import argparse
import cProfile as profile
import pstats

import qcl


def main():
    args_obj = parse_args()
    transpile_opts = qcl.TranspileOptions(print_summary_after_run=args_obj.verbose > 0, run_debug_routine_after_compilation=False)
    root_qyp_path = args_obj.root_qyp_path
    output_dir_path = args_obj.output_dir_path

    emitter = qcl.cpp_emitter.Emitter(output_dir_path)
    root_qyp = qcl.transpile_one_package_set(root_qyp_path, emitter, transpile_opts)
    del root_qyp

    return 0


def parse_args():
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
    arg_parser.add_argument(
        "-v", "--verbose", action="count",
        help="If 'verbose' mode is specified, the compiler prints a bunch of information about compiled files to STDOUT. Good for debugging the compiler.",
        default=0
    )
    return arg_parser.parse_args()


def main_wrapper(profiling=False):
    try:
        if profiling:
            with profile.Profile() as pr:
                ec = main()

            ps = pstats.Stats(pr)
            ps.dump_stats("qc_profile_data.pstats")
            return ec
        else:
            return main()
        
    except qcl.panic.PanicException as exc:
        return exc.exit_code.value
