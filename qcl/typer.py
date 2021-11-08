import abc
import typing as t
import sys

from . import panic
from . import config
from . import pair
from . import feedback as fb
from . import types
from . import scheme
from . import ast1
from . import ast2


#
# source file typing: part 1: seeding
#

def seed_one_source_file(sf: ast2.QySourceFile):
    """
    defines global symbols in a context using free variables, then sets it on `x_typer_ctx`
    """

    new_ctx = Context(Context.builtin_root)

    for top_level_stmt in sf.stmt_list:
        seed_one_top_level_stmt(new_ctx, top_level_stmt)

    sf.x_typer_ctx = new_ctx


def seed_one_top_level_stmt(bind_in_ctx: "Context", stmt: ast1.BaseStatement):
    #
    # Handling 'bind' statements:
    #
    
    new_definition = None
    if isinstance(stmt, ast1.Bind1vStatement):
        new_definition = ValueDefinition(
            stmt.loc,
            stmt.name, 
            scheme.Scheme([], types.VarType(f"bind1v:{stmt.name}"))
        )
    elif isinstance(stmt, ast1.Bind1fStatement):
        new_definition = ValueDefinition(
            stmt.loc,
            stmt.name,
            scheme.Scheme([], types.VarType(f"bind1f:{stmt.name}"))
        )
    elif isinstance(stmt, ast1.Bind1tStatement):
        new_definition = ValueDefinition(
            stmt.loc,
            stmt.name,
            scheme.Scheme([], types.VarType(f"bind1t:{stmt.name}"))
        )
    
    if new_definition is not None:
        old_definition = bind_in_ctx.try_define(new_definition)    
        if old_definition is not None:
            panic.because(
                panic.ExitCode.TyperSeedingDoubleBindError,
                f"Symbol {stmt.name} was defined twice:\n"
                f"- first: {old_definition.loc}\n"
                f"- later: {new_definition.loc}",
                opt_loc=stmt.loc
            )
        return

    #
    # Handling 'type' statements:
    #

    if isinstance(stmt, ast1.Type1vStatement):
        # ignore definitions-- but mark as public if export:
        if stmt.is_export_line:
            bind_in_ctx.export_name_set.add(stmt.name)
        return

    #
    # Handling 'const' statements:
    #

    if isinstance(stmt, ast1.ConstStatement):
        for nested_stmt in stmt.body:
            if not isinstance(nested_stmt, ast1.Bind1vStatement):
                panic.because(
                    panic.ExitCode.SyntaxError,
                    "In 'const' block, expected only 'Bind1v' statements",
                    opt_loc=stmt.loc
                )
            seed_one_top_level_stmt(bind_in_ctx, nested_stmt)

        return 

    #
    # All other statements => error
    #

    panic.because(
        panic.ExitCode.TyperSeedingInputError,
        f"Invalid statement in top-level file: {stmt.desc}",
        opt_loc=stmt.loc
    )


#
# source file typing: part II: solving
#

def solve_one_source_file(sf: ast2.QySourceFile):
    sf_top_level_context = sf.x_typer_ctx
    assert isinstance(sf_top_level_context, Context)
    
    for top_level_stmt in sf.stmt_list:
        solve_one_stmt(sf_top_level_context, top_level_stmt)


def solve_one_stmt(ctx: "Context", stmt: "ast1.BaseStatement") -> "Substitution":
    if isinstance(stmt, ast1.Bind1vStatement):
        definition = ctx.try_lookup(stmt.name)
        assert definition is not None
        def_type = definition.scheme.instantiate()
        exp_sub, exp_type = solve_one_exp(ctx, stmt.initializer)
        return unify(def_type, exp_type).compose(exp_sub)
    # elif isinstance(stmt, ast1.Bind1fStatement):
    #     pass
    # elif isinstance(stmt, ast1.Bind1tStatement):
    #     pass
    # elif isinstance(stmt, ast1.Type1vStatement):
    #     pass
    else:
        raise NotImplementedError(f"Don't know how to solve types: {stmt.desc}")


def solve_one_exp(ctx: "Context", exp) -> t.Tuple["Substitution", types.BaseType]:
    if isinstance(exp, ast1.IntExpression):
        return Substitution.empty, types.IntType.get(exp.width_in_bits, not exp.is_unsigned)
    elif isinstance(exp, ast1.FloatExpression):
        return Substitution.empty, types.FloatType.get(exp.width_in_bits)
    elif isinstance(exp, ast1.StringExpression):
        return Substitution.empty, types.StringType.singleton
    # elif isinstance(exp, ast1.IotaExpression):
    #     pass

    raise NotImplementedError(f"Don't know how to solve types: {exp.desc}")

