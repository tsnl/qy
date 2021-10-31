import json

from . import config
from . import panic
from . import feedback as fb
from . import ast2


def transpile_one_package_set(path_to_root_qyp_file: str):
    qyp_set = ast2.QypSet.load(path_to_root_qyp_file)
    
    #
    # Debug: printing all loaded modules
    #

    print("INFO: Module summary:")
    for qyp_name, qyp in qyp_set.qyp_name_map.items():
        print(f"- qyp {repr(qyp_name)} @ path({repr(qyp.file_path)})")
        for src_file in qyp.iter_src_paths():
            print(f"  - Qy source file @ path({repr(src_file)})")
