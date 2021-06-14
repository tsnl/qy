"""
This module constructs the `fs_scaffold` data-structure.
After it is complete, all parse trees are guaranteed to be in-memory.
"""

from qcl import fs_scaffold
from qcl import excepts

from .dep_dispatch_visitor import DepDispatchVisitor


def build_scaffold_from(project: fs_scaffold.Project, rel_entry_point_path: str):
    if not any((rel_entry_point_path.endswith(ext) for ext in entry_point_extensions)):
        msg_suffix = f"expected entry-point to have any of the following extensions: {entry_point_extensions}"
        raise excepts.DependencyDispatchCompilationError(msg_suffix)
    entry_point_source_module = project.register_source_module(rel_entry_point_path, is_entry_point=True)

    # running a BFS to enumerate files to add to the scaffold:
    source_module_list = [entry_point_source_module]
    index = 0
    while index < len(source_module_list):
        # for each node,
        source_module = source_module_list[index]

        # getting each dependency node...
        dependency_source_module_list = check_dependency_source_module_list_of_source_module(source_module)

        # ...and adding to the BFS queue if not already there,
        for dependency_source_module in dependency_source_module_list:
            if dependency_source_module not in source_module_list:
                source_module_list.append(dependency_source_module)

        # before proceeding to the next node.
        index += 1

    return source_module_list


def check_dependency_source_module_list_of_source_module(parent_sm: fs_scaffold.SourceModule):
    child_sm_list = get_dependency_source_module_list_of_source_module(parent_sm)

    for child_sm in child_sm_list:
        if child_sm.file_path == parent_sm.file_path:
            msg_suffix = f"cannot import a source node from itself: {parent_sm.file_path}"
            raise excepts.DependencyDispatchCompilationError(msg_suffix)
        elif not any((child_sm.file_path.endswith(ext) for ext in source_module_extensions)):
            msg_suffix = f"cannot import a module whose extension is not one of: {source_module_extensions}"
            raise excepts.DependencyDispatchCompilationError(msg_suffix)

    return child_sm_list


def get_dependency_source_module_list_of_source_module(parent_source_module: fs_scaffold.SourceModule):
    visitor = DepDispatchVisitor(parent_source_module)
    visitor.lazily_parse_and_apply()
    return visitor.new_source_module_list


entry_point_extensions = [
    ".qy-app",
    ".qy-lib"
]
source_module_extensions = [
    ".qy"
]
