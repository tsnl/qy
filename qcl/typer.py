import abc
import typing as t
import sys
import enum
import textwrap

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

    new_ctx = Context(ContextKind.TopLevelOfSourceFile, Context.builtin_root)

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
            scheme.Scheme([], types.VarType(f"bind1v_{stmt.name}"))
        )
    elif isinstance(stmt, ast1.Bind1fStatement):
        new_definition = ValueDefinition(
            stmt.loc,
            stmt.name,
            scheme.Scheme([], types.VarType(f"bind1f_{stmt.name}"))
        )
    elif isinstance(stmt, ast1.Bind1tStatement):
        new_definition = ValueDefinition(
            stmt.loc,
            stmt.name,
            scheme.Scheme([], types.VarType(f"bind1t_{stmt.name}"))
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
    
    sol_sub = solve_one_block(sf_top_level_context, sf.stmt_list)
    sf.x_typer_ctx.apply_sub_in_place_to_sub_tree(sol_sub)
    print(f"Applying `sol_sub`: {sol_sub}")
    # TODO: apply 'sol_sub' to the whole system before solving deferred constraints
    
    # TODO: solve deferred constraints in a separate pass


def solve_one_block(ctx: "Context", stmt_list: t.List[ast1.BaseStatement]) -> "Substitution":
    sub = Substitution.empty
    for stmt in stmt_list:
        stmt_sub = solve_one_stmt(ctx, stmt)
        sub = stmt_sub.compose(sub)
    return sub


def solve_one_block_in_function(
    ctx: "Context",
    arg_name_type_list: t.List[t.Tuple[str, types.BaseType]],
    statements: t.List[ast1.BaseStatement]
) -> t.Tuple["Substitution", types.BaseType]:
    fn_ctx = Context(ContextKind.FunctionBlock, ctx)
    fn_ctx.local_return_type = types.VarType(f"fn_return")
    
    # defining each formal argument for this function:
    for arg_index, (arg_name, arg_type) in enumerate(arg_name_type_list):
        loc = fb.BuiltinLoc(f"arg({arg_index}):{arg_name}")
        scm = scheme.Scheme([], arg_type)
        fn_ctx.try_define(ValueDefinition(loc, arg_name, scm))

    # solving the block statements:
    #   - any 'return' statements are associated with the nearest 'return_type' attribute
    sub = solve_one_block(fn_ctx, statements)
    
    return sub, fn_ctx.local_return_type


def solve_one_stmt(ctx: "Context", stmt: "ast1.BaseStatement") -> "Substitution":
    if isinstance(stmt, ast1.Bind1vStatement):
        definition = ctx.try_lookup(stmt.name)
        assert definition is not None
        def_sub, def_type = definition.scheme.instantiate()
        exp_sub, exp_type = solve_one_exp(ctx, stmt.initializer)
        return unify(def_type, exp_type).compose(exp_sub).compose(def_sub)
    elif isinstance(stmt, ast1.Bind1fStatement):
        arg_type_list = [
            types.VarType(f"arg{arg_index}:{arg_name}")
            for arg_index, arg_name in enumerate(stmt.args)
        ]
        arg_name_type_list = list(zip(stmt.args, arg_type_list))
        ret_sub, ret_type = solve_one_block_in_function(ctx, arg_name_type_list, stmt.body)
        proc_type = types.ProcedureType.new(arg_type_list, ret_type)
        def_sub, def_type = ctx.try_lookup(stmt.name).scheme.instantiate()
        return unify(proc_type, def_type).compose(def_sub).compose(ret_sub)
    elif isinstance(stmt, ast1.Bind1tStatement):
        definition = ctx.try_lookup(stmt.name)
        assert definition is not None
        def_sub, def_type = definition.scheme.instantiate()
        ts_sub, ts_type = solve_one_type_spec(ctx, stmt.initializer)
        return unify(def_type, ts_type).compose(ts_sub).compose(def_sub)
    elif isinstance(stmt, ast1.Type1vStatement):
        definition = ctx.try_lookup(stmt.name)
        t_sub, t = definition.scheme.instantiate()
        ts_sub, ts_type = solve_one_type_spec(ctx, stmt.ts)
        return unify(t, ts_type).compose(ts_sub).compose(t_sub)
    elif isinstance(stmt, ast1.ConstStatement):
        sub = Substitution.empty
        for const_bind_stmt in stmt.body:
            assert isinstance(const_bind_stmt, ast1.Bind1vStatement)
            definition = ctx.try_lookup(const_bind_stmt.name)
            assert definition is not None
            const_sub, const_type = definition.scheme.instantiate()
            sub = const_sub.compose(sub)
            # TODO: check the constant's type
        return sub
    elif isinstance(stmt, ast1.ReturnStatement):
        if ctx.return_type is None:
            panic.because(
                panic.ExitCode.SyntaxError,
                "Cannot 'return' outside a function block",
                opt_loc=stmt.loc
            )
        ret_exp_sub, ret_exp_type = solve_one_exp(ctx, stmt.returned_exp)
        return unify(ret_exp_type, ctx.return_type).compose(ret_exp_sub)
    else:
        raise NotImplementedError(f"Don't know how to solve types: {stmt.desc}")


def solve_one_exp(ctx: "Context", exp: ast1.BaseExpression) -> t.Tuple["Substitution", types.BaseType]:
    if isinstance(exp, ast1.IdRefExpression):
        found_definition = ctx.try_lookup(exp.name)
        if found_definition is None:
            panic.because(
                panic.ExitCode.TyperSolverUndefinedIdError,
                f"Value identifier {exp.name} used, but not defined or declared",
                opt_loc=exp.loc
            )
        sub, id_type = found_definition.scheme.instantiate()
        return sub, id_type
    elif isinstance(exp, ast1.IntExpression):
        return Substitution.empty, types.IntType.get(exp.width_in_bits, not exp.is_unsigned)
    elif isinstance(exp, ast1.FloatExpression):
        return Substitution.empty, types.FloatType.get(exp.width_in_bits)
    elif isinstance(exp, ast1.StringExpression):
        return Substitution.empty, types.StringType.singleton
    elif isinstance(exp, ast1.ConstructorExpression):
        made_ts_sub, made_type = solve_one_type_spec(ctx, exp.made_ts)
        args_sub = Substitution.empty
        initializer_type_list = []
        for initializer_arg_exp in exp.initializer_list:
            initializer_arg_sub, initializer_arg_type = solve_one_exp(initializer_arg_exp)
            args_sub = initializer_arg_sub.compose(args_sub)
            initializer_type_list.append(initializer_arg_type)
        # TODO: check the arguments against the made type, maybe using a deferred query.
        sub = args_sub.compose(made_ts_sub)
        return sub, made_type
    elif isinstance(exp, ast1.UnaryOpExpression):
        # TODO: use a deferred query to resolve this.
        raise NotImplementedError("UnaryOpExpression")
    elif isinstance(exp, ast1.BinaryOpExpression):
        # TODO: use a deferred query to resolve this.
        raise NotImplementedError("BinaryOpExpression")
    elif isinstance(exp, ast1.ProcCallExpression):
        # collecting actual procedure type information:
        # type based on how the procedure is used, derived from 'actual' arguments and 'actual' return type
        all_arg_sub = Substitution.empty
        arg_type_list = []
        for arg_exp in exp.arg_exps:
            arg_sub, arg_type = solve_one_exp(ctx, arg_exp)
            arg_type_list.append(arg_type)
            all_arg_sub = arg_sub.compose(all_arg_sub)
        proxy_ret_type = types.VarType(f"proc_call_ret")
        actual_proc_type = types.ProcedureType.new(arg_type_list, proxy_ret_type)
        
        # collecting formal procedure type information:
        # type based on how the procedure was defined in this context:
        formal_proc_sub, formal_proc_type = solve_one_exp(ctx, exp.proc)

        # unifying, returning:
        sub = unify(formal_proc_type, actual_proc_type).compose(formal_proc_sub).compose(all_arg_sub)
        return sub, proxy_ret_type
    elif isinstance(exp, ast1.IotaExpression):
        raise NotImplementedError("IotaExpression")
    else:
        raise NotImplementedError(f"Don't know how to solve types: {exp.desc}")


def solve_one_type_spec(ctx: "Context", ts: "ast1.BaseTypeSpec") -> t.Tuple["Substitution", types.BaseType]:
    if isinstance(ts, ast1.BuiltinPrimitiveTypeSpec):
        return Substitution.empty, {
            ast1.BuiltinPrimitiveTypeIdentity.Float32: types.FloatType.get(32),
            ast1.BuiltinPrimitiveTypeIdentity.Float64: types.FloatType.get(64),
            ast1.BuiltinPrimitiveTypeIdentity.Int8: types.IntType.get(8, is_signed=True),
            ast1.BuiltinPrimitiveTypeIdentity.Int16: types.IntType.get(16, is_signed=True),
            ast1.BuiltinPrimitiveTypeIdentity.Int32: types.IntType.get(32, is_signed=True),
            ast1.BuiltinPrimitiveTypeIdentity.Int64: types.IntType.get(64, is_signed=True),
            ast1.BuiltinPrimitiveTypeIdentity.Bool: types.IntType.get(1, is_signed=False),
            ast1.BuiltinPrimitiveTypeIdentity.UInt8: types.IntType.get(8, is_signed=False),
            ast1.BuiltinPrimitiveTypeIdentity.UInt16: types.IntType.get(16, is_signed=False),
            ast1.BuiltinPrimitiveTypeIdentity.UInt32: types.IntType.get(32, is_signed=False),
            ast1.BuiltinPrimitiveTypeIdentity.UInt64: types.IntType.get(64, is_signed=False),
            ast1.BuiltinPrimitiveTypeIdentity.String: types.StringType.singleton,
            ast1.BuiltinPrimitiveTypeIdentity.Void: types.VoidType.singleton
        }[ts.identity]
    elif isinstance(ts, ast1.IdRefTypeSpec):
        found_definition = ctx.try_lookup(ts.name)
        if found_definition is None:
            panic.because(
                panic.ExitCode.TyperSolverUndefinedIdError,
                f"Undefined ID used: {ts.name}",
                opt_loc=ts.loc
            )
        sub, def_type = found_definition.scheme.instantiate()
        return sub, def_type
    elif isinstance(ts, ast1.ProcSignatureTypeSpec):
        all_args_sub = Substitution.empty
        all_arg_types = []
        for opt_arg_name, arg_type in ts.args_list:
            arg_sub, arg_type = solve_one_type_spec(ctx, arg_type)
            all_args_sub = arg_sub.compose(all_args_sub)
            all_arg_types.append(arg_type)
        ret_sub, ret_type = solve_one_type_spec(ctx, ts.ret_ts)
        sub = ret_sub.compose(all_args_sub)
        return sub, types.ProcedureType.new(all_arg_types, ret_type)
    elif isinstance(ts, ast1.AdtTypeSpec):
        sub = Substitution.empty
        fields = []
        for field_name, field_ts in ts.fields_list:
            assert field_name is not None
            field_sub, field_type  = solve_one_type_spec(ctx, field_ts)
            sub = field_sub.compose(sub)
            fields.append((field_name, field_type))
        if ts.linear_op == ast1.LinearTypeOp.Product:
            return sub, types.StructType(fields)
        elif ts.linear_op == ast1.LinearTypeOp.Sum:
            return sub, types.UnionType(fields)
        else:
            raise NotImplementedError(f"Unknown LinearTypeOp: {ts.linear_op.name}")
    else:
        raise NotImplementedError(f"Don't know how to solve type-spec: {ts.desc}")


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
    
    # var -> anything else (including var)
    if t1.is_var or t2.is_var:
        if t1.is_var and t2.is_var:
            # in this case, want a consistent way to eliminate variables independently of the order of arguments 
            # received.
            # We choose (arbitrarily) to eliminate values with a higher `id`
            if id(t1) < id(t2):
                var_type = t2
                replacement_type = t1
            else:
                assert id(t1) > id(t2)
                var_type = t1
                replacement_type = t2
        elif t1.is_var:
            var_type = t1
            replacement_type = t2
        else:
            var_type = t2
            replacement_type = t1

        # perform an occurs-check here:
        # - ensure 'var_type' is not one of the free variables of 'rewritten_type'
        # - can define a method named 'free_vars' on types that returns the set of free type variables 
        #   recursively
        # cf https://en.wikipedia.org/wiki/Occurs_check
        if var_type in replacement_type.iter_free_vars():
            raise_unification_error(t1, t2, "occurs check failed (see https://en.wikipedia.org/wiki/Occurs_check)")

        return Substitution.get({var_type: replacement_type})


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
        raise_unification_error(t1, t2)


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

class ContextKind(enum.Enum):
    BuiltinRoot = enum.auto()
    TopLevelOfSourceFile = enum.auto()
    FunctionArgs = enum.auto()
    FunctionBlock = enum.auto()
    

class Context(object):
    builtin_root: "Context" = None

    def __init__(self, kind: ContextKind, parent: t.Optional["Context"]) -> None:
        super().__init__()
        self.kind = kind
        self.symbol_table = {}
        self.opt_parent = parent
        self.export_name_set = set()
        self.local_return_type = None

        self.children = []
        if self.opt_parent is not None:
            self.opt_parent.children.append(self)

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

    @property
    def return_type(self):
        if self.local_return_type is not None:
            return self.local_return_type
        elif self.opt_parent is not None:
            return self.opt_parent.return_type
        else:
            return None

    def print(self):
        self.print_impl(0)
        print()

    def print_impl(self, indent_count: int):
        indent = '  ' * indent_count
        lines = [f"+ {self.kind.name}"]
        for sym_name, sym_definition in self.symbol_table.items():
            if isinstance(sym_definition, ValueDefinition):
                def_sub, def_type = sym_definition.scheme.instantiate()
                line = f"  - {sym_name}: {def_type} [public={sym_definition.is_public}]"
            elif isinstance(sym_definition, TypeDefinition):
                def_sub, def_type = sym_definition.scheme.instantiate()
                line = f"  - {sym_name} = {def_type} [public={sym_definition.is_public}]"
            else:
                raise NotImplementedError("Printing unknown definition")
            lines.append(line)
    
        for child_context in self.children:
            child_context.print_impl(1+indent_count)

        for line in lines:
            print(indent, line, sep='')

    def apply_sub_in_place_to_sub_tree(self, sub: "Substitution"):
        # applying to 'self'
        for def_obj in self.symbol_table.values():
            assert isinstance(def_obj, BaseDefinition)
            def_obj.scheme = sub.rewrite_scheme(def_obj.scheme)

        # applying to 'self.children'
        for child_ctx in self.children:
            child_ctx.apply_sub_in_place_to_sub_tree(sub)



Context.builtin_root = Context(ContextKind.BuiltinRoot, None)


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
        sub_map: t.Dict[types.VarType, types.BaseConcreteType], 
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

    def compose(self, applied_first: "Substitution") -> "Substitution":
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
            # always preserve sub in s2 over s1 if conflict occurs.
            return Substitution.get(sub_map=(s1_sub_map | s2_sub_map))

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
        opt_replacement_t = self._get_replacement_type_for(t)
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

    def _get_replacement_type_for(self, t):
        return self.sub_map.get(t, t)

    def rewrite_scheme(self, s: scheme.Scheme) -> scheme.Scheme:
        if s.vars:
            # NOTE: any bound vars mapped in this substitution must be removed from the substitution, since these 
            # variables must be free in the body of the scheme to be substituted out by instantiation.
            # If we rewrote these bound vars, then they would not be unique to each instantiation.
            new_sub_map = {var: self.sub_map[var] for var in s.vars}
            new_sub = Substitution.get(new_sub_map)
        else:
            new_sub = self

        return scheme.Scheme(s.vars, new_sub.rewrite_type(s.body))


Substitution.empty = Substitution({}, _suppress_construct_empty_error=True)


class InfiniteSizeTypeException(BaseException):
    pass
