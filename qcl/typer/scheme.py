from typing import *
import copy

from qcl import type

from . import substitution


class Scheme(object):
    bound_vars: List[type.identity.TID]
    body_tid: type.identity.TID

    def __init__(self, body_tid: type.identity.TID, bound_var_names: Optional[List[str]] = None):
        super().__init__()
        if bound_var_names is not None:
            self.bound_vars = [type.new_bound_var(var_name) for var_name in bound_var_names]
        else:
            self.bound_vars = []
        self.body_tid = body_tid

    def __str__(self):
        return self.spell()

    def spell(self) -> str:
        body_spelling = type.spelling.of(self.body_tid)

        if self.bound_vars:
            args_text = ', '.join(map(type.spelling.of, self.bound_vars))
            return f"∀ ({args_text}) {body_spelling}"
        else:
            return body_spelling

    def sub_body(self, new_body) -> "Scheme":
        """
        :return: a new `Scheme` instance with the `body` attribute replaced by this argument.
        """
        new_scheme = copy.copy(self)
        new_scheme.body_tid = new_body
        return new_body

    def instantiate(self) -> Tuple[substitution.Substitution, type.identity.TID]:
        if self.bound_vars:
            sub = substitution.Substitution({
                bound_var: type.new_free_var(f"instantiated-free-var")
                for bound_var in self.bound_vars
            })
            return sub, sub.rewrite_type(self.body_tid)
        else:
            return substitution.empty, self.body_tid
