import abc
import typing as t
import json

from . import types
from . import pair
from . import feedback
from . import panic


#
# TODO: implement unification
#

def unify(t1: types.BaseType, t2: types.BaseType) -> "Substitution":
    """
    Returns the most general substitution that would make these types identical when both are rewritten.
    WARNING: 
        types must be checked for infinite-size (aka loops in composites) before-hand-- otherwise, will stack overflow.
    """

    # if already equal, return empty sub
    if t1 == t2:
        return Substitution.empty
    
    # var -> anything else
    if t1.is_var ^ t2.is_var:
        if t1.is_var:
            var_type = t1
            rewritten_type = t2
        else:
            var_type = t2
            rewritten_type = t1

        # TODO: perform an occurs-check here:
        # - ensure 'var_type' is not one of the free variables of 'rewritten_type'
        # - can define a method named 'free_vars' on types that returns the set of free type variables 
        #   recursively
        # cf https://en.wikipedia.org/wiki/Occurs_check

        return Substitution.get({var_type: rewritten_type})


    # composite types => just unify each field recursively.
    elif t1.kind() == t2.kind() and t1.is_composite:
        assert t2.is_composite

        # ensure field names & field counts are identical:
        if t1.field_names != t2.field_names:
            raise_unification_error()

        # generate a substitution by unifying matching fields:
        s = Substitution.empty
        for ft1, ft2 in zip(t1.field_types, t2.field_types):
            s = unify(ft1, ft2).compose(s)
        return s

    # any other case: raise a unification error.
    else:
        raise_unification_error()


def raise_unification_error(t: types.BaseType, u: types.BaseType):
    panic.because(
        panic.ExitCode.TyperError,
        f"UNIFICATION_ERROR: Cannot unify {t} and {u}"
    )


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
    empty: t.Optional["Substitution"] = None

    @staticmethod
    def get(sub_map: t.Dict[types.VarType, types.BaseConcreteType]) -> "Substitution":
        if sub_map:
            return Substitution(sub_map)
        else:
            assert isinstance(Substitution.empty, Substitution)
            return Substitution.empty

    def __init__(
        self, 
        sub_map: t.List[t.Tuple[types.VarType, types.BaseConcreteType]], 
        _suppress_construct_empty_error=False
    ) -> None:
        if not _suppress_construct_empty_error:
            if not sub_map:
                raise ValueError("Cannot construct an empty substitution: use `Substitution.empty` instead.")

        # print("Sub map:", sub_map)
        assert isinstance(sub_map, dict)
        assert all((isinstance(key, types.BaseType) and key.is_var for key, _ in sub_map.items()))
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
        return '{' + ','.join((f"{str(key)}->{str(val)}" for key, val in self.sub_map.items())) + '}'

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
        for cmp_t, replacement_t in self.sub_map.items():
            if cmp_t == t:
                return replacement_t
        else:
            return None


Substitution.empty = Substitution({}, _suppress_construct_empty_error=True)


class InfiniteSizeTypeException(BaseException):
    pass
