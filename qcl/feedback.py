import typing as t


class Loc(object):
    def __init__(self, line_index, col_index) -> None:
        super().__init__()
        self.line_index = line_index
        self.col_index = col_index

    def __str__(self) -> str:
        return f"{self.line_index}:{self.col_index}"

    @property
    def line_num(self):
        return 1 + self.line_index

    @property
    def col_num(self):
        return 1 + self.col_index


class Span(object):
    def __init__(self, first_char_pos: Loc, opt_last_char_pos: t.Optional[Loc] = None) -> None:
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
