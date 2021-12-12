"""
`ast2` handles higher-level node organization, like...
- tracking whole source files
- tracking `QypSet`s, or Qy Package sets: groups of interdependent packages
- tracking `Qyp`s, or Qy Packages
- tracking `QySourceFile`s
"""

import os.path
import json
import typing as t
from collections import OrderedDict

from . import panic
from . import feedback as fb
from . import ast1
from . import parser
from . import config

import jstyleson

#
#
# QypSet, Qyp, QySourceFile:
#
#

class QypSet(object):
    @staticmethod
    def load(path_to_root_qyp_file: str) -> t.Optional["QypSet"]:
        # checking input file path:
        if not path_to_root_qyp_file.endswith(config.QYP_FILE_EXTENSION):
            panic.because(
                panic.ExitCode.BadProjectFile,
                f"expected project file path to end with '{config.QYP_FILE_EXTENSION}', got:",
                path_to_root_qyp_file
            )
        if not os.path.isfile(path_to_root_qyp_file):
            panic.because(
                panic.ExitCode.BadProjectFile,
                f"project file path does not refer to a file:",
                path_to_root_qyp_file
            )

        # using a BFS to iteratively construct a second list parallel to an input list of paths
        # NOTE: paths must be absolute to properly detect cycles.
        qyp_path_queue: t.List[str] = [os.path.abspath(path_to_root_qyp_file)]
        qyp_path_queue_parent_list = [None]
        qyp_path_index: int = 0
        qyp_queue: t.List[Qyp] = []
        qyp_name_map: t.OrderedDict[str, "Qyp"] = OrderedDict()
        all_loaded_ok = True
        while qyp_path_index < len(qyp_path_queue):
            # acquiring the next path to load, loading a Qyp
            opt_parent_path = qyp_path_queue_parent_list[qyp_path_index]
            qyp_path_to_load = qyp_path_queue[qyp_path_index]
            loader_map = {
                config.QYP_FILE_EXTENSION: Qyp.load,
                config.QYX_FILE_EXTENSION: Qyx.load
            }
            for loader_ext, loader_fun in loader_map.items():
                if qyp_path_to_load.endswith(loader_ext):
                    loaded_qyp = loader_fun(qyp_path_to_load)
                    break
            else:
                more = ""
                for wrong_ext in config.WRONG_QYP_LIKE_EXTENSIONS:
                    if qyp_path_to_load.endswith(wrong_ext):
                        more += f"... received wrong/incomplete extension '{wrong_ext}'.\n"
                        break
                expected_exts = loader_map.keys()
                expected_exts_desc = ', '.join((f"'{expected_ext}'" for expected_ext in expected_exts))
                more += f"... expected extensions: {expected_exts_desc}\n"
                more += f"... see file:"
                panic.because(
                    panic.ExitCode.BadProjectFile,
                    f"Dependency '{qyp_path_to_load}' does not have a valid extension.\n{more}",
                    opt_file_path=opt_parent_path
                )
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
                        qyp_path_queue_parent_list.append(qyp_path_to_load)
                        qyp_path_queue.append(target_path)

            # incrementing the index into the path queue:
            qyp_path_index += 1

        if all_loaded_ok:
            return QypSet(qyp_queue[0], qyp_name_map)
        else:
            return None

    def __init__(self, root_qyp: "Qyp", qyp_name_map: t.OrderedDict[str, "Qyp"]) -> None:
        super().__init__()
        self.qyp_name_map = qyp_name_map
        self.root_qyp = root_qyp

    def iter_source_files(self) -> t.Iterable[t.Tuple[str, str, "QySourceFile"]]:
        for qyp_name, qyp in self.qyp_name_map.items():
            assert isinstance(qyp, Qyp)
            for src_file_path, qy_source_file in qyp.src_map.items():
                yield qyp_name, src_file_path, qy_source_file


