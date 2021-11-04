import typing as t

from . import types
from . import typer


class Scheme(object):
    def __init__(self, vars: t.List[types.BoundVarType], body: types.BaseConcreteType) -> None:
        assert all((isinstance(it, types.BoundVarType) for it in vars))
        super().__init__()
        self.vars = vars
        self.body = body

    def instantiate(
        self, 
        opt_actual_args_list: t.Optional[t.List[types.BaseType]]=None
    ) -> t.Tuple[typer.Substitution, types.BaseConcreteType]:
        if opt_actual_args_list is None:
            actual_arg_types = list((types.FreeVarType(f"new({var})") for var in self.vars))
        else:
            actual_arg_types = opt_actual_args_list
            assert len(actual_arg_types) == len(self.vars)

        sub = typer.Substitution(list(zip(
            self.vars,
            actual_arg_types
        )))
        res = sub.rewrite_type(self.body)
        return sub, res

    def __str__(self) -> str:
        return f"({','.join((var.name for var in self.vars))})=>{self.body}"
