"""
A substitution is a mapping from named type variables to types.
`Substitution` instances are immutable and composable.
"""

from qcl import type

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

    def rewrite_type(self, tid: type.identity.TID, rw_in_progress_tid_set=None) -> type.identity.TID:
        """
        performs substitution on types and their contents/elements.
        :param tid: the type to rewrite after the substitution
        :param rw_in_progress_tid_set: if tid is in this set, its rewrite does not take the substitution.
            - means rewrite already in progress.
            - e.g. consider case where two modules import each other, so each is an element of the other
            - we must still infer infinite types to handle modules, so delay reporting these to basic checks.
        :return: the rewritten type.
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

        t_kind = type.kind.of(tid)

        # variables replaced:
        replacement_tid = self.sub_map.get(tid, None)
        if replacement_tid is not None:
            return replacement_tid

        # atoms:
        primitive_tk_set = {
            type.kind.TK.FreeVar, type.kind.TK.BoundVar,
            type.kind.TK.Unit, type.kind.TK.String,
            type.kind.TK.SignedInt, type.kind.TK.UnsignedInt, type.kind.TK.Float
        }
        if t_kind in primitive_tk_set:
            return tid

        # memory views: ptr, array, slice
        mem_view_tk_set = {
            type.kind.TK.Pointer, type.kind.TK.Array, type.kind.TK.Slice
        }
        if t_kind in mem_view_tk_set:
            replacement_ctor_map = {
                type.kind.TK.Pointer: type.get_ptr_type,
                type.kind.TK.Array: type.get_array_type,
                type.kind.TK.Slice: type.get_slice_type
            }
            mem_view_is_mut = type.mem_window.is_mut(tid)
            return replacement_ctor_map[t_kind](
                self.rewrite_type(type.elem.tid_of_ptd(tid)),
                mem_view_is_mut
            )

        # compounds: tuple, struct, union, enum, module
        compound_tk_set = {
            type.kind.TK.Tuple, type.kind.TK.Struct, type.kind.TK.Union,
            type.kind.TK.Module
        }
        if t_kind in compound_tk_set:
            replacement_elem_tid_list = []
            for element_index in range(type.elem.count(tid)):
                element_tid = type.elem.tid_of_field_ix(tid, element_index)
                replacement_elem_tid = self.rewrite_type(element_tid, rw_in_progress_tid_set=rw_in_progress_tid_set)
                replacement_elem_tid_list.append(replacement_elem_tid)

            if t_kind == type.kind.TK.Tuple:
                return type.get_tuple_type(tuple(replacement_elem_tid_list))
            else:
                replacement_elem_info_tuple = tuple((
                    type.elem.ElemInfo(
                        type.elem.field_name_at_ix(tid, field_index),
                        replacement_field_tid,
                        type.elem.is_type_field_at_field_ix(tid, field_index)
                    )
                    for field_index, replacement_field_tid in enumerate(replacement_elem_tid_list)
                ))

                replacement_ctor_map = {
                    type.kind.TK.Struct: type.get_struct_type,
                    type.kind.TK.Union: type.get_union_type,
                    type.kind.TK.Module: type.new_module_type
                }
                return replacement_ctor_map[t_kind](replacement_elem_info_tuple)

        # functions:
        if t_kind == type.kind.TK.Fn:
            return type.get_fn_type(
                self.rewrite_type(type.elem.tid_of_fn_arg(tid)),
                self.rewrite_type(type.elem.tid_of_fn_ret(tid)),
                type.side_effects.of(tid),
                qcl.typer.memory.of(tid)
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
            f"{type.spelling.of(key)} -> {type.spelling.of(value)}"
            for (key, value) in self.sub_map.items()
        )) + '}'


empty = Substitution()
