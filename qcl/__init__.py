import json

from . import config
from . import panic
from . import feedback as fb
from . import source


def transpile_one_package(path_to_root_qyp_file: str):
    qyp_set = source.QypSet.load(path_to_root_qyp_file)
    
    #
    # Debug: printing all loaded modules
    #

    print("INFO: Module summary:")
    for qyp_name, qyp in qyp_set.qyp_name_map.items():
        print(f"- qyp {repr(qyp_name)} @ {qyp.file_path}")
