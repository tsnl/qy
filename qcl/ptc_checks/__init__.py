from qcl import ast
from qcl import typer

from . import basic_checks
from . import interp_checks


def run(project):
    # 
    # Basic checks (pre-interpretation)
    #

    basic_checks.run(project)

    #
    # Interpreted checks
    #

    # TODO: check that `TOT`-assignment not misused, i.e.
    #   - check that pointer contents can never be non-local
    #   - rather than SMT analysis, consider logical CFA

    # TODO: implement 'init_order' checks and other passes involving VM interpretation
    #   here...

    # REJECT: for each value_def_rec, must store def recs of any VIDs used in the RHS/initializer expression.
    #       these def recs are 'dependency value def recs' and must be initialized before this def rec.
    #       if a dependency def rec cannot be initialized before the depending def rec, it must be because of
    #       a 'dependency cycle'.
    #   THUS, our goal is to detect 'dependency cycles'. If any exist, compilation exits.
    #       - this is easily accomplished using a DFS or a BFS with a 'visited' set.
    #       - def recs are stored for IdExps on the AST node in the 'typer', which is the first module to 
    #         resolve scoping operations.
    #       - we must first expand the dependencies of each def rec (i.e., the 'edge' set)
    #       - we must check that a def rec's dependency set does not include itself (no reflexivity)

    # TODO: for each value_def_rec, eagerly load all dependencies into the VM
    #   - this must be done after verifying SES-es inductively.

    # # base case: for each ID, add the ValueRecord used to define it.
    # # - if the record is already in the list, skip it.
    # if isinstance(exp, ast.node.IdExp):
    #     rec = exp.found_def_rec
    #     assert isinstance(rec, typer.definition.ValueRecord)
    #     dep_set.add(rec)
    
    # # lambda expressions:
    # #   - the body is not a dependency in general
    # #   - FIXME: what if one initializer calls another function?
    # #   - the only way to reliably do this is to EVALUATE top-level values 
    # elif isinstance(exp, ast.node.LambdaExp):
    #     pass

    interp_checks.run(project)
