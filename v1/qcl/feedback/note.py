import abc

from .loc import ILoc


class INote(object, metaclass=abc.ABCMeta):
    def __init__(self, caption):
        super().__init__()
        self.caption = caption

    def __str__(self):
        return self.caption


class LocNote(INote):
    def __init__(self, caption, loc: "ILoc"):
        super().__init__(caption)
        self.loc = loc

    def __str__(self):
        return f"{super().__str__()}\ncheck [{str(self.loc)}]"
