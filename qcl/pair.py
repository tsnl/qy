import typing as t


List = t.Optional["Pair"]


class Pair(object):
    def __init__(self, car: object, cdr: t.Optional["Pair"]) -> None:
        super().__init__()
        self.car = car
        self.cdr = cdr


def cons(car: object, cdr: t.Optional[Pair]) -> Pair:
    return Pair(car, cdr)


def list_contains(l: List, v: object) -> bool:
    if l is None:
        return False
    elif l.car == v:
        return True
    elif l.cdr is not None:
        return list_contains(l.cdr, v)
    else:
        return False

