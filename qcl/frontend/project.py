from typing import *
from os import path

from . import file


class Project(object):
    def __init__(self, abs_working_dir_path: str):
        super().__init__()
        self.abs_working_dir_path = abs_working_dir_path
        self.all_sm_map = {}
        self.abs_content_dir_path = None
        self.entry_point_source_module = None

    def register_source_module(self, rel_path, is_entry_point=False):
        source_module = self.help_register_source_module(rel_path)

        if is_entry_point:
            assert self.entry_point_source_module is None
            self.entry_point_source_module = source_module

            assert self.abs_content_dir_path is None
            self.abs_content_dir_path = path.normpath(path.join(
                self.abs_working_dir_path,
                source_module.dir_path_rel_project
            ))

        return source_module

    def help_register_source_module(self, rel_path):
        # source_module_path = path.normpath(path.join(self.abs_working_dir_path, rel_path))
        source_module_path = path.normpath(rel_path)

        cached_source_module = self.all_sm_map.get(source_module_path, None)
        if cached_source_module is not None:
            return cached_source_module
        else:
            source_module = file.FileModuleSource(self, source_module_path)
            self.all_sm_map[source_module_path] = source_module
            return source_module
