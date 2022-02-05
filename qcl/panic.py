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
    TyperSeedingInputError = enum.auto()
    TyperSeedingDoubleBindError = enum.auto()
    TyperModelerUndefinedIdError = enum.auto()
    TyperModelerRedefinedIdError = enum.auto()
    TyperModelerInvalidIdError = enum.auto()
    TyperDtoSolverStalledError = enum.auto()
    TyperDtoSolverFailedError = enum.auto()
    ScopingError = enum.auto()
    EmitterError = enum.auto()
    UnsupportedExternCFeature = enum.auto()
    ExternCompileFailed = enum.auto()


def because(
    exit_code: ExitCode, 
    opt_msg: t.Optional[str] = None, 
    opt_file_path: t.Optional[str] = None,
    opt_file_region: t.Optional[fb.BaseFileRegion] = None,
    opt_loc: t.Optional[fb.ILoc] = None
):
    """
    Halts program execution after printing a helpful error message with a reference to the error.
    NOTE: you can either supply 'opt_file_path', 'opt_file_path, opt_file_region', or 'opt_loc': do not mix otherwise.
    """

    if opt_file_path is not None:
        assert opt_loc is None
    elif opt_loc is not None:
        assert opt_file_path is None and opt_file_region is None

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
    elif opt_loc is not None:
        print(f"abspath: {str(opt_loc)}", file=sys.stderr)
    else:
        # this is OK! sometimes, we have a global error: just ensure message includes locations.
        pass

    raise PanicException(exit_code, msg)
