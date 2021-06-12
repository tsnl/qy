"""
This module manages a single tree of input source files.
"""

import os.path as path

from qcl import parser


class Project(object):
    def __init__(self, abs_working_dir_path: str):
        super().__init__()
        self.abs_working_dir_path = abs_working_dir_path
        self.all_sm_map = {}

    def load_source_module(self, rel_path):
        source_module_path = path.join(self.abs_working_dir_path, rel_path)
        source_module = SourceModule(self, path.normpath(source_module_path))
        return source_module


class SourceModule(object):
    def __init__(self, project, rel_path):
        super().__init__()
        self.project = project
        self.rel_path = rel_path
        self.rel_dir_path, self.file_name = path.split(self.rel_path)
        self.is_qy_source_file = self.file_name.endswith(".qy")

    def load_relative_source_module(self, rel_path_from_self):
        rel_path_from_cwd = path.join(self.rel_dir_path, rel_path_from_self)
        self.project.load_source_module(rel_path_from_cwd)
        return rel_path_from_cwd
