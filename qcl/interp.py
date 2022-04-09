"""
`interp` handles compile-time evaluation.
This should be run during the typer.
"""

from . import ast1
from . import typer
from . import panic


def evaluate_constant(exp: ast1.BaseExpression):
    if isinstance(exp, (ast1.IntExpression, ast1.FloatExpression, ast1.StringExpression)):
        return exp.value
    
    elif isinstance(exp, ast1.UnaryOpExpression):
        assert exp.operand is not None
        
        operand_value = evaluate_constant(exp.operand)
        try:
            return {
                ast1.UnaryOperator.LogicalNot: lambda: not operand_value,
                ast1.UnaryOperator.Minus: lambda: -operand_value,
                ast1.UnaryOperator.Plus: lambda: +operand_value
            }[exp.operator]()
        except KeyError:
            # error handled below...
            pass

    
    elif isinstance(exp, ast1.BinaryOpExpression):
        assert exp.lt_operand_exp is not None and exp.rt_operand_exp is not None
        
        lt_operand_value = evaluate_constant(exp.lt_operand_exp)
        rt_operand_value = evaluate_constant(exp.rt_operand_exp)
        try:
            return {
                ast1.BinaryOperator.Mul: lambda: lt_operand_value * rt_operand_value,
                ast1.BinaryOperator.Div: lambda: lt_operand_value / rt_operand_value,
                ast1.BinaryOperator.Mod: lambda: lt_operand_value % rt_operand_value,
                ast1.BinaryOperator.Add: lambda: lt_operand_value + rt_operand_value,
                ast1.BinaryOperator.Sub: lambda: lt_operand_value - rt_operand_value,
                ast1.BinaryOperator.LSh: lambda: lt_operand_value << rt_operand_value,
                ast1.BinaryOperator.RSh: lambda: lt_operand_value >> rt_operand_value,
                ast1.BinaryOperator.BitwiseAnd: lambda: lt_operand_value & rt_operand_value,
                ast1.BinaryOperator.BitwiseXOr: lambda: lt_operand_value ^ rt_operand_value,
                ast1.BinaryOperator.BitwiseOr: lambda: lt_operand_value | rt_operand_value,
                ast1.BinaryOperator.LThan: lambda: lt_operand_value < rt_operand_value,
                ast1.BinaryOperator.GThan: lambda: lt_operand_value > rt_operand_value,
                ast1.BinaryOperator.LEq: lambda: lt_operand_value <= rt_operand_value,
                ast1.BinaryOperator.GEq: lambda: lt_operand_value >= rt_operand_value,
                ast1.BinaryOperator.Eq: lambda: lt_operand_value == rt_operand_value,
                ast1.BinaryOperator.NEq: lambda: lt_operand_value != rt_operand_value,
                ast1.BinaryOperator.LogicalAnd: lambda: lt_operand_value and rt_operand_value,
                ast1.BinaryOperator.LogicalOr: lambda: lt_operand_value or rt_operand_value
            }[exp.operator]()
        except KeyError:
            # error handled below...
            pass

    
    elif isinstance(exp, ast1.IdRefExpression):
        def_obj = exp.lookup_def_obj()
    
        if not isinstance(def_obj, typer.ValueDefinition):
            panic.because(
                panic.ExitCode.CompileTimeEvaluationError,
                f"Expected a value ID but received a type ID: {def_obj.name}",
                opt_loc=exp.loc
            )

        if not def_obj.is_compile_time_constant:
            panic.because(
                panic.ExitCode.CompileTimeEvaluationError,
                f"Cannot evaluate non-const ID: {def_obj.name}",
                opt_loc=exp.loc
            )
        
        return evaluate_constant(def_obj.binder.initializer)

    panic.because(
        panic.ExitCode.CompileTimeEvaluationError,
        f"Cannot evaluate expression at compile-time: {exp.desc}",
        opt_loc=exp.loc
    )
