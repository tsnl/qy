"""
This module manages a single tree of input source files.
"""

import functools
import os.path as path

from qcl import parser


class Project(object):
    def __init__(self, abs_working_dir_path: str):
        super().__init__()
        self.abs_working_dir_path = abs_working_dir_path
        self.all_sm_map = {}
        self.abs_content_dir_path = None

    def register_source_module(self, rel_path, is_entry_point=False):
        source_module = self.help_register_source_module(rel_path)

        if is_entry_point:
            assert self.abs_content_dir_path is None
            self.abs_content_dir_path = path.normpath(path.join(
                self.abs_working_dir_path,
                source_module.dir_path_rel_project
            ))

        return source_module

    def help_register_source_module(self, rel_path):
        source_module_path = path.normpath(path.join(self.abs_working_dir_path, rel_path))

        cached_source_module = self.all_sm_map.get(source_module_path, None)
        if cached_source_module is not None:
            return cached_source_module
        else:
            source_module = SourceModule(self, source_module_path)
            self.all_sm_map[source_module_path] = source_module
            return source_module


class SourceModule(object):
    def __init__(self, project, rel_path):
        super().__init__()
        self.project = project
        self.file_path_rel_project = rel_path
        self.file_path = path.normpath(path.join(self.project.abs_working_dir_path, self.file_path_rel_project))
        self.dir_path_rel_project, self.file_name = path.split(self.file_path_rel_project)

    def load_relative_source_module(self, rel_path_from_self):
        rel_path_from_cwd = path.join(self.dir_path_rel_project, rel_path_from_self)
        return self.project.register_source_module(rel_path_from_cwd)


"""
TOOD: add other kinds of source files, e.g. extern linked/loaded files.
"""
