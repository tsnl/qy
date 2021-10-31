"""
This module handles...
- tracking individual source files
- tracking `Qyp`s, or Qy Packages
- tracking `QypSet`s, or Qy Package sets: groups of interdependent packages
"""

import os.path
import json
import typing as t
from collections import OrderedDict

from . import panic
from . import feedback as fb


class QypSet(object):
    @staticmethod
    def load(path_to_root_qyp_file: str) -> t.Optional["QypSet"]:
        # using a BFS to iteratively construct a second list parallel to an input list of paths
        # NOTE: paths must be absolute to properly detect cycles.
        qyp_path_queue: t.List[str] = [os.path.abspath(path_to_root_qyp_file)]
        qyp_path_index: int = 0
        qyp_queue: t.List[Qyp] = []
        qyp_name_map: t.OrderedDict[str, "Qyp"] = OrderedDict()
        all_loaded_ok = True
        while qyp_path_index < len(qyp_path_queue):
            # acquiring the next path to load, loading a Qyp
            qyp_path_to_load = qyp_path_queue[qyp_path_index]
            loaded_qyp = Qyp.load(qyp_path_to_load)
            qyp_queue.append(loaded_qyp)

            # complaining if the loaded qyp has the same name as another we've already loaded:
            if loaded_qyp.js_name in qyp_name_map:
                old_qyp = qyp_name_map[loaded_qyp.js_name]
                print(f"ERROR: qyp {repr(loaded_qyp.js_name)} already exists at path {old_qyp.js_name}")
                all_loaded_ok = False
            else:
                qyp_name_map[loaded_qyp.js_name] = loaded_qyp

            # adding all dependency paths:
            for dep_index, dep_path in enumerate(loaded_qyp.js_dep_list):
                if dep_path.startswith("https://"):
                    panic.because(
                        panic.ExitCode.BadProjectFile,
                        f"Dependency path cannot start with 'https://': see 'deps' item {1 + dep_index}: {dep_path}\n"
                        r"(this will be implemented in the future)",
                        qyp_path_to_load
                    )
                elif dep_path.startswith("/"):
                    panic.because(
                        panic.ExitCode.BadProjectFile,
                        f"Dependency path cannot start with '/': see 'deps' item {1 + dep_index}: {dep_path}",
                        qyp_path_to_load
                    )
                else:
                    # relative path
                    target_path = os.path.abspath(os.path.join(loaded_qyp.dir_path, dep_path))
                    if target_path not in qyp_path_queue:
                        qyp_path_queue.append(target_path)

            # incrementing the index into the path queue:
            qyp_path_index += 1

        if all_loaded_ok:
            return QypSet(qyp_name_map)
        else:
            return None

    def __init__(self, qyp_name_map: t.OrderedDict[str, "Qyp"]) -> None:
        super().__init__()
        self.qyp_name_map = qyp_name_map


class Qyp(object):
    @staticmethod
    def load(path_to_root_qyp_file: str) -> "Qyp":
        try:
            with open(path_to_root_qyp_file, "r") as project_file:
                js_map = json.load(project_file)
        except json.decoder.JSONDecodeError as exc:
            panic.because(
                panic.ExitCode.BadProjectFile,
                f"failed to parse project file: {exc.msg} in:",
                path_to_root_qyp_file,
                fb.Span(fb.Loc(exc.lineno-1, exc.colno-1))
            )

        # basic error checking: still need owner to query and report for us
        provided_props_set = set(js_map.keys())
        
        # checking all required keys are present, panic otherwise:
        missing_keys = []
        for supported_key in package_required_keys:
            if supported_key not in provided_props_set:
                missing_keys.append(supported_key)
        if missing_keys:
            missing_keys_str = ', '.join(map(repr, missing_keys))
            panic.because(
                panic.ExitCode.BadProjectFile,
                f"project file missing {len(missing_keys)} top-level key-value pairs {missing_keys_str}"
            )
        
        # checking no extra keys are present, panic otherwise:
        extra_keys = provided_props_set - package_supported_keys
        if extra_keys:
            extra_keys_str = ', '.join(map(repr, extra_keys))
            panic.because(
                panic.ExitCode.BadProjectFile,
                f"project file has {len(missing_keys)} extra keys: {extra_keys_str}"
            )

        # args look OK! Create a Qy project (Qyp)
        return Qyp(
            path_to_root_qyp_file,
            js_map["name"],
            js_map["author"],
            js_map["help"],
            js_map["src"],
            js_map.get("deps", [])
        )

    def __init__(
        self, 
        qyp_file_path, 
        name: str, author: str, help: str, 
        src_list: t.List[str], 
        dep_list: t.List[str]
    ) -> None:
        """
        WARNING: Do not instantiate this class directly.
        Instead, invoke `Qyp.load`
        """
        super().__init__()
        self.file_path = qyp_file_path
        self.dir_path = os.path.dirname(qyp_file_path)
        self.js_name = name
        self.js_author = author
        self.js_help = help
        self.js_src_list = src_list
        self.js_dep_list = dep_list


package_required_keys = {
    "name", "author", "help", "src"
}
package_optional_keys = {
    "deps"
}
package_supported_keys = package_required_keys | package_optional_keys
