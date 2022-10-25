from dataclasses import dataclass


@dataclass
class CompilerSettings:
    tmp_root_module_path: str
    output_dir_path: str
