import qy.compiler
import sys

expected_python_version = "3.9"


def exit_if_bad_python_version():
    if not sys.version.startswith(expected_python_version):
        print("[QY] [ERROR]  Expected Python " + expected_python_version)
        print("[QY] [ERROR]  Got: Python " + sys.version)
        exit(-1)


if __name__ == "__main__":
    exit_if_bad_python_version()
    exit(qy.compiler.cli.main(profiling=False))