class Qyp(object):
    @staticmethod
    def load(path_to_root_qyp_file: str) -> "Qyp":
        try:
            with open(path_to_root_qyp_file, "r") as project_file:
                js_map = jstyleson.load(project_file)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            panic.because(
                panic.ExitCode.BadProjectFile,
                f"failed to parse project file: {exc} in:",
                path_to_root_qyp_file,
                # fb.FileSpan(fb.FilePos(exc.lineno - 1, exc.colno - 1))
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
                f"project file missing {len(missing_keys)} top-level key-value pair(s) {missing_keys_str}"
            )

        # checking no extra keys are present, panic otherwise:
        extra_keys = provided_props_set - package_supported_keys
        if extra_keys:
            extra_keys_str = ', '.join(map(repr, extra_keys))
            panic.because(
                panic.ExitCode.BadProjectFile,
                f"project file has {len(extra_keys)} extra key(s): {extra_keys_str}"
            )

        # args look OK!

        # loading each source file, checking for duplicates or errors:
        qyp_dir_path = os.path.dirname(path_to_root_qyp_file)
        src_map = {}
        for rel_src_file_path in js_map["src"]:
            abs_src_file_path = os.path.abspath(os.path.join(qyp_dir_path, rel_src_file_path))

            if abs_src_file_path in src_map:
                panic.because(
                    panic.ExitCode.BadProjectFile,
                    f"Source file added multiple times to project: {path_to_root_qyp_file}\nSource file path:",
                    opt_file_path=abs_src_file_path
                )

            if not os.path.isfile(abs_src_file_path):
                panic.because(
                    panic.ExitCode.BadProjectFile,
                    f"Source file reference does not exist: {repr(rel_src_file_path)}",
                    opt_file_path=abs_src_file_path
                )

            src_map[abs_src_file_path] = QySourceFile.load(abs_src_file_path)

        # create a Qy project (Qyp)
        return Qyp(
            path_to_root_qyp_file,
            qyp_dir_path,
            js_map["name"],
            js_map["author"],
            js_map["help"],
            js_map["src"],
            js_map.get("deps", []),
            src_map
        )

    def __init__(
        self,
        qyp_file_path: str, dir_path: str,
        name: str, author: str, project_help: str,
        src_list: t.List[str],
        dep_list: t.List[str],
        src_map: t.Dict[str, "QySourceFile"]
    ) -> None:
        """
        WARNING: Do not instantiate this class directly.
        Instead, invoke `Qyp.load`
        """
        super().__init__()
        self.file_path = qyp_file_path
        self.dir_path = dir_path
        self.js_name = name
        self.js_author = author
        self.js_help = project_help
        self.js_src_list = src_list
        self.js_dep_list = dep_list
        self.src_map = src_map

    def iter_src_paths(self):
        yield from self.js_src_list


class Qyx(Qyp):
    """
    A 'Qyx' is a 'Qyp' that contains code from another language.
    It is also known as an extension package.
    """
    pass


package_required_keys = {
    "name", "author", "help", "src"
}
package_optional_keys = {
    "deps"
}
package_supported_keys = package_required_keys | package_optional_keys


class QySourceFile(object):
    @staticmethod
    def load(source_file_path: str) -> "QySourceFile":
        if not source_file_path.endswith(config.SOURCE_FILE_EXTENSION):
            panic.because(
                panic.ExitCode.BadProjectFile, 
                f"expected source file path to end with '{config.SOURCE_FILE_EXTENSION}', got:", 
                source_file_path
            )
        if not os.path.isfile(source_file_path):
            panic.because(
                panic.ExitCode.BadProjectFile,
                f"source file path does not refer to a file:",
                source_file_path
            )
        stmt_list = parser.parse_one_file(source_file_path)
        return QySourceFile(source_file_path, stmt_list)

    def __init__(self, source_file_path: str, stmt_list: t.List[ast1.BaseStatement]):
        super().__init__()
        self.file_path = source_file_path
        self.stmt_list = stmt_list

        # writeback properties: properties computed over the course of evaluation and 'written back' for later:
        self.wb_typer_ctx = None
