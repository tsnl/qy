"""
A substitution is a mapping from named types variables to types.
`Substitution` instances are immutable and composable.
"""

from qcl import types

from . import scheme
from . import context


class Substitution(object):
    """
    `Substitution` instances are immutable mappings from variables to other types.
    """

    def __init__(self, sub_map=None):
        super().__init__()
        if sub_map is None:
            # only used to instantiate singleton `empty` instance
            self.sub_map = {}
        else:
            self.sub_map = sub_map

    def get_scheme_body_sub_without_bound_vars(self, s: "scheme.Scheme", replace_deeply=False):
        if self is empty:
            return self

        if s.all_bound_var_map:
            sub_without_bound_vars_map = {}
            if replace_deeply:
                all_bound_var_set = set(s.all_bound_var_map.values())
            else:
                all_bound_var_set = set(s.bound_var_map.values())

            for k, v in self.sub_map.items():
                if k not in all_bound_var_set:
                    sub_without_bound_vars_map[k] = v
            sub_without_bound_vars = Substitution(sub_without_bound_vars_map)
        else:
            sub_without_bound_vars = self

        return sub_without_bound_vars

    def rewrite_scheme(self, s: "scheme.Scheme") -> "scheme.Scheme":
        assert isinstance(s, scheme.Scheme)
        sub_without_bound_vars = self.get_scheme_body_sub_without_bound_vars(s)
        new_body = sub_without_bound_vars.rewrite_type(s.body_tid)
        return s.sub_body(new_body)

    def rewrite_type(self, tid: types.identity.TID, rw_in_progress_tid_set=None) -> types.identity.TID:
        """
        performs substitution on types and their contents/elements.
        :param tid: the types to rewrite after the substitution
        :param rw_in_progress_tid_set: if tid is in this set, its rewrite does not take the substitution.
            - means rewrite already in progress.
            - e.g. consider case where two modules import each other, so each is an element of the other
            - we must still infer infinite types to handle modules, so delay reporting these to basic checks.
        :return: the rewritten types.
        """
        # TODO: test to see if ignoring rewrites in cycles results in incorrect substitution application.
        #   - for now, the incorrect sub always results in a free-var that is always eliminated
        #   - janky at best

        if rw_in_progress_tid_set is None:
            rw_in_progress_tid_set = set()
        elif tid in rw_in_progress_tid_set:
            return tid
        else:
            # FIXME: rather than copying rw_in_progress_tid_set, use a linked list of visited TIDs
            rw_in_progress_tid_set = set(rw_in_progress_tid_set)
            rw_in_progress_tid_set.add(tid)

        t_kind = types.kind.of(tid)

        # variables replaced:
        replacement_tid = self.sub_map.get(tid, None)
        if replacement_tid is not None:
            return replacement_tid

        # atoms:
        primitive_tk_set = {
            types.kind.TK.FreeVar, types.kind.TK.BoundVar,
            types.kind.TK.Unit, types.kind.TK.String,
            types.kind.TK.SignedInt, types.kind.TK.UnsignedInt, types.kind.TK.Float
        }
        if t_kind in primitive_tk_set:
            return tid

        # memory views: ptr, array, slice
        mem_view_tk_set = {
            types.kind.TK.Pointer, types.kind.TK.Array, types.kind.TK.Slice
        }
        if t_kind in mem_view_tk_set:
            replacement_ctor_map = {
                types.kind.TK.Pointer: types.get_ptr_type,
                types.kind.TK.Array: types.get_array_type,
                types.kind.TK.Slice: types.get_slice_type
            }
            mem_view_is_mut = types.mem_window.is_mut(tid)
            return replacement_ctor_map[t_kind](
                self.rewrite_type(types.elem.tid_of_ptd(tid)),
                mem_view_is_mut
            )

        # compounds: tuple, struct, union, enum, module
        compound_tk_set = {
            types.kind.TK.Tuple, types.kind.TK.Struct, types.kind.TK.Union,
            types.kind.TK.Module
        }
        if t_kind in compound_tk_set:
            replacement_elem_tid_list = []
            for element_index in range(types.elem.count(tid)):
                element_tid = types.elem.tid_of_field_ix(tid, element_index)
                replacement_elem_tid = self.rewrite_type(element_tid, rw_in_progress_tid_set=rw_in_progress_tid_set)
                replacement_elem_tid_list.append(replacement_elem_tid)

            if t_kind == types.kind.TK.Tuple:
                return types.get_tuple_type(tuple(replacement_elem_tid_list))
            else:
                replacement_elem_info_tuple = tuple((
                    types.elem.ElemInfo(
                        types.elem.field_name_at_ix(tid, field_index),
                        replacement_field_tid,
                        types.elem.is_type_field_at_field_ix(tid, field_index)
                    )
                    for field_index, replacement_field_tid in enumerate(replacement_elem_tid_list)
                ))

                replacement_ctor_map = {
                    types.kind.TK.Struct: types.get_struct_type,
                    types.kind.TK.Union: types.get_union_type,
                    types.kind.TK.Module: types.new_module_type
                }
                return replacement_ctor_map[t_kind](replacement_elem_info_tuple)

        # functions:
        if t_kind == types.kind.TK.Fn:
            return types.get_fn_type(
                self.rewrite_type(types.elem.tid_of_fn_arg(tid)),
                self.rewrite_type(types.elem.tid_of_fn_ret(tid)),
                types.side_effects.of(tid)
            )

        # unknown:
        raise NotImplementedError(f"Substitution.apply_to_type for TK {t_kind}")

    def rewrite_contexts_everywhere(self, ctx: "context.Context"):
        """
        updates all frames in a context in-place.
        :param ctx: the context manager to update IN-PLACE.
        """

        if self is not empty:
            ctx.map_everyone(self.help_rewrite_single_context_defs)

    def rewrite_contexts_downward(self, ctx: "context.Context"):
        ctx.map_descendants(self.help_rewrite_single_context_defs)

    def help_rewrite_single_context_defs(self, frame: "context.Context"):
        for def_name, def_obj in frame.symbol_table.items():
            def_obj.scheme = self.rewrite_scheme(def_obj.scheme)
            assert isinstance(def_obj.scheme, scheme.Scheme)

    def compose(self, applied_first: "Substitution"):
        # composeSubst s1 s2 = Map.union (Map.map (applySubst s1) s2) s1

        s1 = self
        s2 = applied_first

        if s1 is empty:
            return s2
        elif s2 is empty:
            return s1
        else:
            s1_sub_map = s1.sub_map
            s2_sub_map = {
                key: s1.rewrite_type(value)
                for key, value in s2.sub_map.items()
            }
            return Substitution(sub_map=(s1_sub_map | s2_sub_map))

    def __str__(self):
        return '{' + ', '.join((
            f"{types.spelling.of(key)} -> {types.spelling.of(value)}"
            for (key, value) in self.sub_map.items()
        )) + '}'


empty = Substitution()
