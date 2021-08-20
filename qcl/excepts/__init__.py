import abc


class CompilationError(BaseException, metaclass=abc.ABCMeta):
    def __init__(self, message_suffix):
        super().__init__(f"An error occurred during compilation: {message_suffix}")


class ParserCompilationError(CompilationError):
    pass


class DependencyDispatchCompilationError(CompilationError):
    pass


class TyperCompilationError(CompilationError):
    pass


class CheckerCompilationError(CompilationError):
    pass


class EmitterCompilationError(CompilationError):
    pass


class CompilerError(BaseException):
    def __init__(self, msg: str):
        super().__init__(f"CompilerError: {msg}")
