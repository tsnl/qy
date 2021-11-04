import typing as t

from . import types
from . import typer


class Scheme(object):
    def __init__(self, vars: t.List[types.BoundVarType], body: types.BaseConcreteType) -> None:
        assert all((isinstance(it, types.BoundVarType) for it in vars))
        super().__init__()
        self.vars = vars
        self.body = body

    def instantiate(self) -> t.Tuple[typer.Substitution, types.BaseConcreteType]:
        sub = typer.Substitution(list(zip(
            self.vars,
            (types.FreeVarType(f"new({var})") for var in self.vars)
        )))
        res = sub.rewrite_type(self.body)
        return sub, res

    def __str__(self) -> str:
        return f"({','.join((var.name for var in self.vars))})=>{self.body}"
