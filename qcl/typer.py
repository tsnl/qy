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
            Scheme([], types.VarType(f"bind1v_{stmt.name}"))
        )
    elif isinstance(stmt, ast1.Bind1fStatement):
        new_definition = ValueDefinition(
            stmt.loc,
            stmt.name,
            Scheme([], types.VarType(f"bind1f_{stmt.name}"))
        )
    elif isinstance(stmt, ast1.Bind1tStatement):
        new_definition = ValueDefinition(
            stmt.loc,
            stmt.name,
            Scheme([], types.VarType(f"bind1t_{stmt.name}"))
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
# source file typing: part II: modelling
#

def model_one_source_file(sf: ast2.QySourceFile, dto_list: "DTOList"):
    sf_top_level_context = sf.x_typer_ctx
    assert isinstance(sf_top_level_context, Context)
    
    sol_sub = model_one_block(sf_top_level_context, sf.stmt_list, dto_list, is_top_level=True)
    # sf.x_typer_ctx.apply_sub_in_place_to_sub_tree(sol_sub)
    # print(f"Applying `sol_sub`: {sol_sub}")
    
    # TODO: solve deferred constraints in a separate pass


def model_one_block(
    ctx: "Context", 
    stmt_list: t.List[ast1.BaseStatement], 
    dto_list: "DTOList", 
    is_top_level=False
) -> "Substitution":
    sub = Substitution.empty
    for stmt in stmt_list:
        stmt_sub = model_one_statement(ctx, stmt, dto_list)
        sub = stmt_sub.compose(sub)
        if is_top_level:
            ctx.apply_sub_in_place_to_sub_tree(sub)
            dto_list.update(sub)
    return sub


def model_one_block_in_function(
    ctx: "Context",
    arg_name_type_list: t.List[t.Tuple[str, types.BaseType]],
    statements: t.List[ast1.BaseStatement],
    dto_list: "DTOList"
) -> t.Tuple["Substitution", types.BaseType]:
    fn_ctx = Context(ContextKind.FunctionBlock, ctx)
    fn_ctx.local_return_type = types.VarType(f"fn_return")
    
    # defining each formal argument for this function:
    for arg_index, (arg_name, arg_type) in enumerate(arg_name_type_list):
        loc = fb.BuiltinLoc(f"arg({arg_index}):{arg_name}")
        scm = Scheme([], arg_type)
        fn_ctx.try_define(ValueDefinition(loc, arg_name, scm))

    # solving the block statements:
    #   - any 'return' statements are associated with the nearest 'return_type' attribute
    sub = model_one_block(fn_ctx, statements, dto_list, is_top_level=False)
    
    return sub, fn_ctx.local_return_type


def model_one_statement(ctx: "Context", stmt: "ast1.BaseStatement", dto_list: "DTOList") -> "Substitution":
    if isinstance(stmt, ast1.Bind1vStatement):
        exp_sub, exp_type = model_one_exp(ctx, stmt.initializer, dto_list)
        if ctx.kind == ContextKind.TopLevelOfSourceFile:
            # definition is already seeded-- just retrieve and unify.
            definition = ctx.symbol_table[stmt.name]
            def_sub, def_type = definition.scheme.instantiate()
            last_sub = def_sub.compose(exp_sub)
            return unify(
                last_sub.rewrite_type(def_type), 
                last_sub.rewrite_type(exp_type),
                opt_loc=stmt.loc
            ).compose(last_sub)
        else:
            # try to create a local definition using the expression type.
            definition = ValueDefinition(stmt.loc, stmt.name, Scheme([], exp_type))
            conflicting_def = ctx.try_define(definition)
            if conflicting_def is not None:
                panic.because(
                    panic.ExitCode.TyperModelerRedefinedIdError,
                    f"Local value identifier {stmt.name} bound twice:\n"
                    f"first: {conflicting_def.loc}\n"
                    f"later: {definition.loc}"
                )
            else:
                def_sub, def_type = definition.scheme.instantiate()
                return def_sub
    elif isinstance(stmt, ast1.Bind1fStatement):
        arg_type_list = [
            types.VarType(f"arg{arg_index}:{arg_name}")
            for arg_index, arg_name in enumerate(stmt.args)
        ]
        arg_name_type_list = list(zip(stmt.args, arg_type_list))
        ret_sub, ret_type = model_one_block_in_function(ctx, arg_name_type_list, stmt.body, dto_list)
        proc_type = types.ProcedureType.new(arg_type_list, ret_type)
        def_sub, def_type = ctx.try_lookup(stmt.name).scheme.instantiate()
        last_sub = def_sub.compose(ret_sub)
        return unify(
            last_sub.rewrite_type(proc_type), 
            last_sub.rewrite_type(def_type),
            opt_loc=stmt.loc
        ).compose(last_sub)
    elif isinstance(stmt, ast1.Bind1tStatement):
        definition = ctx.try_lookup(stmt.name)
        assert definition is not None
        def_sub, def_type = definition.scheme.instantiate()
        ts_sub, ts_type = model_one_type_spec(ctx, stmt.initializer, dto_list)
        last_sub = ts_sub.compose(def_sub)
        return unify(
            last_sub.rewrite_type(def_type), 
            last_sub.rewrite_type(ts_type),
            opt_loc=stmt.loc
        ).compose(last_sub)
    elif isinstance(stmt, ast1.Type1vStatement):
        definition = ctx.try_lookup(stmt.name)
        def_sub, def_type = definition.scheme.instantiate()
        ts_sub, ts_type = model_one_type_spec(ctx, stmt.ts, dto_list)
        last_sub = ts_sub.compose(def_sub)
        return unify(
            last_sub.rewrite_type(def_type), 
            last_sub.rewrite_type(ts_type),
            opt_loc=stmt.loc
        ).compose(last_sub)
    elif isinstance(stmt, ast1.ConstStatement):
        sub, enum_type = model_one_type_spec(ctx, stmt.const_type_spec, dto_list)
        iota_ctx = Context(ContextKind.ConstImmediatelyInvokedFunctionBlock, ctx)
        iota_ctx.local_return_type = enum_type
        for const_bind_stmt in stmt.body:
            assert isinstance(const_bind_stmt, ast1.Bind1vStatement)
            definition = ctx.try_lookup(const_bind_stmt.name)
            assert definition is not None
            const_sub, const_type = definition.scheme.instantiate()
            
            # unifying with RHS; note 'iota_ctx' so 'iota' resolves correctly
            rhs_sub, rhs_type = model_one_exp(iota_ctx, const_bind_stmt.initializer, dto_list)
            rhs_u_sub = unify(rhs_type, const_type)

            # unifying with enum type:
            common_u_sub = unify(const_type, enum_type)

            # updating accumulator 'sub'
            sub = common_u_sub.compose(rhs_u_sub).compose(rhs_sub).compose(const_sub).compose(sub)

        return sub
    elif isinstance(stmt, ast1.ReturnStatement):
        if ctx.return_type is None:
            panic.because(
                panic.ExitCode.SyntaxError,
                "Cannot 'return' outside a function block",
                opt_loc=stmt.loc
            )
        ret_exp_sub, ret_exp_type = model_one_exp(ctx, stmt.returned_exp, dto_list)
        return unify(ret_exp_type, ret_exp_sub.rewrite_type(ctx.return_type), opt_loc=stmt.loc).compose(ret_exp_sub)
    elif isinstance(stmt, ast1.IteStatement):
        condition_sub, condition_type = model_one_exp(ctx, stmt.cond, dto_list)
        cond_dto_sub = dto_list.add_dto(IteCondTypeCheckDTO(stmt.loc, condition_type))
        then_sub = model_one_block(ctx, stmt.then_block, dto_list)
        else_sub = model_one_block(ctx, stmt.else_block, dto_list) if stmt.else_block else Substitution.empty
        return then_sub.compose(else_sub).compose(cond_dto_sub).compose(condition_sub)
    else:
        raise NotImplementedError(f"Don't know how to solve types: {stmt.desc}")


def model_one_exp(
    ctx: "Context", 
    exp: ast1.BaseExpression, 
    dto_list: "DTOList"
) -> t.Tuple["Substitution", types.BaseType]:
    exp_sub, exp_type = help_model_one_exp(ctx, exp, dto_list)
    return exp_sub, exp_sub.rewrite_type(exp_type)


def help_model_one_exp(
    ctx: "Context", 
    exp: ast1.BaseExpression, 
    dto_list: "DTOList"
) -> t.Tuple["Substitution", types.BaseType]:
    if isinstance(exp, ast1.IdRefExpression):
        found_definition = ctx.try_lookup(exp.name)
        if found_definition is None:
            panic.because(
                panic.ExitCode.TyperModelerUndefinedIdError,
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
        made_ts_sub, made_type = model_one_type_spec(ctx, exp.made_ts, dto_list)
        args_sub = Substitution.empty
        initializer_type_list = []
        for initializer_arg_exp in exp.initializer_list:
            initializer_arg_sub, initializer_arg_type = model_one_exp(ctx, initializer_arg_exp, dto_list)
            args_sub = initializer_arg_sub.compose(args_sub)
            initializer_type_list.append(initializer_arg_type)
        # TODO: check the arguments against the made type, maybe using a deferred query.
        sub = args_sub.compose(made_ts_sub)
        return sub, made_type
    elif isinstance(exp, ast1.UnaryOpExpression):
        res_type = types.VarType(f"unary_op_{exp.operator.name.lower()}_res", exp.loc)
        operand_sub, operand_type = model_one_exp(ctx, exp.operand, dto_list)
        operation_dto_sub = dto_list.add_dto(UnaryOpDTO(exp.loc, exp.operator, res_type, operand_type))
        return operand_sub.compose(operation_dto_sub), res_type
    elif isinstance(exp, ast1.BinaryOpExpression):
        res_type = types.VarType(f"binary_op_{exp.operator.name.lower()}_res")
        lt_operand_sub, lt_operand_type = model_one_exp(ctx, exp.lt_operand, dto_list)
        rt_operand_sub, rt_operand_type = model_one_exp(ctx, exp.rt_operand, dto_list)
        operation_dto_sub = dto_list.add_dto(BinaryOpDTO(exp.loc, exp.operator, res_type, lt_operand_type, rt_operand_type))
        sub = operation_dto_sub.compose(rt_operand_sub).compose(lt_operand_sub)
        return sub, res_type
    elif isinstance(exp, ast1.ProcCallExpression):
        # collecting actual procedure type information:
        # type based on how the procedure is used, derived from 'actual' arguments and 'actual' return type
        all_arg_sub = Substitution.empty
        arg_type_list = []
        for arg_exp in exp.arg_exps:
            arg_sub, arg_type = model_one_exp(ctx, arg_exp, dto_list)
            arg_type_list.append(all_arg_sub.rewrite_type(arg_type))
            all_arg_sub = arg_sub.compose(all_arg_sub)
        proxy_ret_type = types.VarType(f"proc_call_ret")
        actual_proc_type = types.ProcedureType.new(arg_type_list, proxy_ret_type)
        
        # collecting formal procedure type information:
        # type based on how the procedure was defined in this context:
        formal_proc_sub, formal_proc_type = model_one_exp(ctx, exp.proc, dto_list)
        last_sub = formal_proc_sub.compose(all_arg_sub)

        # unifying, returning:
        sub = unify(
            last_sub.rewrite_type(formal_proc_type), 
            last_sub.rewrite_type(actual_proc_type),
            opt_loc=exp.loc
        ).compose(last_sub)
        return sub, proxy_ret_type
    elif isinstance(exp, ast1.DotIdExpression):
        container_sub, container_type = model_one_exp(ctx, exp.container, dto_list)
        proxy_ret_type = types.VarType(f"dot_{exp.key}")
        add_dto_sub = dto_list.add_dto(DotIdDTO(exp.loc, container_type, proxy_ret_type, exp.key))
        return container_sub.compose(add_dto_sub), proxy_ret_type
    elif isinstance(exp, ast1.IotaExpression):
        return Substitution.empty, ctx.return_type
    else:
        raise NotImplementedError(f"Don't know how to solve types: {exp.desc}")


def model_one_type_spec(
    ctx: "Context", 
    ts: "ast1.BaseTypeSpec", 
    dto_list: "DTOList"
) -> t.Tuple["Substitution", types.BaseType]:
    ts_sub, ts_type = help_model_one_type_spec(ctx, ts, dto_list)
    return ts_sub, ts_sub.rewrite_type(ts_type)


def help_model_one_type_spec(
    ctx: "Context", 
    ts: "ast1.BaseTypeSpec", 
    dto_list: "DTOList"
) -> t.Tuple["Substitution", types.BaseType]:
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
                panic.ExitCode.TyperModelerUndefinedIdError,
                f"Undefined ID used: {ts.name}",
                opt_loc=ts.loc
            )
        sub, def_type = found_definition.scheme.instantiate()
        return sub, def_type
    elif isinstance(ts, ast1.ProcSignatureTypeSpec):
        all_args_sub = Substitution.empty
        all_arg_types = []
        for opt_arg_name, arg_type in ts.args_list:
            arg_sub, arg_type = model_one_type_spec(ctx, arg_type, dto_list)
            all_args_sub = arg_sub.compose(all_args_sub)
            all_arg_types.append(arg_type)
        ret_sub, ret_type = model_one_type_spec(ctx, ts.ret_ts, dto_list)
        sub = ret_sub.compose(all_args_sub)
        return sub, types.ProcedureType.new(all_arg_types, ret_type)
    elif isinstance(ts, ast1.AdtTypeSpec):
        sub = Substitution.empty
        fields = []
        for field_name, field_ts in ts.fields_list:
            assert field_name is not None
            field_sub, field_type  = model_one_type_spec(ctx, field_ts, dto_list)
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
# source file typing: part III: deferred resolution (solving)
#

# DTOList = Deferred Type Order List
# (cf BaseDTO below)

class DTOList(object): 
    def __init__(self):
        self.internal_dto_list: t.List[BaseDTO] = []

    def add_dto(self, dto: "BaseDTO") -> "Substitution":
        # before adding to the list, we first try applying immediately
        finished, sub = dto.increment_solution()
        if finished:
            return sub
        else:
            self.internal_dto_list.append(dto)
            return Substitution.empty

    def update(self, sub, opt_replacement_internal_dto_list=None):
        if opt_replacement_internal_dto_list is not None:
            dto_list = opt_replacement_internal_dto_list
            self.internal_dto_list = dto_list
        else:
            dto_list = self.internal_dto_list

        for dto in dto_list:
            dto.rewrite_with_sub(sub)

    def solve(self) -> "Substitution":
        finished = False
        while not finished:
            # solving one iteration:
            old_dto_list = self.internal_dto_list
            finished, new_dto_list, sub = DTOList.solve_one_iteration(old_dto_list)
            
            # ensuring solving hasn't stalled:
            if len(new_dto_list) == len(old_dto_list):
                panic.because(
                    panic.ExitCode.TyperDtoSolverStalledError,
                    f"TYPER: DTOList solution stalled with {len(new_dto_list)} constraints remaining:\n" +
                    '\n'.join(map(str, new_dto_list))
                )

            # applying the substitution:
            Context.builtin_root.apply_sub_in_place_to_sub_tree(sub)
            self.update(sub, new_dto_list)

    @staticmethod
    def solve_one_iteration(dto_list: t.List["BaseDTO"]) -> t.Tuple[bool, t.List["BaseDTO"], "Substitution"]:
        new_dto_list = []
        sub = Substitution.empty
        all_finished = True
        for dto in dto_list:
            dto_finished, dto_sub = dto.increment_solution()
            if not dto_finished:
                new_dto_list.append(dto)
                all_finished = False
            sub = sub.compose(dto_sub)
        return all_finished, new_dto_list, sub


# DTO = Deferred Type Order
#

class BaseDTO(object, metaclass=abc.ABCMeta):
    def __init__(self, loc: fb.ILoc, arg_type_list: t.List[types.BaseType]):
        super().__init__()
        self.loc: fb.ILoc = loc
        self.arg_type_list: t.List[types.BaseType] = arg_type_list

    @abc.abstractmethod
    def increment_solution(self) -> t.Tuple[bool, "Substitution"]:
        pass

    @abc.abstractmethod
    def __str__(self):
        pass

    def __repr__(self):
        return str(self)

    def rewrite_with_sub(self, sub: "Substitution"):
        for i in range(len(self.arg_type_list)):
            self.arg_type_list[i] = sub.rewrite_type(self.arg_type_list[i])


class IteCondTypeCheckDTO(BaseDTO):
    def __init__(self, loc: fb.ILoc, cond_type: types.BaseType):
        super().__init__(loc, [cond_type])
    
    @property
    def condition_type(self):
        return self.arg_type_list[0]
    
    def increment_solution(self) -> t.Tuple[bool, "Substitution"]:
        if self.condition_type.is_var:
            return True, Substitution.get({self.condition_type: types.IntType.get(1, is_signed=False)})
        elif self.condition_type != types.IntType.get(1, is_signed=False):
            panic.because(
                panic.ExitCode.TyperDtoSolverFailedError,
                f"If-Then-Else (ITE) expected a boolean condition expression type, but got: {self.condition_type}",
                opt_loc=self.loc
            )
        else:
            return True, Substitution.empty

    def __str__(self):
        return f"IfThenElse(cond={self.condition_type})"


class UnaryOpDTO(BaseDTO):
    def __init__(self, loc: fb.ILoc, unary_op: ast1.UnaryOperator, res_type: types.BaseType, arg_type: types.BaseType):
        super().__init__(loc, [res_type, arg_type])
        self.unary_op = unary_op
    
    @property
    def return_type(self) -> types.BaseType:
        return self.arg_type_list[0]

    @property
    def operand_type(self) -> types.BaseType:
        return self.arg_type_list[1]

    def increment_solution(self) -> t.Tuple[bool, "Substitution"]:
        if self.unary_op == ast1.UnaryOperator.LogicalNot:
            arg_u_sub = unify(self.operand_type, types.IntType.get(1, is_signed=False), opt_loc=self.loc)
            ret_u_sub = unify(self.return_type, types.IntType.get(1, is_signed=False), opt_loc=self.loc)
            return True, ret_u_sub.compose(arg_u_sub)
        elif self.unary_op in (ast1.UnaryOperator.Minus, ast1.UnaryOperator.Plus):
            if self.operand_type.is_var:
                return False, Substitution.empty
            else:
                if self.operand_type.kind == types.IntType:
                    if self.operand_type.is_signed:
                        # + <int> => return identity
                        ret_sub = unify(self.operand_type, self.return_type, opt_loc=self.loc)
                        return True, ret_sub
                    else:
                        # + <uint> => return a signed integer of the same width
                        ret_type = types.IntType.get(self.operand_type.width_in_bits, is_signed=True)
                        ret_sub = unify(ret_type, self.return_type, opt_loc=self.loc)
                        return True, ret_sub
                elif self.operand_type.kind == types.TypeKind.Float:
                    ret_sub = unify(self.return_type, self.operand_type, opt_loc=self.loc)
                    return True, ret_sub
                else:
                    panic.because(
                        panic.ExitCode.TyperDtoSolverFailedError,
                        f"Cannot apply {self.unary_op.name} to argument of non-atomic type: {self.operand_type}",
                        opt_loc=self.loc
                    )
        else:
            raise NotImplementedError(f"Solving one iter for UnaryOpDTO for unary op: {self.unary_op.name}")

    def __str__(self):
        return f"{self.unary_op}({self.operand_type})"


class BinaryOpDTO(BaseDTO):
    arithmetic_binary_operator_set = {
        ast1.BinaryOperator.Mul,
        ast1.BinaryOperator.Div,
        ast1.BinaryOperator.Mod,
        ast1.BinaryOperator.Add,
        ast1.BinaryOperator.Sub
    }
    comparison_binary_operator_set = {
        ast1.BinaryOperator.LThan,
        ast1.BinaryOperator.GThan,
        ast1.BinaryOperator.LEq,
        ast1.BinaryOperator.GEq,
        ast1.BinaryOperator.Eq,
        ast1.BinaryOperator.NEq
    }
    logical_binary_operator_set = {
        ast1.BinaryOperator.LogicalAnd,
        ast1.BinaryOperator.LogicalOr
    }
    # TODO: add support for remaining binary operators

    def __init__(
        self, 
        loc: fb.ILoc,
        binary_op: ast1.BinaryOperator, 
        res_type: types.BaseType, 
        lt_arg_type: types.BaseType, rt_arg_type: types.BaseType
    ):
        super().__init__(loc, [res_type, lt_arg_type, rt_arg_type])
        self.binary_op = binary_op

    @property
    def return_type(self):
        return self.arg_type_list[0]

    @property
    def lt_operand_type(self):
        return self.arg_type_list[1]

    @property
    def rt_operand_type(self):
        return self.arg_type_list[2]

    def increment_solution(self) -> t.Tuple[bool, "Substitution"]:
        # can infer if we have either argument type
        # NOTE: can infer from return type as well, but would lose ability to handle operator overloads.
        if self.lt_operand_type.is_var and self.rt_operand_type.is_var:
            return False, Substitution.empty
        
        # arithmetic operators
        if self.binary_op in BinaryOpDTO.arithmetic_binary_operator_set:
            # arithmetic binary operators are symmetrically typed: arguments must have the same type.
            symmetric_args_sub = unify(self.lt_operand_type, self.rt_operand_type, opt_loc=self.loc)
            lt_operand_type = symmetric_args_sub.rewrite_type(self.lt_operand_type)
            rt_operand_type = symmetric_args_sub.rewrite_type(self.rt_operand_type)

            # dispatching based on atomicity:
            if lt_operand_type.is_atomic:
                if isinstance(lt_operand_type, (types.IntType, types.FloatType)):
                    ret_sub = unify(lt_operand_type, self.return_type, opt_loc=self.loc)
                    return True, ret_sub.compose(symmetric_args_sub)
                else:
                    panic.because(
                        panic.ExitCode.TyperDtoSolverFailedError,
                        f"Cannot apply arithmetic binary operator {self.binary_op.name} to these arguments:\n"
                        f"left argument:  {lt_operand_type}\n"
                        f"right argument: {rt_operand_type}"
                    )
            else:
                # NOTE: operator overloading can be added later very easily here.
                panic.because(
                    panic.ExitCode.TyperDtoSolverFailedError,
                    f"Cannot apply arithmetic binary operator {self.binary_op.name} to non-atomic arguments:\n"
                    f"left argument:  {lt_operand_type}\n"
                    f"right argument: {rt_operand_type}"
                )

        # comparison operators
        elif self.binary_op in BinaryOpDTO.comparison_binary_operator_set:
            # comparison operators are symmetrically typed: arguments must have the same type.
            symmetric_args_sub = unify(self.lt_operand_type, self.rt_operand_type, opt_loc=self.loc)
            lt_operand_type = symmetric_args_sub.rewrite_type(self.lt_operand_type)
            rt_operand_type = symmetric_args_sub.rewrite_type(self.rt_operand_type)

            builtin_operation_is_defined = (
                # equality is defined on all types.
                self.binary_op in (ast1.BinaryOperator.Eq, ast1.BinaryOperator.NEq) or
                # all comparison operations are defined on all atomic argument types.
                lt_operand_type.is_atomic
            )
            if builtin_operation_is_defined:
                ret_sub = unify(self.return_type, types.IntType.get(1, is_signed=False), opt_loc=self.loc)
                return True, ret_sub.compose(symmetric_args_sub)
            elif not lt_operand_type.is_atomic:
                panic.because(
                    panic.ExitCode.TyperDtoSolverFailedError,
                    f"Cannot apply comparison binary operator {self.binary_op.name} to non-atomic arguments:\n"
                    f"left argument:  {lt_operand_type}\n"
                    f"right argument: {rt_operand_type}"
                )
            else:
                panic.because(
                    panic.ExitCode.TyperDtoSolverFailedError,
                    f"Cannot apply comparison binary operator {self.binary_op.name} to these arguments:\n"
                    f"left argument:  {lt_operand_type}\n"
                    f"right argument: {rt_operand_type}"
                )
        
        # boolean operators
        elif self.binary_op in BinaryOpDTO.logical_binary_operator_set:
            # NOTE: for now, forcing to be boolean. Can expand once operator overloading is supported.
            symmetric_args_sub = unify(self.lt_operand_type, self.rt_operand_type, opt_loc=self.loc)
            bool_type = types.IntType.get(1, is_signed=False)
            args_check_sub = unify(symmetric_args_sub.rewrite_type(self.lt_operand_type), bool_type, opt_loc=self.loc)
            ret_sub = unify(self.return_type, types.IntType.get(1, is_signed=False), opt_loc=self.loc)
            return True, ret_sub.compose(args_check_sub).compose(symmetric_args_sub)
        
        else:
            raise NotImplementedError(f"Solving one iter for BinaryOpDTO for binary op: {self.binary_op.name}")
        
    def __str__(self):
        return f"{self.binary_op}({self.lt_operand_type}, {self.rt_operand_type})"


class DotIdDTO(BaseDTO):
    def __init__(self, loc: fb.ILoc, container_type: types.BaseType, proxy_ret_type: types.BaseType, key_name: str):
        super().__init__(loc, [container_type, proxy_ret_type])
        self.key_name = key_name

    @property
    def container_type(self) -> types.BaseType:
        return self.arg_type_list[0]
    
    @property
    def proxy_ret_type(self) -> types.BaseType:
        return self.arg_type_list[1]

    def increment_solution(self) -> t.Tuple[bool, "Substitution"]:
        if self.container_type.is_var:
            return False, Substitution.empty
        if not self.container_type.is_composite:
            panic.because(
                panic.ExitCode.TyperDtoSolverFailedError,
                f"Cannot lookup `.{self.key_name}` in non-composite container type: {self.container_type}"
            )
        else:
            assert isinstance(self.container_type, types.BaseCompositeType)
            for field_name, field_type in self.container_type.fields:
                if field_name == self.key_name:
                    break
            else:
                panic.because(
                    panic.ExitCode.TyperDtoSolverFailedError,
                    f"Undefined field `{self.key_name}` in composite container type: {self.container_type}"
                )
            sub = unify(self.proxy_ret_type, field_type, self.loc)
            return True, sub

    def __str__(self):
        return f"DOT({self.container_type}, {self.key_name}, {self.proxy_ret_type})"


#
# Unification
#

def unify(
    t1: types.BaseType, 
    t2: types.BaseType, 
    opt_loc: t.Optional[fb.ILoc] = None
) -> "Substitution":
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
        if t1.is_var:
            var_type = t1
            replacement_type = t2
        else:
            # includes the case where both types are variables.
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
                raise_unification_error(t1, t2)

        # generate a substitution by unifying matching fields:
        s = Substitution.empty
        for ft1, ft2 in zip(t1.field_types, t2.field_types):
            s = unify(
                s.rewrite_type(ft1), 
                s.rewrite_type(ft2),
                opt_loc=opt_loc
            ).compose(s)
        return s

    # any other case: raise a unification error.
    else:
        raise_unification_error(t1, t2, opt_loc=opt_loc)


def raise_unification_error(t: types.BaseType, u: types.BaseType, opt_more=None, opt_loc=None):
    msg_chunks = [f"UNIFICATION_ERROR: Cannot unify {t} and {u}"]
    if opt_more is not None:
        assert isinstance(opt_more, str)
        msg_chunks.append(textwrap.indent(opt_more, ' '*4))
    
    panic.because(
        panic.ExitCode.TyperUnificationError,
        '\n'.join(msg_chunks),
        opt_loc=opt_loc
    )


#
# Contexts:
#

class ContextKind(enum.Enum):
    BuiltinRoot = enum.auto()
    TopLevelOfSourceFile = enum.auto()
    FunctionArgs = enum.auto()
    FunctionBlock = enum.auto()
    ConstImmediatelyInvokedFunctionBlock = enum.auto()
    

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

    def print(self, indent_count: int = 0):
        indent = '  ' * indent_count
        lines = [f"+ {self.kind.name}"]
        for sym_name, sym_definition in self.symbol_table.items():
            if isinstance(sym_definition, ValueDefinition):
                _, def_type = sym_definition.scheme.instantiate()
                line = f"  - {sym_name}: {def_type} [public={sym_definition.is_public}]"
            elif isinstance(sym_definition, TypeDefinition):
                _, def_type = sym_definition.scheme.instantiate()
                line = f"  - {sym_name} = {def_type} [public={sym_definition.is_public}]"
            else:
                raise NotImplementedError("Printing unknown definition")
            lines.append(line)

        for line in lines:
            print(indent, line, sep='')
    
        for child_context in self.children:
            child_context.print(1+indent_count)

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
    def __init__(self, loc: fb.ILoc, name: str, scm: "Scheme") -> None:
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

        # s2 = applied_first
        # s1 = self

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
            
            # if a conflict between s1 and s2 occurs, need to ensure s1 and s2 do not diverge.
            intersecting_key_set = set(s1_sub_map.keys()) & set(s2_sub_map.keys())
            if intersecting_key_set:
                offending_intersecting_key_set = {
                    key
                    for key in intersecting_key_set
                    if s1_sub_map[key] != s2_sub_map[key]
                }
                can_overwrite = all((
                    Substitution.can_overwrite_t1_with_t2(s1_sub_map[key], s2_sub_map[key])
                    for key in offending_intersecting_key_set
                ))
                if offending_intersecting_key_set and not can_overwrite:
                    s1_intersect_map = {key: s1_sub_map[key] for key in offending_intersecting_key_set}
                    s2_intersect_map = {key: s2_sub_map[key] for key in offending_intersecting_key_set}
                    panic.because(
                        panic.ExitCode.TyperUnificationError,
                        f"Unification error: conflicting substitutions composed:\n"
                        f"first: {Substitution.get(s1_intersect_map)}\n"
                        f"later: {Substitution.get(s2_intersect_map)}"
                    )

            return Substitution.get(sub_map=(s1_sub_map | s2_sub_map))

    def __str__(self) -> str:
        return '{' + ','.join((f"{str(key)}->{str(val)}" for key, val in self.sub_map.items())) + '}'

    def __repr__(self) -> str:
        return str(self)

    def rewrite_type(self, t: types.BaseType) -> types.BaseType:
        return self._rewrite_type(t, None)

    def _rewrite_type(self, t: types.BaseType, rw_in_progress_pair_list: pair.List) -> types.BaseType:
        assert isinstance(t, types.BaseType)

        if self is Substitution.empty:
            return t
        if pair.list_contains(rw_in_progress_pair_list, t):
            raise InfiniteSizeTypeException()
    
        rw_in_progress_pair_list = pair.cons(t, rw_in_progress_pair_list)

        # BoundVar in `sub_map` -> replacement
        # FreeVar in `sub_map` -> replacement
        opt_replacement_t = self.sub_map.get(t, None)
        if opt_replacement_t is not None:
            return opt_replacement_t
        
        # Composite types: map rewrite on each component
        if isinstance(t, types.BaseCompositeType):
            return t.copy_with_elements([
                (element_name, self._rewrite_type(element_type, rw_in_progress_pair_list))
                for element_name, element_type in t.fields
            ])
        
        # Otherwise, just return the type as is:
        assert t.is_atomic or t.is_var
        return t

    def rewrite_scheme(self, s: "Scheme") -> "Scheme":
        if s.vars:
            # NOTE: any bound vars mapped in this substitution must be removed from the substitution, since these 
            # variables must be free in the body of the scheme to be substituted out by instantiation.
            # If we rewrote these bound vars, then they would not be unique to each instantiation.
            new_sub_map = {var: self.sub_map[var] for var in s.vars}
            new_sub = Substitution.get(new_sub_map)
        else:
            new_sub = self

        return Scheme(s.vars, new_sub.rewrite_type(s.body))

    @staticmethod
    def can_overwrite_t1_with_t2(t1: types.BaseType, t2: types.BaseType):
        # if t1 == t2, then rewriting one with the other loses no information.
        if t1 == t2:
            return True
        
        # if t1 is a variable, we prefer t2 as a replacement (be it a var or not)
        if t1.is_var:
            return True

        # if t1 is composite, check if t2 has preferable fields.
        if t1.is_composite and t2.is_composite:
            if t1.kind == t2.kind and len(t1.fields) == len(t2.fields):
                return all((
                    Substitution.can_overwrite_t1_with_t2(field_type1, field_type2)
                    for field_type1, field_type2 in zip(t1.field_types, t2.field_types)
                ))

        return False


Substitution.empty = Substitution({}, _suppress_construct_empty_error=True)


#
# Schemes:
#

class Scheme(object):
    def __init__(self, vars: t.List[types.VarType], body: types.BaseType) -> None:
        assert all((isinstance(it, types.VarType) for it in vars))
        super().__init__()
        self.vars = vars
        self.body = body

    def instantiate(
        self, 
        opt_actual_args_list: t.Optional[t.List[types.BaseType]]=None
    ) -> t.Tuple["Substitution", types.BaseType]:
        if not self.vars:
            assert not opt_actual_args_list
            return Substitution.empty, self.body
        
        if opt_actual_args_list is None:
            actual_arg_types = list((types.VarType(f"new({var})") for var in self.vars))
        else:
            actual_arg_types = opt_actual_args_list
            assert len(actual_arg_types) == len(self.vars)

        sub = Substitution.get(dict(zip(
            self.vars,
            actual_arg_types
        )))
        res = sub.rewrite_type(self.body)
        return sub, res

    def __str__(self) -> str:
        return f"({','.join(map(str, self.vars))})=>{self.body}"


#
# Exceptions:
#

class InfiniteSizeTypeException(BaseException):
    pass

