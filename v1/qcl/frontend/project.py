import typing as t
import os.path as path

from qcl import typer

from . import file


class Project(object):
    def __init__(self, abs_working_dir_path: str):
        super().__init__()
        self.abs_working_dir_path = abs_working_dir_path
        self.all_sm_map = {}
        self.abs_content_dir_path = None
        self.entry_point_source_module = None
        self.file_module_exp_list = None
        self.all_def_val_rec_list = []
        self.final_root_ctx = None

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

    def set_file_module_exp_list(self, file_module_exp_list):
        assert self.file_module_exp_list is None
        self.file_module_exp_list = file_module_exp_list

    #
    # We store the root context on the project once it is typed:
    #

    def set_final_root_ctx(self, final_root_ctx: "typer.context.Context"):
        self.final_root_ctx = final_root_ctx

    #
    # We store ValDefRecs
    #

    def allocate_val_def_id(self, val_def_rec: "typer.definition.ValueRecord") -> int:
        def_id = len(self.all_def_val_rec_list)
        self.all_def_val_rec_list.append(val_def_rec)
        return def_id

    def count_val_defs(self):
        return len(self.all_def_val_rec_list)
