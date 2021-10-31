import typing as t
import enum
import os

from . import feedback as fb


class ExitCode(enum.Enum):
    AllOK = enum.auto()
    BadCliArgs = enum.auto()
    BadProjectFile = enum.auto()
    CompilationFailed = enum.auto()
    InterpreterError = enum.auto()
    SyntaxError = enum.auto()


def because(
    exit_code: ExitCode, 
    opt_msg: t.Optional[str] = None, 
    opt_file_path: t.Optional[str] = None,
    opt_file_region: t.Optional[fb.BaseFileRegion] = None
):
    if opt_msg:
        print(f"PANIC: {opt_msg}")
    if opt_file_path:
        custom_end = '\n'
        if opt_file_region is not None:
            custom_end = f":{str(opt_file_region)}\n"

        print(f"relpath: {opt_file_path}", end=custom_end)
        print(f"abspath: {os.path.abspath(opt_file_path)}", end=custom_end)
    
    exit(exit_code.value)
