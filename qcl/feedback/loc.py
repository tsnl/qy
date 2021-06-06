import abc

#
# ILoc: different ways to indicate a location in the interpreter system
# - e.g. in a text file
# - e.g. in builtins
#


class ILoc(object, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __str__(self):
        pass


class BuiltinLoc(ILoc):
    def __init__(self, purpose):
        super().__init__()
        self.purpose = purpose

    def __str__(self):
        return f"<builtin:{self.purpose}>"


class TextFileLoc(ILoc):
    text_file_path: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int

    def __init__(self, text_file_path, start_line, start_column, end_line, end_column):
        super().__init__()
        self.text_file_path = text_file_path
        self.start_line = start_line
        self.start_column = start_column
        self.end_line = end_line
        self.end_column = end_column

    def __str__(self):
        return f"{repr(self.text_file_path)}[{self.short_text_desc}]"

    @property
    def short_text_desc(self):
        if self.start_line == self.end_line:
            if self.start_column == self.end_column:
                return f"{self.start_line}:{self.start_column}"
            else:
                return f"{self.start_line}:{self.start_column}-{self.end_column}"
        else:
            return f"{self.start_line}:{self.end_column}-{self.end_line}:{self.end_column}"
