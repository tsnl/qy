from os import path


class FileModuleSource(object):
    def __init__(self, project, rel_path):
        super().__init__()
        self.project = project
        self.file_path_rel_cwd = rel_path
        self.file_path = path.normpath(path.join(self.project.abs_working_dir_path, self.file_path_rel_cwd))
        self.dir_path_rel_project, self.file_name = path.split(self.file_path_rel_cwd)
        self.ast_file_mod_exp_from_frontend = None

    def load_relative_source_module(self, import_name: str, rel_path_from_self: str):
        rel_path_from_cwd = path.join(self.dir_path_rel_project, rel_path_from_self)
        source_module = self.project.register_source_module(rel_path_from_cwd)
        self.ast_file_mod_exp_from_frontend.imports_source_map_from_frontend[import_name] = source_module
        return source_module
