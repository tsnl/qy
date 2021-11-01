import abc
import typing as t


class ILoc(object, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __str__(self):
        pass


class BuiltinLoc(ILoc):
    def __init__(self, desc: str):
        super().__init__()
        self.desc = desc

    def __str__(self):
        return f"<BuiltinLoc:{self.desc}>"


class FileLoc(ILoc):
    def __init__(self, file_path: str, file_region: "BaseFileRegion"):
        super().__init__()
        self.file_path = file_path
        self.file_region = file_region

    def __str__(self):
        return f"{self.file_path}:{self.file_region}"


class BaseFileRegion(object, metaclass=abc.ABCMeta):
    def __init__(self):
        super().__init__()

    @abc.abstractmethod
    def __str__(self):
        pass


class FilePos(BaseFileRegion):
    def __init__(self, line_index, col_index) -> None:
        super().__init__()
        self.line_index = line_index
        self.col_index = col_index

    def __str__(self) -> str:
        return f"{self.line_num}:{self.col_num}"

    @property
    def line_num(self):
        return 1 + self.line_index

    @property
    def col_num(self):
        return 1 + self.col_index


class FileSpan(BaseFileRegion):
    def __init__(self, first_char_pos: FilePos, opt_last_char_pos: t.Optional[FilePos] = None) -> None:
        super().__init__()
        self.first_pos = first_char_pos
        self.last_pos = first_char_pos if opt_last_char_pos is None else opt_last_char_pos

    def __str__(self) -> str:
        if self.first_pos.line_num == self.last_pos.line_num:
            if self.first_pos.col_num == self.last_pos.col_num:
                return f"{self.first_pos}"
            else:
                return f"{self.first_pos.line_num}:{self.first_pos.line_num}-{self.last_pos.line_num}"
        else:
            return f"{self.first_pos}-{self.last_pos}"
