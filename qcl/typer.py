import abc
import typing as t
import sys
import enum
import textwrap

from . import panic
from . import pair
from . import feedback as fb
from . import types
from . import ast1
from . import ast2
from . import interp


#
# source file typing: part 1: seeding
#

def seed_one_source_file(sf: ast2.BaseSourceFile, new_ctx):
    """
    defines global symbols in a context using free variables, then sets it on `x_typer_ctx`
    """

    for top_level_stmt in sf.stmt_list:
        seed_one_top_level_stmt(new_ctx, top_level_stmt)

    sf.wb_typer_ctx = new_ctx


def seed_one_top_level_stmt(bind_in_ctx: "Context", stmt: ast1.BaseStatement):
    #
    # Handling 'bind' statements:
    #
    
    new_definition = None
    if isinstance(stmt, ast1.Bind1vStatement):
        extern_tag = None
        if isinstance(stmt, ast1.Extern1vStatement):
            extern_tag = "c"
            var_type = stmt.var_type_spec.wb_type
            assert var_type is not None
        else:
            assert isinstance(stmt, ast1.Bind1vStatement)
            if stmt.is_constant:
                var_type = types.VarType(f"bind1v_{stmt.name}")
            else:
                panic.because(
                    panic.ExitCode.ScopingError,
                    "Runtime `val` bindings are not allowed at the top-level: no global variables are supported: use `const` instead.",
                    opt_loc=stmt.loc
                )
        new_definition = ValueDefinition(
            stmt.loc,
            stmt.name, 
            Scheme([], var_type),
            stmt,
            extern_tag=extern_tag,
            is_compile_time_constant=stmt.is_constant
        )
    elif isinstance(stmt, ast1.Bind1fStatement):
        extern_tag = None
        if isinstance(stmt, ast1.Extern1fStatement):
            extern_tag = "c"
            fn_arg_types = []
            for arg_ts in stmt.arg_typespecs:
                arg_type = arg_ts.wb_type
                assert arg_type is not None
                fn_arg_types.append(arg_type)
            fn_ret_type = stmt.ret_typespec.wb_type
            fn_type = types.ProcedureType.new(fn_arg_types, fn_ret_type, has_closure_slot=False, is_c_variadic=stmt.is_variadic)
        else:
            fn_type = types.VarType(f"bind1f_{stmt.name}")
        new_definition = ValueDefinition(
            stmt.loc,
            stmt.name,
            Scheme([], fn_type),
            stmt,
            extern_tag=extern_tag,
            is_compile_time_constant=True
        )
    elif isinstance(stmt, ast1.Bind1tStatement):
        if stmt.initializer is not None and stmt.initializer.wb_type is not None:
            extern_tag = "c"
            bound_type = stmt.initializer.wb_type
        else:
            extern_tag = None
            bound_type = types.VarType(f"bind1t_{stmt.name}")

        new_definition = TypeDefinition(
            stmt.loc,
            stmt.name,
            Scheme([], bound_type),
            stmt,
            extern_tag=extern_tag
        )
    elif isinstance(stmt, (ast1.ConstStatement, ast1.Type1vStatement)):
        # handled later...
        pass
    else:
        panic.because(
            panic.ExitCode.ScopingError,
            "Invalid statement found in top-level scope: please move this into a function.",
            opt_loc=stmt.loc
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
# source file typing: part 2: modelling
#

def model_one_source_file(
    sf: ast2.BaseSourceFile, dto_list: "DTOList", 
    sub: t.Optional["Substitution"]
) -> "Substitution":
    sf_top_level_context = sf.wb_typer_ctx
    assert isinstance(sf_top_level_context, Context)
    return model_one_block(sf_top_level_context, sf.stmt_list, dto_list, init_sub=sub, is_top_level=True)


def model_one_block(
    ctx: "Context", 
    stmt_list: t.List[ast1.BaseStatement], 
    dto_list: "DTOList", 
    init_sub: t.Optional["Substitution"] = None,
    is_top_level=False
) -> t.Tuple["Substitution", types.BaseType]:
    sub, _ = model_one_block_with_type(ctx, stmt_list, dto_list, init_sub, is_top_level)
    return sub


def model_one_block_with_type(
    ctx: "Context", 
    stmt_list: t.List[ast1.BaseStatement], 
    dto_list: "DTOList", 
    init_sub: t.Optional["Substitution"] = None,
    is_top_level=False
) -> t.Tuple["Substitution", types.BaseType]:
    if init_sub is None:
        init_sub = Substitution.empty

    assert isinstance(init_sub, Substitution)
    sub = init_sub
    
    for stmt in stmt_list:
        stmt_sub = model_one_statement(ctx, stmt, dto_list)
        sub = stmt_sub.compose(sub, stmt.loc)
        if is_top_level:
            Context.apply_sub_everywhere(sub)
            dto_list.update(sub)
            ast1.WbTypeMixin.apply_sub_everywhere(sub)
    
    shallow_return_type = types.VoidType.singleton
    if stmt_list:
        last_stmt = stmt_list[-1]
        if isinstance(last_stmt, ast1.ReturnStatement) and last_stmt.is_shallow:
            shallow_return_type = last_stmt.returned_exp.wb_type
    
    return sub, shallow_return_type


def model_one_lambda_body(
    ctx: "Context", loc,
    arg_name_type_list: t.List[t.Tuple[str, types.BaseType]],
    body_prefix_stmt_list: t.List["ast1.BaseStatement"],
    opt_body_tail_exp: t.Optional["ast1.BaseExpression"],
    dto_list: "DTOList"
) -> t.Tuple["Substitution", types.BaseType]:
    # setting the function context, 'local_return_type' attribute, init other stuff
    fn_ctx = Context(ContextKind.FunctionBlock, ctx)
    fn_ctx.local_return_type = types.VarType(f"fn_return")
    sub = Substitution.empty

    # defining each formal argument for this function:
    for arg_index, (arg_name, arg_type) in enumerate(arg_name_type_list):
        loc = fb.BuiltinLoc(f"arg({arg_index}):{arg_name}")
        scm = Scheme([], arg_type)
        fn_ctx.try_define(ValueDefinition(loc, arg_name, scm, binder=None))

    # solving any prefix statements:
    #   - any 'return' statements are associated with the nearest 'return_type' attribute, set above.
    if body_prefix_stmt_list:
        sub = model_one_block(ctx, body_prefix_stmt_list, dto_list)

    # solving the tail expression:
    tail_return_type = types.VoidType.singleton
    tail_loc = loc
    if opt_body_tail_exp is not None:
        tail_sub, tail_return_type = model_one_exp(fn_ctx, opt_body_tail_exp, dto_list)
        sub = tail_sub.compose(sub, opt_body_tail_exp.loc)
        tail_loc = opt_body_tail_exp.loc
    sub = unify(fn_ctx.local_return_type, tail_return_type, tail_loc).compose(sub, loc)

    # returns sub + _return type_, not type of lambda
    return sub, fn_ctx.local_return_type


def model_one_statement(ctx: "Context", stmt: "ast1.BaseStatement", dto_list: "DTOList") -> "Substitution":
    stmt.wb_ctx = ctx

    if isinstance(stmt, ast1.Bind1vStatement):
        if isinstance(stmt, ast1.Extern1vStatement):
            exp_sub, exp_type = model_one_type_spec(ctx, stmt.var_type_spec, dto_list)
        else:
            exp_sub, exp_type = model_one_exp(ctx, stmt.initializer, dto_list)
        if ctx.kind in (ContextKind.TopLevelOfQypSet, ContextKind.ConstImmediatelyInvokedFunctionBlock):
            # definition is already seeded-- just retrieve and unify.
            # NOTE: must use 'lookup' instead of a shallow lookup in symbol table for special case of 'ConstStatement':
            # - the 'ctx_with_loc' context is a child of the global context containing the defined symbol
            # - the 'ctx_with_loc' context is used to extend the global context with '$pred' or other special keywords.
            definition = ctx.lookup(stmt.name)
            def_sub, def_type = definition.scheme.instantiate()
            last_sub = def_sub.compose(exp_sub, stmt.loc)
            return unify(
                last_sub.rewrite_type(def_type), 
                last_sub.rewrite_type(exp_type),
                opt_loc=stmt.loc
            ).compose(last_sub, stmt.loc)
        else:
            # try to create a local definition using the expression type.
            definition = ValueDefinition(stmt.loc, stmt.name, Scheme([], exp_type), stmt)
            conflicting_def = ctx.try_define(definition)
            if conflicting_def is not None:
                panic.because(
                    panic.ExitCode.TyperModelerRedefinedIdError,
                    f"Local value identifier '{stmt.name}' bound twice:\n"
                    f"first: {conflicting_def.loc}\n"
                    f"later: {definition.loc}"
                )
            else:
                def_sub, def_type = definition.scheme.instantiate()
                return def_sub

    elif isinstance(stmt, ast1.Bind1fStatement):
        args_sub = Substitution.empty
        if isinstance(stmt, ast1.Extern1fStatement):
            assert stmt.ret_typespec.wb_type is not None
            ret_sub, ret_type = model_one_type_spec(ctx, stmt.ret_typespec, dto_list)
            arg_type_list = []
            for arg_ts in stmt.arg_typespecs:
                assert arg_ts.wb_type is not None
                arg_ts_sub, arg_type = model_one_type_spec(ctx, arg_ts, dto_list)

                args_sub = arg_ts_sub.compose(args_sub, arg_ts.loc)
                arg_type_list.append(arg_type)
        else:
            arg_type_list = [
                types.VarType(f"arg{arg_index}:{arg_name}")
                for arg_index, arg_name in enumerate(stmt.args_names)
            ]
            arg_name_type_list = list(zip(stmt.args_names, arg_type_list))
            ret_sub, ret_type = model_one_lambda_body(ctx, stmt.loc, arg_name_type_list, [], stmt.body_exp, dto_list)
        proc_type = types.ProcedureType.new(arg_type_list, ret_type)
        def_sub, def_type = ctx.try_lookup(stmt.name).scheme.instantiate()
        last_sub = def_sub.compose(ret_sub, stmt.loc)
        return unify(
            last_sub.rewrite_type(proc_type), 
            last_sub.rewrite_type(def_type),
            opt_loc=stmt.loc
        ).compose(last_sub, stmt.loc)

    elif isinstance(stmt, ast1.Bind1tStatement):
        definition = ctx.try_lookup(stmt.name)
        assert definition is not None
        def_sub, def_type = definition.scheme.instantiate()
        ts_sub, ts_type = model_one_type_spec(ctx, stmt.initializer, dto_list)
        last_sub = ts_sub.compose(def_sub, stmt.initializer.loc)
        return unify(
            last_sub.rewrite_type(def_type), 
            last_sub.rewrite_type(ts_type),
            opt_loc=stmt.loc
        ).compose(last_sub, stmt.loc)

    elif isinstance(stmt, ast1.Type1vStatement):
        definition = ctx.try_lookup(stmt.name)
        if definition is None:
            panic.because(
                panic.ExitCode.TyperModelerUndefinedIdError,
                f"Identifier '{stmt.name}' declared, but not defined.",
                opt_loc=stmt.loc
            )
        assert definition is not None and definition.is_value_definition
        def_sub, def_type = definition.scheme.instantiate()
        ts_sub, ts_type = model_one_type_spec(ctx, stmt.ts, dto_list)
        last_sub = ts_sub.compose(def_sub, stmt.ts.loc)
        return unify(
            last_sub.rewrite_type(def_type), 
            last_sub.rewrite_type(ts_type),
            opt_loc=stmt.loc
        ).compose(last_sub, stmt.loc)

    elif isinstance(stmt, ast1.ConstStatement):
        sub, enum_type = model_one_type_spec(ctx, stmt.const_type_spec, dto_list)
        
        ctx_with_pred = Context(ContextKind.ConstImmediatelyInvokedFunctionBlock, ctx)
        ctx_with_pred.local_return_type = enum_type
        
        for const_bind_stmt in stmt.body:
            assert isinstance(const_bind_stmt, ast1.Bind1vStatement)
            
            # note 'ctx_with_pred' so '$pred' resolves correctly
            new_sub = model_one_statement(ctx_with_pred, const_bind_stmt, dto_list)
            sub = new_sub.compose(sub, const_bind_stmt.loc)

            # type-checking:
            typecheck_sub = unify(const_bind_stmt.initializer.wb_type, enum_type, stmt.loc)
            sub = typecheck_sub.compose(sub, stmt.loc)

        return sub

    elif isinstance(stmt, ast1.ReturnStatement):
        if ctx.return_type is None:
            panic.because(
                panic.ExitCode.SyntaxError,
                "Cannot 'return' outside a function block",
                opt_loc=stmt.loc
            )
        ret_exp_sub, ret_exp_type = model_one_exp(ctx, stmt.returned_exp, dto_list)
        l = stmt.loc
        return unify(ret_exp_type, ret_exp_sub.rewrite_type(ctx.return_type),l).compose(ret_exp_sub,l)
    
    elif isinstance(stmt, ast1.DiscardStatement):
        sub, _ = model_one_exp(ctx, stmt.discarded_exp, dto_list)
        return sub
    
    elif isinstance(stmt, ast1.LoopStatement):
        # if `while (cond) do {body...}`, then model 'cond' before 'body'
        cond_exp_sub, cond_exp_type = (
            model_one_exp(ctx, stmt.cond, dto_list)
            if stmt.loop_style == ast1.LoopStyle.WhileDo else
            (None, None)
        )
        
        # modelling body:
        body_sub = model_one_block(ctx, stmt.body, dto_list)
        
        # if `do {body...} while (cond)`, then model 'body' before 'cond'
        cond_exp_sub, cond_exp_type = (
            model_one_exp(ctx, stmt.cond, dto_list)
            if stmt.loop_style == ast1.LoopStyle.DoWhile else
            (cond_exp_sub, cond_exp_type)
        )

        # returning:
        assert cond_exp_type is not None and cond_exp_sub is not None
        return (
            body_sub.compose(cond_exp_sub, stmt.loc)
            if stmt.loop_style == ast1.LoopStyle.DoWhile else
            cond_exp_sub.compose(body_sub, stmt.loc)
        )
    
    elif isinstance(stmt, ast1.BaseLoopControlStatement):
        return Substitution.empty
    
    else:
        raise NotImplementedError(f"Don't know how to solve types: {stmt.desc}")


def model_one_exp(
    ctx: "Context", 
    exp: ast1.BaseExpression, 
    dto_list: "DTOList"
) -> t.Tuple["Substitution", types.BaseType]:
    exp.wb_ctx = ctx
    exp_sub, exp_type = help_model_one_exp(ctx, exp, dto_list)
    exp.wb_type = exp_type
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
                f"Value identifier '{exp.name}' used, but not defined or declared",
                opt_loc=exp.loc
            )
        if not isinstance(found_definition, ValueDefinition):
            panic.because(
                panic.ExitCode.TyperModelerInvalidIdError,
                f"ID '{exp.name}' does not refer to a value, but was used as one.",
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

    elif isinstance(exp, ast1.ConstructExpression):
        made_ts_sub, made_type = model_one_type_spec(ctx, exp.made_ts, dto_list)
        args_sub = Substitution.empty
        initializer_type_list = []
        for initializer_arg_exp in exp.initializer_list:
            initializer_arg_sub, initializer_arg_type = model_one_exp(ctx, initializer_arg_exp, dto_list)
            args_sub = initializer_arg_sub.compose(args_sub, exp.loc)
            initializer_type_list.append(initializer_arg_type)
        
        # TODO: check the arguments against the made type, maybe using a deferred query or unification?
        # - different types admit different constructors, e.g.
        #   - most datatypes accept an instance of the value or a value that can be cast to the target
        #   - arrays accept a single 'init_fill' argument OR a 'fill' predicate mapping indices to objects
        #   - dynamic arrays accept two arguments: length and a 'fill' value OR a 'fill' predicate mapping indices to objects
        #   - slices accept four arguments: a backing array or buffer or slice, offset, count, stride
        #     - elem-size inferred from element-type
        #     - offset, count, and stride have same dimension as array key, i.e. 1
        
        # the constructed instance can be referenced directly or via a pointer:
        # preparing the return type:
        sub = args_sub.compose(made_ts_sub, exp.loc)
        if exp.construct_frontend == ast1.ConstructFrontend.New:
            assert not exp.is_mut
            ret_type = sub.rewrite_type(made_type)
        elif exp.construct_frontend in (ast1.ConstructFrontend.Heap, ast1.ConstructFrontend.Push):
            ret_type = types.PointerType.new(sub.rewrite_type(made_type), is_mut=exp.is_mut)
        else:
            raise NotImplementedError("ConstructExpression: Unknown frontend: how was this constructor used, and what does the user expect in return?")

        return sub, ret_type

    elif isinstance(exp, ast1.UnaryOpExpression):
        res_type = types.VarType(f"unary_op_{exp.operator.name.lower()}_res", exp.loc)
        operand_sub, operand_type = model_one_exp(ctx, exp.operand, dto_list)
        operation_dto_sub = dto_list.add_dto(UnaryOpDTO(exp.loc, exp.operator, res_type, operand_type))
        return operand_sub.compose(operation_dto_sub, exp.loc), res_type

    elif isinstance(exp, ast1.BinaryOpExpression):
        res_type = types.VarType(f"binary_op_{exp.operator.name.lower()}_res")
        lt_operand_sub, lt_operand_type = model_one_exp(ctx, exp.lt_operand_exp, dto_list)
        rt_operand_sub, rt_operand_type = model_one_exp(ctx, exp.rt_operand_exp, dto_list)
        operation_dto_sub = dto_list.add_dto(BinaryOpDTO(exp.loc, exp.operator, res_type, lt_operand_type, rt_operand_type))
        sub = operation_dto_sub.compose(rt_operand_sub, exp.loc).compose(lt_operand_sub, exp.loc)
        return sub, res_type

    elif isinstance(exp, ast1.ProcCallExpression):
        # collecting actual procedure type information:
        # type based on how the procedure is used, derived from 'actual' arguments and 'actual' return type
        all_arg_sub = Substitution.empty
        arg_type_list = []
        for arg_exp in exp.arg_exps:
            arg_sub, arg_type = model_one_exp(ctx, arg_exp, dto_list)
            arg_type_list.append(all_arg_sub.rewrite_type(arg_type))
            all_arg_sub = arg_sub.compose(all_arg_sub, exp.loc)
        proxy_src_type = types.VarType(f"proc_call_ret")
        actual_proc_type = types.ProcedureType.new(arg_type_list, proxy_src_type)
        
        # collecting formal procedure type information:
        # type based on how the procedure was defined in this context:
        formal_proc_sub, formal_proc_type = model_one_exp(ctx, exp.proc, dto_list)
        last_sub = formal_proc_sub.compose(all_arg_sub, exp.loc)

        # unifying, returning:
        sub = unify(
            last_sub.rewrite_type(formal_proc_type), 
            last_sub.rewrite_type(actual_proc_type),
            opt_loc=exp.loc
        ).compose(last_sub, exp.loc)
        return sub, sub.rewrite_type(proxy_src_type)

    elif isinstance(exp, ast1.DotIdExpression):
        container_sub, container_type = model_one_exp(ctx, exp.container, dto_list)
        proxy_src_type = types.VarType(f"dot_{exp.key}")
        add_dto_sub = dto_list.add_dto(DotIdDTO(exp.loc, container_type, proxy_src_type, exp.key))
        return add_dto_sub.compose(container_sub, exp.loc), proxy_src_type

    elif isinstance(exp, ast1.ConstPredecessorExpression):
        return Substitution.empty, ctx.return_type

    elif isinstance(exp, ast1.IfExpression):
        def help_model_branch_type(branch_exp):
            nonlocal ctx, dto_list, sub
            
            # first, ensuring this branch is a 0-ary lambda:
            assert isinstance(branch_exp, ast1.LambdaExpression)
            if branch_exp.arg_names:
                panic.because(
                    panic.ExitCode.TyperModelerBadConditional,
                    opt_msg=f"Expected a 0-ary lambda, but got {len(branch_exp.arg_names)}-ary lambda",
                    opt_loc=branch_exp.loc
                )
            
            # next, typing the branch:
            branch_sub, branch_lambda_type = model_one_exp(ctx, branch_exp, dto_list)
            branch_lambda_type = sub.rewrite_type(branch_lambda_type)
            sub = branch_sub.compose(sub, branch_exp.loc)
            
            # extracting the branch return-value as the 'ite' return value
            assert isinstance(branch_lambda_type, types.ProcedureType)
            branch_type = branch_lambda_type.ret_type

            # returning:
            return sub, branch_type

        # first, modelling the 'cond', 'then', and 'else' branch expressions:
        cond_sub, cond_type = model_one_exp(ctx, exp.cond_exp, dto_list)
        sub = cond_sub
        sub, then_type = help_model_branch_type(exp.then_exp)
        sub, else_type = (
            help_model_branch_type(exp.else_exp)
            if exp.else_exp is not None else
            (Substitution.empty, types.VoidType.singleton)
        )
        
        # next, unifying types to type-check.
        ret_type = types.VarType(f"ite_ret_type", exp.loc)
        bool_type = types.IntType.get(1, is_signed=False)
        sub = unify(cond_type, bool_type, exp.loc).compose(sub, exp.loc)     # ensuring 'cond' is a boolean
        sub = unify(then_type, else_type, exp.loc).compose(sub, exp.loc)     # ensuring branches return the same type
        sub = unify(then_type, ret_type, exp.loc).compose(sub, exp.loc)      # ensuring branches return the ret type
        
        # finally, returning:
        return sub, sub.rewrite_type(ret_type)

    elif isinstance(exp, ast1.LambdaExpression):
        # TODO: check that 'has_closure_slot' is respected before passing to C++
        has_closure_slot = exp.no_closure
        
        arg_types = []
        arg_name_type_list = []
        if exp.arg_names is not None:
            arg_types = [
                types.VarType(f"lambda_formal_arg_{arg_name}", exp.loc)
                for arg_name in exp.arg_names
            ]
            arg_name_type_list = list(zip(exp.arg_names, arg_types))
        
        prefix_stmt_list = []
        if exp.body_prefix:
            prefix_stmt_list = exp.body_prefix

        opt_tail_exp = exp.opt_body_tail

        sub, ret_type = model_one_lambda_body(ctx, exp.loc, arg_name_type_list, prefix_stmt_list, opt_tail_exp, dto_list)
        
        return sub, types.ProcedureType.new(arg_types, ret_type, has_closure_slot=has_closure_slot, is_c_variadic=False)
    
    elif isinstance(exp, ast1.UpdateExpression):
        # typechecking the following rule:
        # MutPtr(T) := T

        proxy_src_type = types.VarType(f"update_proxy_src_type", exp.loc)
        proxy_dst_type = types.PointerType.new(proxy_src_type, is_mut=True)

        dst_sub, dst_type = model_one_exp(ctx, exp.store_address, dto_list)
        sub = dst_sub

        src_sub, src_type = model_one_exp(ctx, exp.stored_value, dto_list)
        sub = src_sub.compose(dst_sub, exp.loc)
        
        src_type = sub.rewrite_type(src_type)
        dst_type = sub.rewrite_type(dst_type)
        proxy_dst_type = sub.rewrite_type(proxy_dst_type)
        proxy_src_type = sub.rewrite_type(proxy_src_type)
        
        # unifying src type with the src proxy:
        src_typecheck_sub = unify(proxy_src_type, src_type, exp.loc)
        proxy_src_type = src_typecheck_sub.rewrite_type(proxy_src_type)
        proxy_dst_type = src_typecheck_sub.rewrite_type(proxy_dst_type)
        sub = src_typecheck_sub.compose(sub, exp.loc)

        # unifying dst type with the dst proxy:
        # via above sub, the dst proxy should contain information about actual src type.
        dst_typecheck_sub = unify(proxy_dst_type, dst_type, exp.loc)
        proxy_src_type = dst_typecheck_sub.rewrite_type(proxy_src_type)
        proxy_dst_type = dst_typecheck_sub.rewrite_type(proxy_dst_type)
        sub = dst_typecheck_sub.compose(sub, exp.loc)

        return sub, proxy_src_type

    elif isinstance(exp, ast1.IndexExpression):
        container_sub, container_type = model_one_exp(ctx, exp.container, dto_list)
        sub = container_sub

        index_sub, index_type = model_one_exp(ctx, exp.index, dto_list)
        index_type = sub.rewrite_type(index_type)
        sub = index_sub.compose(sub, exp.loc)
        
        index_dto_sub = dto_list.add_dto(IsIntTypeDTO(exp.loc, index_type, "array-like index expression"))
        sub = index_dto_sub.compose(sub, exp.loc)

        res_type = types.VarType("res-type", opt_loc=exp.loc)
        get_item_dto_sub = dto_list.add_dto(ArrayLikeElementDTO(exp.loc, container_type, res_type, exp.ret_ref))
        sub = get_item_dto_sub.compose(sub, exp.loc)

        return sub, res_type

    else:
        raise NotImplementedError(f"Don't know how to solve types: {exp.desc}")


def model_one_type_spec(
    ctx: "Context", 
    ts: "ast1.BaseTypeSpec", 
    dto_list: "DTOList"
) -> t.Tuple["Substitution", types.BaseType]:
    if ts.wb_type is not None:
        assert isinstance(ts.wb_type, types.BaseType)
        return Substitution.empty, ts.wb_type
    else:
        ts.wb_ctx = ctx
        ts_sub, ts_type = help_model_one_type_spec(ctx, ts, dto_list)
        ts.wb_type = ts_type
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
        if not isinstance(found_definition, TypeDefinition):
            panic.because(
                panic.ExitCode.TyperModelerInvalidIdError,
                f"ID '{ts.name}' does not refer to a type, but was used as one.",
                opt_loc=ts.loc
            )
        sub, def_type = found_definition.scheme.instantiate()
        return sub, def_type

    elif isinstance(ts, ast1.ProcSignatureTypeSpec):
        all_args_sub = Substitution.empty
        all_arg_types = []
        if ts.opt_args_list:
            for opt_arg_name, arg_type in ts.opt_args_list:
                arg_sub, arg_type = model_one_type_spec(ctx, arg_type, dto_list)
                all_args_sub = arg_sub.compose(all_args_sub, ts.loc)
                all_arg_types.append(arg_type)
        ret_sub, ret_type = model_one_type_spec(ctx, ts.ret_ts, dto_list)
        sub = ret_sub.compose(all_args_sub, ts.loc)
        return sub, types.ProcedureType.new(all_arg_types, ret_type, ts.takes_closure)

    elif isinstance(ts, ast1.AdtTypeSpec):
        sub = Substitution.empty
        fields = []
        for field_name, field_ts in ts.fields_list:
            field_sub, field_type = model_one_type_spec(ctx, field_ts, dto_list)
            sub = field_sub.compose(sub, ts.loc)
            fields.append((field_name, field_type))
        if ts.linear_op == ast1.LinearTypeOp.Product:
            return sub, types.StructType(fields)
        elif ts.linear_op == ast1.LinearTypeOp.Sum:
            return sub, types.UnionType(fields)
        else:
            raise NotImplementedError(f"Unknown LinearTypeOp: {ts.linear_op.name}")
    
    elif isinstance(ts, ast1.PtrTypeSpec):
        pointee_sub, pointee_type = model_one_type_spec(ctx, ts.pointee_type_spec, dto_list)
        return pointee_sub, types.PointerType.new(pointee_type, ts.is_mut)
    
    elif isinstance(ts, ast1.ArrayTypeSpec):
        element_sub, element_type = model_one_type_spec(ctx, ts.element_type_spec, dto_list)
        sub = element_sub
        
        count_sub, count_type = model_one_exp(ctx, ts.count_expression, dto_list)
        sub = count_sub.compose(sub, ts.count_expression.loc)

        # NOTE: must run evaluation AFTER modelling so 'ctx' is valid for const IDs
        count_value = interp.evaluate_constant(ts.count_expression)
        count_value_type_encoding = types.UniqueValueType(count_value)
        
        if not isinstance(count_value, int):
            panic.because(
                panic.ExitCode.CompileTimeEvaluationError,
                f"Expected an integer as array count, got: {count_value}",
                opt_loc=ts.count_expression.loc
            )
        if count_value < 0:
            panic.because(
                panic.ExitCode.CompileTimeEvaluationError,
                f"Received a negative value as array count: either overflow or logical error: {count_value}",
                opt_loc=ts.count_expression.loc
            )
        
        add_dto_sub = dto_list.add_dto(IsIntTypeDTO(ts.count_expression.loc, count_type, "array type-spec size"))
        sub = add_dto_sub.compose(sub, ts.count_expression.loc)
        
        return sub, types.ArrayType.new(element_type, count_value_type_encoding, ts.is_mut)

    elif isinstance(ts, ast1.ArrayBoxTypeSpec):
        element_sub, element_type = model_one_type_spec(ctx, ts.element_type_spec, dto_list)
        return element_sub, types.ArrayBoxType.new(element_type, ts.is_mut)

    else:
        raise NotImplementedError(f"Don't know how to solve type-spec: {ts.desc}")


#
# source file typing: part 3: deferred resolution (solving)
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
            if not finished and len(new_dto_list) == len(old_dto_list):
                panic.because(
                    panic.ExitCode.TyperDtoSolverStalledError,
                    f"TYPER: DTOList solution stalled with {len(new_dto_list)} constraints remaining:\n" +
                    '\n'.join(map(str, new_dto_list))
                )

            # applying the substitution:
            Context.apply_sub_everywhere(sub)
            self.update(sub, new_dto_list)
            ast1.WbTypeMixin.apply_sub_everywhere(sub)

    @staticmethod
    def solve_one_iteration(dto_list: t.List["BaseDTO"]) -> t.Tuple[bool, t.List["BaseDTO"], "Substitution"]:
        if len(dto_list) == 0:
            return True, dto_list, Substitution.empty
        
        new_dto_list = []
        sub = Substitution.empty
        all_finished = True
        for dto in dto_list:
            dto_finished, dto_sub = dto.increment_solution()
            if not dto_finished:
                new_dto_list.append(dto)
                all_finished = False
            sub = sub.compose(dto_sub, dto.loc)
        return all_finished, new_dto_list, sub


# DTO = Deferred Type Order
#

class BaseDTO(object, metaclass=abc.ABCMeta):
    """
    Each DTO encodes a type relation of the form `R(arg-type-list...)`
    """

    def __init__(self, loc: fb.ILoc, arg_type_list: t.List[types.BaseType]):
        super().__init__()
        self.loc: fb.ILoc = loc
        self.arg_type_list: t.List[types.BaseType] = arg_type_list

    @abc.abstractmethod
    def increment_solution(self) -> t.Tuple[bool, "Substitution"]:
        pass

    @abc.abstractmethod
    def prefix_str(self):
        pass

    def __str__(self) -> str:
        return f"{self.prefix_str()} @ {self.loc}"

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

    def prefix_str(self):
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
        operand_kind = self.operand_type.kind()
        if self.unary_op == ast1.UnaryOperator.LogicalNot:
            arg_u_sub = unify(self.operand_type, types.IntType.get(1, is_signed=False), opt_loc=self.loc)
            ret_u_sub = unify(self.return_type, types.IntType.get(1, is_signed=False), opt_loc=self.loc)
            return True, ret_u_sub.compose(arg_u_sub)
        elif self.unary_op in (ast1.UnaryOperator.Minus, ast1.UnaryOperator.Plus):
            if self.operand_type.is_var:
                return False, Substitution.empty
            else:
                if operand_kind == types.IntType:
                    if self.operand_type.is_signed:
                        # + <int> => return identity
                        ret_sub = unify(self.operand_type, self.return_type, opt_loc=self.loc)
                        return True, ret_sub
                    else:
                        # + <uint> => return a signed integer of the same width
                        ret_type = types.IntType.get(self.operand_type.width_in_bits, is_signed=True)
                        ret_sub = unify(ret_type, self.return_type, opt_loc=self.loc)
                        return True, ret_sub
                elif operand_kind == types.TypeKind.Float:
                    ret_sub = unify(self.return_type, self.operand_type, opt_loc=self.loc)
                    return True, ret_sub
                else:
                    self.panic_because_invalid_overload()
        elif self.unary_op == ast1.UnaryOperator.Do:
            if self.operand_type.is_var:
                return False, Substitution.empty
            else:
                if operand_kind == types.TypeKind.Procedure:
                    assert isinstance(self.operand_type, types.ProcedureType)
                    if self.operand_type.arg_count != 0:
                        self.panic_because_invalid_overload(more="expected 0-arg procedure")
                    ret_type = self.operand_type.ret_type
                    ret_sub = unify(ret_type, self.return_type, opt_loc=self.loc)
                    return True, ret_sub
                else:
                    self.panic_because_invalid_overload()
        elif self.unary_op == ast1.UnaryOperator.DeRef:
            if self.operand_type.is_var:
                return False, Substitution.empty
            else:
                if operand_kind == types.TypeKind.Pointer:
                    sol_type = self.operand_type.pointee_type
                    return True, unify(sol_type, self.return_type, self.loc)
                else:
                    panic.because(
                        panic.ExitCode.TyperDtoSolverFailedError,
                        f"Invalid argument to unary-'*' (de-ref) operator: expected Pointer type, got: {self.operand_type}",
                        opt_loc=self.loc
                    )
        else:
            raise NotImplementedError(f"Solving one iter for UnaryOpDTO for unary op: {self.unary_op.name}")

    def prefix_str(self):
        return f"{self.unary_op}({self.operand_type})"

    def panic_because_invalid_overload(self, more="see below"):
        panic.because(
            panic.ExitCode.TyperDtoSolverFailedError,
            f"Cannot apply {self.unary_op.name} to argument of type {self.operand_type}: {more}",
            opt_loc=self.loc
        )


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
                    return True, ret_sub.compose(symmetric_args_sub, self.loc)
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
                return True, ret_sub.compose(symmetric_args_sub, self.loc)
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
            l = self.loc
            ret_sub = unify(self.return_type, types.IntType.get(1, is_signed=False), opt_loc=l)
            return True, ret_sub.compose(args_check_sub,l).compose(symmetric_args_sub,l)
        
        else:
            raise NotImplementedError(f"Solving one iter for BinaryOpDTO for binary op: {self.binary_op.name}")
        
    def prefix_str(self):
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

    def prefix_str(self):
        return f"DOT({self.container_type}, {self.key_name}, {self.proxy_ret_type})"


class IsIntTypeDTO(BaseDTO):
    def __init__(self, loc: fb.ILoc, checked_type: types.BaseType, purpose_hint: str):
        super().__init__(loc, [checked_type])
        self.purpose_hint = purpose_hint
    
    @property
    def checked_type(self):
        return self.arg_type_list[0]

    def prefix_str(self):
        return f"INT?({self.checked_type})"

    def increment_solution(self) -> t.Tuple[bool, "Substitution"]:
        if self.checked_type.is_var:
            return True, Substitution.get({self.checked_type: types.IntType.get(64, True)})
        else:
            if self.checked_type.kind() == types.TypeKind.Int:
                assert isinstance(self.checked_type, types.IntType)
                if self.checked_type.is_signed:
                    return True, Substitution.empty
                else:
                    panic.because(
                        panic.ExitCode.TyperDtoSolverFailedError,
                        f"Expected a signed integer, got unsigned: {self.checked_type}",
                        opt_loc=self.loc
                    )
            else:
                panic.because(
                    panic.ExitCode.TyperDtoSolverFailedError,
                    f"Expected an integer datatype for {self.purpose_hint}, got: {self.checked_type}",
                    opt_loc=self.loc
                )


class ArrayLikeElementDTO(BaseDTO):
    def __init__(self, loc, container_type, res_type, ret_ref):
        super().__init__(loc, [container_type, res_type])
        self.ret_ref = ret_ref

    @property
    def container_type(self):
        return self.arg_type_list[0]

    @property
    def res_type(self):
        return self.arg_type_list[1]

    def increment_solution(self) -> t.Tuple[bool, "Substitution"]:
        def is_flat_array_type(t):
            return isinstance(t, (types.ArrayType, types.ArrayBoxType))
        
        is_flat_array = is_flat_array_type(self.container_type)
        if is_flat_array:
            elem_type = self.container_type.element_type

            if not self.ret_ref:
                return True, unify(self.res_type, elem_type, self.loc)
            else:
                return True, unify(self.res_type, types.PointerType.new(elem_type, is_mut=self.container_type.is_mut))

        if isinstance(self.container_type, types.PointerType) and is_flat_array_type(self.container_type.pointee_type):
            array_type = self.container_type.pointee_type
            elem_type = array_type.element_type
            return True, unify(self.res_type, types.PointerType.new(elem_type, is_mut=self.container_type.is_mut))

        return False, Substitution.empty

    def prefix_str(self):
        return f"ARRAYLIKE_ELEMENT({self.container_type}, {self.res_type})"


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
        if t1.is_var and t2.is_var:
            # must ensure eliminations are consistent; 
            #   - always replace with newer type (t1.id > t2.id => var=t1, replacement=t2)
            #   - always replace with older type (t1.id < t2.id => var=t2, replacement=t1)
            # for correctness: solver should be invariant to this: good way to hunt for bugs.
            if t1.id > t2.id:
                var_type = t1
                replacement_type = t2
            else:
                var_type = t2
                replacement_type = t1
        elif t1.is_var:
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

        # checking that other type properties match:
        if t1.kind() == types.TypeKind.Procedure:
            assert isinstance(t1, types.ProcedureType)
            assert isinstance(t2, types.ProcedureType)
            closure_slots_ok = t1.has_closure_slot == t2.has_closure_slot
            if not closure_slots_ok:
                raise_unification_error(t1, t2, opt_more="Cannot unify a procedure type with a closure slot with a procedure type without one", opt_loc=opt_loc)

        # generate a substitution by unifying matching fields:
        s = Substitution.empty
        for ft1, ft2 in zip(t1.field_types, t2.field_types):
            s = unify(
                s.rewrite_type(ft1), 
                s.rewrite_type(ft2),
                opt_loc=opt_loc
            ).compose(s, opt_loc)
        return s

    # any other case: raise a unification error.
    else:
        raise_unification_error(t1, t2, opt_loc=opt_loc)


def raise_unification_error(t: types.BaseType, u: types.BaseType, opt_more=None, opt_loc=None):
    tab_w = 4
    msg_chunks = [f"UNIFICATION_ERROR: Cannot unify {t} and {u}"]
    if opt_more is not None:
        assert isinstance(opt_more, str)
        msg_chunks.append(textwrap.indent(opt_more, ' '*tab_w))
    
    panic.because(panic.ExitCode.TyperUnificationError, '\n'.join(msg_chunks), opt_loc=opt_loc)


#
# Contexts:
#

class ContextKind(enum.Enum):
    BuiltinRoot = enum.auto()
    TopLevelOfQypSet = enum.auto()
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

    def lookup(self, name: str) -> "BaseDefinition":
        """
        Finds a symbol of this name and returns its Definition, else behavior undefined.
        """
        res = self.try_lookup(name)
        assert res is not None
        return res

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

    @staticmethod
    def apply_sub_everywhere(s):
        Context.builtin_root.apply_sub_in_place_to_sub_tree(s)


Context.builtin_root = Context(ContextKind.BuiltinRoot, None)


#
# Definitions:
#

class BaseDefinition(object, metaclass=abc.ABCMeta):
    def __init__(
        self, 
        loc: fb.ILoc, name: str, scm: "Scheme", 
        binder: t.Optional[t.Union[ast1.Bind1vStatement, ast1.Bind1tStatement]], 
        extern_tag=None, is_compile_time_constant=False
    ) -> None:
        super().__init__()
        self.loc = loc
        self.name = name
        self.scheme = scm
        self.bound_in_ctx = None
        self.extern_tag = extern_tag
        self.binder = binder
        self.is_compile_time_constant = is_compile_time_constant

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
        self.oc_sub_map_keys = set(sub_map.keys())

    def compose(self, applied_first: "Substitution", src_loc: fb.ILoc) -> "Substitution":
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
            
            # if a conflict between s1 and s2 occurs, need to ensure s1 and s2 do not diverge.
            intersecting_key_set = set(s1_sub_map.keys()) & set(s2_sub_map.keys())
            if intersecting_key_set:
                offending_intersecting_key_set = {
                    key
                    for key in intersecting_key_set
                    if s1_sub_map[key] != s2_sub_map[key]
                }
                if offending_intersecting_key_set:
                    can_overwrite_lr = all((
                        Substitution.can_overwrite_t1_with_t2(s1_sub_map[key], s2_sub_map[key])
                        for key in offending_intersecting_key_set
                    ))
                    if can_overwrite_lr:
                        return Substitution.get(sub_map=(s1_sub_map | s2_sub_map))
                    
                    # NOTE: this is hacky, and breaks the 'order of propagation' (albeit conservatively)
                    #   (will have to rewrite typer anyway...)
                    can_overwrite_rl = all((
                        Substitution.can_overwrite_t1_with_t2(s2_sub_map[key], s1_sub_map[key])
                        for key in offending_intersecting_key_set
                    ))
                    if can_overwrite_rl:
                        return Substitution.get(sub_map=(s2_sub_map | s1_sub_map))
                    
                    s1_intersect_map = {key: s1_sub_map[key] for key in offending_intersecting_key_set}
                    s2_intersect_map = {key: s2_sub_map[key] for key in offending_intersecting_key_set}
                    panic.because(
                        panic.ExitCode.TyperUnificationError,
                        f"Unification error: conflicting substitutions composed:\n"
                        f"first: {Substitution.get(s1_intersect_map)}\n"
                        f"later: {Substitution.get(s2_intersect_map)}",
                        opt_loc=src_loc
                    )

            return Substitution.get(sub_map=(s1_sub_map | s2_sub_map))

    def __str__(self) -> str:
        return '{' + ','.join((f"{str(key)}->{str(val)}" for key, val in self.sub_map.items())) + '}'

    def __repr__(self) -> str:
        return str(self)

    def rewrite_type(self, t: types.BaseType) -> types.BaseType:
        # optimization: a substitution must map free variables to some type.
        # we can check if 't' contains any of the free variables mapped by this substitution.
        # if not, we just return the type as is.
        assert isinstance(t.oc_free_vars, set)
        if self.oc_sub_map_keys & t.oc_free_vars:
            return self._rewrite_type(t, None)
        else:
            return t

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
        # FIXME: must pass more attributes for types like 'Procedure'
        if isinstance(t, types.BaseCompositeType):
            rt_is_t = False
            new_fields = []
            for element_name, element_type in t.fields:
                rt_field_type = self._rewrite_type(element_type, rw_in_progress_pair_list)
                new_field = (element_name, rt_field_type)
                new_fields.append(new_field)
                rt_is_t |= rt_field_type is not element_type
            if rt_is_t:
                rt = t.copy_with_elements(new_fields)
                if isinstance(t, types.PointerType):
                    rt.contents_is_mut = t.contents_is_mut
                elif isinstance(t, types.ProcedureType):
                    rt.is_c_variadic = t.is_c_variadic
                return rt
            else:
                return t
        
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
            if t1.kind() == t2.kind() and len(t1.fields) == len(t2.fields):
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

    def prefix_str(self) -> str:
        return f"({','.join(map(str, self.vars))})=>{self.body}"


#
# Exceptions:
#

class InfiniteSizeTypeException(BaseException):
    pass

