import abc


class CompilationError(BaseException, metaclass=abc.ABCMeta):
    def __init__(self, message):
        super().__init__(f"An error occurred during compilation: {message}")


class ParserCompilationError(CompilationError):
    pass


class TyperCompilationError(CompilationError):
    pass


class CheckerCompilationError(CompilationError):
    pass


class EmitterCompilationError(CompilationError):
    pass
