import typing as t
import copy

from qcl import types

from . import substitution
from . import unifier


class Scheme(object):
    bound_vars: t.List[types.identity.TID]
    bound_var_map: t.Dict[str, types.identity.TID]
    body_tid: types.identity.TID
    def_context: t.Optional[t.Any]      # actually a context
    all_bound_var_map: t.Optional[t.Dict[str, types.identity.TID]]

    def __init__(
            self,
            body_tid: types.identity.TID,
            bound_var_names: t.Optional[t.List[str]] = None
    ):
        super().__init__()
        if bound_var_names is not None:
            self.bound_vars = [types.new_bound_var(var_name) for var_name in bound_var_names]
            self.bound_var_map = {
                var_name: var
                for var_name, var in zip(bound_var_names, self.bound_vars)
            }
        else:
            self.bound_vars = []
            self.bound_var_map = {}

        self.body_tid = body_tid
        self.def_context = None
        self.all_bound_var_map = self.bound_var_map

    def __str__(self):
        return self.spell()

    def spell(self) -> str:
        body_spelling = types.spelling.of(self.body_tid)

        if self.bound_vars:
            args_text = ', '.join(map(types.spelling.of, self.bound_vars))
            return f"∀ ({args_text}) {body_spelling}"
        else:
            return body_spelling

    def sub_body(self, new_body) -> "Scheme":
        """
        :return: a new `Scheme` instance with the `body` attribute replaced by this argument.
        """
        new_scheme = copy.copy(self)
        new_scheme.body_tid = new_body
        return new_scheme

    def shallow_instantiate(self):
        sub, ret_tid = self.help_instantiate(self.bound_var_map, is_deep_not_shallow=False)
        return sub, ret_tid

    def deep_instantiate(self):
        # return self.help_instantiate(self.all_bound_var_map, is_deep_not_shallow=True)
        sub, ret_tid = self.help_instantiate(self.bound_var_map, is_deep_not_shallow=True)
        return sub, ret_tid

    def help_instantiate(
            self, bound_var_map, is_deep_not_shallow=False
    ) -> t.Tuple[substitution.Substitution, types.identity.TID]:
        """
        substitutes bound vars with fresh free-vars.
        :return: a substitution (including bound var mappings) and the instantiated body
        """

        return_formal_var_mappings = is_deep_not_shallow

        # we want to sub (substitute) all BoundVar occurrences in the spelling of `body` by
        #   - the actual argument if provided, otherwise...
        #   - a fresh FreeVar that can be eliminated by inference

        if bound_var_map:
            # computing all bound vars:
            # generating a sub to replace each bound var by a fresh free-var (to be eliminated):
            sub = substitution.Substitution({
                bound_var: types.new_free_var(f"template_instantiated_free_var.{bound_var_name}")
                for bound_var_name, bound_var in bound_var_map.items()
            })

            # NOTE: what about other (i.e. value) template args? How do they get unified?
            #   - they are unified like a function call in the instantiation logic in `inference`.

            # rewriting the types's body using this sub (INSTANTIATION):
            #   - note that we WANT to map formal args to instantiated ones.
            instantiated_tid = sub.rewrite_type(self.body_tid)

            # occasionally, the user may require which free vars were used to instantiate bound ones.
            #   - e.g., when the user supplies explicit arguments.
            # otherwise, we delete these mappings from the sub to avoid substituting the origin context at the end
            # globally.
            if not return_formal_var_mappings:
                sub = sub.get_scheme_body_sub_without_bound_vars(self, replace_deeply=is_deep_not_shallow)

            # returning the sub (INCLUDING SUBS FOR BOUND VARS)
            return sub, instantiated_tid
        else:
            return substitution.empty, self.body_tid

    def init_def_context(self, def_context):
        """
        This function is called when a definition is bound to a context.
        It is a kind of 'lazy initialization' function.
        :param def_context: the context in which this scheme is instantiated.
        :return:
        """

        assert def_context is not None
        self.def_context = def_context
        self.all_bound_var_map = self.bound_var_map | self.def_context.global_type_template_arg_tid_map
