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
        return exp.value
    
    elif isinstance(exp, ast1.BinaryOpExpression):
        return exp.value
    
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

    else:
        panic.because(
            panic.ExitCode.CompileTimeEvaluationError,
            f"Cannot evaluate expression at compile-time: {exp.desc}",
            opt_loc=exp.loc
        )
