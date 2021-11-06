import sys
import typing as t
import enum
import os

from . import feedback as fb


class PanicException(BaseException):
    def __init__(self, exit_code, msg) -> None:
        super().__init__(msg)
        self.exit_code = exit_code
        self.msg = msg


class ExitCode(enum.Enum):
    AllOK = enum.auto()
    BadCliArgs = enum.auto()
    BadProjectFile = enum.auto()
    CompilationFailed = enum.auto()
    InterpreterError = enum.auto()
    SyntaxError = enum.auto()
    TyperUnificationError = enum.auto()


def because(
    exit_code: ExitCode, 
    opt_msg: t.Optional[str] = None, 
    opt_file_path: t.Optional[str] = None,
    opt_file_region: t.Optional[fb.BaseFileRegion] = None
):
    if opt_msg:
        msg = f"PANIC: {opt_msg}"
    else:
        msg = f"PANIC: a fatal error has occurred"
    print(msg, file=sys.stderr)
    
    if opt_file_path:
        custom_end = '\n'
        if opt_file_region is not None:
            custom_end = f":{str(opt_file_region)}\n"

        rel_path = opt_file_path
        abs_path = os.path.abspath(opt_file_path)
        if rel_path == abs_path:
            print(f"abspath: {opt_file_path}", end=custom_end, file=sys.stderr)
        else:
            print(f"relpath: {rel_path}", end=custom_end, file=sys.stderr)
            print(f"abspath: {abs_path}", end=custom_end, file=sys.stderr)
    
    raise PanicException(exit_code, msg)