#
# Unification
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

        # perform an occurs-check here:
        # - ensure 'var_type' is not one of the free variables of 'rewritten_type'
        # - can define a method named 'free_vars' on types that returns the set of free type variables 
        #   recursively
        # cf https://en.wikipedia.org/wiki/Occurs_check
        if var_type in rewritten_type.iter_free_vars():
            raise_unification_error(t1, t2, "occurs check failed (see https://en.wikipedia.org/wiki/Occurs_check)")

        return Substitution.get({var_type: rewritten_type})


    # composite types => just unify each field recursively.
    elif t1.kind() == t2.kind() and t1.is_composite:
        assert t2.is_composite

        if t1.has_user_defined_field_names():
            # ensure field names & field counts are identical:
            if t1.field_names != t2.field_names:
                raise_unification_error()
        else:
            # just check field counts (optimization)
            if len(t1.field_names) != len(t2.field_names):
                raise_unification_error()

        # generate a substitution by unifying matching fields:
        s = Substitution.empty
        for ft1, ft2 in zip(t1.field_types, t2.field_types):
            s = unify(ft1, ft2).compose(s)
        return s

    # any other case: raise a unification error.
    else:
        raise_unification_error()


def raise_unification_error(t: types.BaseType, u: types.BaseType, opt_more=None):
    msg_lines = [f"UNIFICATION_ERROR: Cannot unify {t} and {u}"]
    if opt_more is not None:
        assert isinstance(opt_more, str)
        msg_lines.append('\t' + opt_more)
    
    panic.because(
        panic.ExitCode.TyperUnificationError,
        '\n'.join(msg_lines)
    )


#
# Contexts:
#

class Context(object):
    builtin_root: "Context" = None

    def __init__(self, parent=None) -> None:
        super().__init__()
        self.symbol_table = {}
        self.opt_parent = parent
        self.export_name_set = set()

        if config.DEBUG_MODE:
            self.dbg_children = []
            if self.opt_parent is not None:
                self.dbg_children.append(self)

    def try_define(self, definition: "BaseDefinition") -> t.Optional["BaseDefinition"]:
        """
        Defines a fresh symbol in this context, returns 'None'.
        If a symbol already exists by this name, it is left as is and this definition is returned instead.
        """

        opt_existing_definition = self.symbol_table.get(definition.name, None)
        if opt_existing_definition is not None:
            return opt_existing_definition
        else:
            self.symbol_table[definition.name] = definition
            definition.bound_in_ctx = self
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

    def print(self):
        pass


Context.builtin_root = Context()


#
# Definitions:
#

class BaseDefinition(object, metaclass=abc.ABCMeta):
    def __init__(self, loc: fb.ILoc, name: str, scm: scheme.Scheme) -> None:
        super().__init__()
        self.loc = loc
        self.name = name
        self.scheme = scm
        self.bound_in_ctx = None

    @property
    def is_value_definition(self):
        return isinstance(self, ValueDefinition)

    @property
    def is_type_definition(self):
        return isinstance(self, TypeDefinition)

    @property
    def is_public(self):
        assert isinstance(self.bound_in_ctx, Context)
        return self.name in self.bound_in_ctx.export_name_set


class ValueDefinition(BaseDefinition):
    pass
        

class TypeDefinition(BaseDefinition):
    pass


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
            intersecting_key_set = set(s1.sub_map.keys()) & set(s2.sub_map.keys())
            if intersecting_key_set:
                mismatch = False
                for key in intersecting_key_set:
                    s1_t = s1.sub_map[key]
                    s2_t = s2.sub_map[key]
                    if s1_t != s2_t:
                        mismatch = True
                        break

                if mismatch:
                    s1_problem_map = {key: s1.sub_map[key] for key in intersecting_key_set}
                    s2_problem_map = {key: s2.sub_map[key] for key in intersecting_key_set}
                    panic.because(
                        panic.ExitCode.TyperUnificationError,
                        f"Conflicting substitutions detected:"
                        f"\n\t* from set 1: {s1_problem_map}\n\t* from set 2: {s2_problem_map}"
                    )
            
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
