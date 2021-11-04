import abc
import typing as t
import json

from . import types
from . import pair


#
# Contexts:
#

class Context(object):
    def __init__(self, opt_parent=None) -> None:
        super().__init__()
        self.symbol_table = {}
        self.opt_parent = opt_parent

    def try_define(self, name: str, definition: "BaseDefinition") -> t.Optional["BaseDefinition"]:
        """
        Defines a fresh symbol in this context, returns 'None'.
        If a symbol already exists by this name, it is left as is and this definition is returned instead.
        """

        opt_existing_definition = self.symbol_table.get(name, None)
        if opt_existing_definition is not None:
            return opt_existing_definition
        else:
            self.symbol_table[name] = definition
            return None

    def try_lookup(self, name: str) -> t.Optional["BaseDefinition"]:
        """
        Finds a symbol of this name and returns its Definition.
        If the symbol is not defined, returns 'None' instead.
        """
        opt_existing_definition = self.symbol_table.get(name, None)
        if opt_existing_definition is not None:
            return opt_existing_definition
        elif self.opt_parent is not None:
            return self.opt_parent.try_lookup(name)
        else:
            return None


#
# Definitions:
#

class BaseDefinition(object, metaclass=abc.ABCMeta):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name


class ValueDefinition(BaseDefinition):
    def __init__(self, name: str, value_type: types.BaseType) -> None:
        super().__init__(name, value_type)
        self.value_type = self.related_type


class TypeDefinition(BaseDefinition):
    def __init__(self, name: str, bound_type: types.BaseType) -> None:
        super().__init__(name, bound_type)
        self.bound_type = self.related_type


#
# Substitutions:
#

class Substitution(object):
    empty = None

    def __init__(self, sub_map: t.List[t.Tuple[types.BaseVarType, types.BaseConcreteType]]) -> None:
        assert isinstance(sub_map, list)
        assert all((isinstance(key, types.BaseType) and key.is_var for key, _ in zip(*sub_map)))
        super().__init__()
        self.sub_map = sub_map

    def compose(self, applied_first: "Substitution"):
        # composeSubst s1 s2 = Map.union (Map.map (applySubst s1) s2) s1

        s1 = self
        s2 = applied_first

        if s1 is Substitution.empty:
            return s2
        elif s2 is Substitution.empty:
            return s1
        else:
            s1_sub_map = s1.sub_map
            s2_sub_map = {
                key: s1.rewrite_type(value)
                for key, value in s2.sub_map.items()
            }
            return Substitution(sub_map=(s1_sub_map | s2_sub_map))

    def __str__(self) -> str:
        return json.dumps({str(key): str(val) for key, val in self.sub_map})

    def rewrite_type(self, t: types.BaseType) -> types.BaseType:
        return self._rewrite_type(t, None)

    def _rewrite_type(self, t: types.BaseType, rw_in_progress_pair_list: pair.List) -> types.BaseType:
        assert isinstance(t, types.BaseType)

        if pair.list_contains(rw_in_progress_pair_list, t):
            raise InfiniteSizeTypeException()
    
        rw_in_progress_pair_list = pair.cons(t, rw_in_progress_pair_list)

        # BoundVar in `sub_map` -> replacement
        # FreeVar in `sub_map` -> replacement
        opt_replacement_t = self._get(t)
        if opt_replacement_t is not None:
            return opt_replacement_t
        
        # Atoms: returned as is
        if isinstance(t, types.AtomicConcreteType):
            return t
        
        # Composite types: map rewrite on each component
        if isinstance(t, types.BaseCompositeType):
            return t.copy_with_elements([
                (element_name, self._rewrite_type(element_type, rw_in_progress_pair_list))
                for element_name, element_type in t.fields
            ])
        
        # Otherwise, just return the type as is:
        assert t.is_atomic or t.is_var
        return t

    def _get(self, t):
        for cmp_t, replacement_t in self.sub_map:
            if cmp_t == t:
                return replacement_t
        else:
            return None


class InfiniteSizeTypeException(BaseException):
    pass
