from qcl import ast
from qcl import typer


def check_project(project):
    all_file_module_exp_list = project.file_module_exp_list

    return all((
        check_file_module_exp(file_module_exp)
        for file_module_exp in all_file_module_exp_list
    ))


def check_file_module_exp(file_mod_exp: ast.node.FileModExp):
    return all((
        check_sub_module_exp(sub_mod_name, sub_mod_exp)
        for sub_mod_name, sub_mod_exp in file_mod_exp.sub_module_map.items()
    ))


def check_sub_module_exp(sub_mod_name: str, sub_mod_exp: ast.node.SubModExp):
    typing_locally_only = ensure_tabular_exp_types_own_ids(sub_mod_exp)

    return (
        typing_locally_only
    ) and all((
        check_element(element)
        for element in sub_mod_exp.table.elements
    ))


def check_element(element: ast.node.BaseElem):
    if isinstance(element, ast.node.BaseBindElem):
        pass
    elif isinstance(element, ast.node.BaseTypingElem):
        pass
    elif isinstance(element, ast.node.BaseImperativeElem):
        pass

    return True


def ensure_tabular_exp_types_own_ids(tabular_ast_node):
    # TODO: verify that Type1Elem statements only refer to values defined in this context
    #   - exception: formal args, since they exist in a shell context

    tabular_ast_node.ctx
    tabular_ast_node.ctx.opt_parent_context

    tabular_ast_node.tid

    return True


# TODO: need to check initialization order of all global constants.
#   - this can be achieved by storing a list of dependencies
dependent_bind_elem_map = {}

# TODO: need to compute the closure of each scope/lambda
lambda_exp_closure_ids_map = {}

# TODO: need to validate mutation

# TODO: need to validate
