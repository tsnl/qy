from typing import *
import copy

from qcl import type


class Scheme(object):
    bound_vars: List[type.identity.TID]
    body: type.identity.TID

    def __init__(self, bound_var_names: List[str], body_tid: type.identity.TID):
        super().__init__()
        self.bound_vars = [type.new_bound_var(var_name) for var_name in bound_var_names]
        self.body = body_tid

    def spell(self):
        body_spelling = type.spelling.of(self.body)

        if self.bound_vars:
            args_text = ', '.join(map(type.spelling.of, self.bound_vars))
            return f"∀ ({args_text}) {body_spelling}"
        else:
            return body_spelling

    def sub_body(self, new_body):
        """
        :return: a new `Scheme` instance with the `body` attribute replaced by this argument.
        """
        new_scheme = copy.copy(self)
        new_scheme.body = new_body
        return new_body
