"""
`ast2` handles higher-level node organization, like...
- tracking whole source files
- tracking `QypSet`s, or Qy Package sets: groups of interdependent packages
- tracking `Qyp`s, or Qy Packages
- tracking `QySourceFile`s

Qy packages have grown to encompass different inputs.
BaseQyp is a base qy package: it includes...
-   `Qyp`s: native Qy packages
-   `Qyx`s: Qy extension packages
    - `CQyx`s: Qy extensions using C source code and C-level object files
"""

import abc
import functools
import os.path
import json
import typing as t
import sys
from collections import OrderedDict

from . import panic
from . import feedback as fb
from . import ast1
from . import qy_parser
from . import c_parser
from . import config
from . import platform

import jstyleson as jsonc

#
#
# QypSet, Qyp, QySourceFile:
#
#

class QypSet(object):
    @staticmethod
    def load(path_to_root_qyp_file: str, target_platform: platform.CorePlatform) -> t.Optional["QypSet"]:
        # checking input file path:
        if not path_to_root_qyp_file.endswith(config.QYP_FILE_EXTENSION):
            panic.because(
                panic.ExitCode.BadProjectFile,
                f"expected root project file path to end with '{config.QYP_FILE_EXTENSION}', but got:",
                path_to_root_qyp_file
            )
        if not os.path.isfile(path_to_root_qyp_file):
            panic.because(
                panic.ExitCode.BadProjectFile,
                f"project file path does not refer to a file:",
                path_to_root_qyp_file
            )

        # using a BFS to iteratively construct a second list of objects parallel to the input list of paths
        # NOTE: paths must be absolute to properly detect cycles.
        # NOTE: we maintain a third parallel list with the parent node for each qyp to load
        qyp_path_queue: t.List[str] = [os.path.abspath(path_to_root_qyp_file)]
        qyp_path_queue_parent_list = [None]
        qyp_path_index: int = 0
        qyp_queue: t.List[NativeQyp] = []
        qyp_name_map: t.OrderedDict[str, "NativeQyp"] = OrderedDict()
        all_loaded_ok = True
        while qyp_path_index < len(qyp_path_queue):
            # acquiring the next path to load:
            opt_parent_path = qyp_path_queue_parent_list[qyp_path_index]
            qyp_path_to_load = qyp_path_queue[qyp_path_index]
            
            # loading the qyp:
            loader_map = {
                config.QYP_FILE_EXTENSION: NativeQyp.load,
                config.QYX_FILE_EXTENSION: CQyx.load
            }
            for loader_ext, loader_fun in loader_map.items():
                if qyp_path_to_load.endswith(loader_ext):
                    # using this loader to load the qyp/qyx at this path:
                    loaded_qyp = loader_fun(qyp_path_to_load, target_platform)
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

            # complaining if the loaded qyp has the same name as another we've already loaded;
            # otherwise, adding the Qyp to the `qyp_name_map`
            if loaded_qyp.js_name in qyp_name_map:
                old_qyp = qyp_name_map[loaded_qyp.js_name]
                print(f"ERROR: qyp {repr(loaded_qyp.js_name)} already exists at path {old_qyp.js_name}")
                all_loaded_ok = False
            else:
                qyp_name_map[loaded_qyp.js_name] = loaded_qyp

            # adding all dependency paths:
            # NOTE: 'qsl' or Qy standard library is always a dependency
            for dep_index, dep_path in enumerate(loaded_qyp.js_dep_path_list):
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
                elif dep_path.startswith("$"):
                    # builtin path
                    p = dep_path[1:]
                    assert os.path.isfile(p)
                    target_path = os.path.abspath(p)
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

    def __init__(self, root_qyp: "NativeQyp", qyp_name_map: t.OrderedDict[str, "BaseQyp"]) -> None:
        super().__init__()
        self.qyp_name_map = qyp_name_map
        self.root_qyp = root_qyp

    # def iter_native_src_paths(self) -> t.Iterable[t.Tuple[str, str, "QySourceFile"]]:
    #     for qyp_name, qyp in self.qyp_name_map.items():
    #         if isinstance(qyp, NativeQyp):
    #             for src_file_path, qy_source_file in qyp.qy_src_map.items():
    #                 yield qyp_name, src_file_path, qy_source_file

    def iter_src_paths(self) -> t.Iterable[t.Tuple[str, str, "BaseSourceFile"]]:
        for qyp_name, qyp in self.qyp_name_map.items():
            for src_file_path, source_file in qyp.src_map.items():
                yield qyp_name, src_file_path, source_file
        

class BaseQyp(object, metaclass=abc.ABCMeta):
    def __init__(
        self,
        qyp_file_path: str, dir_path: str,
        name: str, author: str, project_help: str,
        any_src_path_list: t.List[str],
        dep_path_list: t.List[str],
        src_map: t.Dict[str, "BaseSourceFile"]
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
        self.src_path_list = any_src_path_list
        self.js_dep_path_list = dep_path_list
        self.src_map = src_map

    @staticmethod
    def panic_because_bad_keys(path_to_root_qyp_file, missing_keys):
        missing_keys_str = ', '.join(map(repr, missing_keys))
        panic.because(
            panic.ExitCode.BadProjectFile,
            f"Qyp/Qyx project file missing {len(missing_keys)} top-level key-value pair(s) {missing_keys_str}",
            opt_file_path=path_to_root_qyp_file
        )
    
    @staticmethod
    def panic_because_bad_project_file(path_to_file, exc):
        panic.because(
            panic.ExitCode.BadProjectFile,
            f"failed to parse project file: {exc} in:",
            path_to_file,
            fb.FileSpan(fb.FilePos(exc.lineno-1, exc.colno-1)) if isinstance(exc, json.JSONDecodeError) else None
        )

    @abc.abstractmethod
    def iter_native_src_paths(self):
        pass
    

class NativeQyp(BaseQyp):
    @staticmethod
    def load(path_to_root_qyp_file: str, target_platform: platform.CorePlatform) -> "NativeQyp":
        try:
            with open(path_to_root_qyp_file, "r") as project_file:
                js_map = jsonc.load(project_file)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            NativeQyp.panic_because_bad_project_file(path_to_root_qyp_file, exc)

        # basic error checking: still need owner to query and report for us
        provided_props_set = set(js_map.keys())

        # checking all required keys are present, panic otherwise:
        missing_keys = qyp_required_keys - provided_props_set
        if missing_keys:
            NativeQyp.panic_because_bad_keys(path_to_root_qyp_file, missing_keys)

        # checking no extra keys are present, panic otherwise:
        extra_keys = provided_props_set - qyp_supported_keys
        if extra_keys:
            extra_keys_str = ', '.join(map(repr, extra_keys))
            panic.because(
                panic.ExitCode.BadProjectFile,
                f"project file has {len(extra_keys)} extra key(s): {extra_keys_str}",
                opt_file_path=path_to_root_qyp_file
            )

        # args look OK!

        # logging:
        print(f"INFO: Loading Qyp: {path_to_root_qyp_file}")

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
                    f"Source file reference does not exist or is not a file: {repr(rel_src_file_path)}",
                    opt_file_path=abs_src_file_path
                )

            src_map[abs_src_file_path] = QySourceFile.load(abs_src_file_path)

        # create a Qy project (Qyp)
        return NativeQyp(
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
        qy_src_path_list: t.List[str],
        dep_path_list: t.List[str],
        qy_src_map: t.Dict[str, "QySourceFile"]
    ) -> None:
        """
        WARNING: Do not instantiate this class directly.
        Instead, invoke `Qyp.load`
        """
        super().__init__(qyp_file_path, dir_path, name, author, project_help, qy_src_path_list, dep_path_list, qy_src_map)
        
        # every native Qyp depends on QSL
        self.js_dep_path_list.append(qsl_qyp_dep_path)

    def iter_native_src_paths(self):
        return iter(self.src_path_list)


class BaseQyx(BaseQyp, metaclass=abc.ABCMeta):
    """
    A 'Qyx' is a 'Qyp' that contains code from another language.
    It is also known as an extension package.
    """

    @classmethod
    def load(cls, path_to_root_qyx_file: str, target_platform: platform.CorePlatform) -> "BaseQyx":
        try:
            with open(path_to_root_qyx_file, "r") as project_file:
                js_map = jsonc.load(project_file)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            BaseQyp.panic_because_bad_project_file(path_to_root_qyx_file, exc)

        # basic error checking: still need owner to query and report for us
        provided_props_set = set(js_map.keys())

        # checking all required keys are present, panic otherwise:
        missing_keys = []
        for supported_key in qyx_required_keys:
            if supported_key not in provided_props_set:
                missing_keys.append(supported_key)
        if missing_keys:
            missing_keys_str = ', '.join(map(repr, missing_keys))
            panic.because(
                panic.ExitCode.BadProjectFile,
                f"Qyx project file missing {len(missing_keys)} top-level key-value pair(s) {missing_keys_str}",
                opt_file_path=path_to_root_qyx_file
            )

        # checking for more required keys and extra keys depends on the extension language, and is handled later.
        qyx_dir_path = os.path.dirname(path_to_root_qyx_file)
        
        # args look OK!

        # logging:
        print(f"INFO: Loading Qyx: {path_to_root_qyx_file}")

        # dispatching to language-specific loaders:
        lang = js_map["binder"].upper()
        if lang == 'C-V1':
            return cls.load_ext(target_platform, js_map, path_to_root_qyx_file, qyx_dir_path, lang)
        else:
            panic.because(
                panic.ExitCode.BadProjectFile,
                f"Unknown language in Qyx: {repr(lang)}"
            )
        
    @classmethod
    @abc.abstractmethod
    def load_ext(cls, target_platform, js_map, path_to_root_qyx_file, qyx_dir_path, language):
        raise NotImplementedError("BaseQyx.load_ext: This method should be overridden before invocation.")

    def iter_native_src_paths(self):
        return iter(())
        
    def __init__(
        self,
        qyp_file_path: str, dir_path: str,
        name: str, author: str, project_help: str,
        src_list: t.List[str],
        dep_path_list: t.List[str],
        src_map
    ) -> None:
        """
        WARNING: Do not instantiate this class directly.
        Instead, invoke `<Lang>Qyx.load`
        """
        super().__init__(qyp_file_path, dir_path, name, author, project_help, src_list, dep_path_list, src_map)



class CQyx(BaseQyx):
    required_keys = {"cc-args"}

    def __init__(
        self, 
        qyp_file_path: str, 
        dir_path: str, 
        name: str, 
        author: str, 
        project_help: str, 
        src_path_list: t.List[str], 
        dep_path_list: t.List[str],
        c_source_files: t.List["CSourceFile"]
    ) -> None:
        super().__init__(qyp_file_path, dir_path, name, author, project_help, src_path_list, dep_path_list, dict(zip(src_path_list, c_source_files)))
        self.c_source_files = c_source_files

    @classmethod
    def load_ext(cls, target_platform, js_map, path_to_root_qyx_file, qyx_dir_path, binder_name):
        assert binder_name == 'C-V1'
        assert isinstance(target_platform, platform.Platform)

        missing_keys = CQyx.required_keys - set(js_map.keys())
        if missing_keys:
            CQyx.panic_because_bad_keys(path_to_root_qyx_file, missing_keys)

        # extracting args from cc-args object:
        # NOTE: only a few core platforms are supported right now. This can be expanded in the future.

        c_compiler_args_obj = js_map["cc-args"]
        CQyx.check_args_obj("cc-args", c_compiler_args_obj, {"*"}, platform.core_platform_names)
        raw_common_args = c_compiler_args_obj["*"]
        common_args = CQyxV1_CompilerArgs.from_json_obj(path_to_root_qyx_file, target_platform, raw_common_args)

        platform_args_map = {}
        for platform_name in platform.core_platform_names:
            raw_platform_args = c_compiler_args_obj.get(platform_name, None)
            if raw_platform_args is not None:
                platform_args = CQyxV1_CompilerArgs.from_json_obj(path_to_root_qyx_file, target_platform, raw_platform_args)
                platform_args_map[platform.Platform.name_map[platform_name].core_platform_type] = platform_args

        selected_platform_args = platform_args_map.get(target_platform.core_platform_type, CQyxV1_CompilerArgs.default)
        headers_objs = common_args.headers + selected_platform_args.headers
        sources_objs = common_args.sources + selected_platform_args.sources

        # loading headers in 2 parallel lists:
        header_c_source_files = []
        header_src_path_list = []
        for index, include_obj in enumerate(headers_objs):
            include_path = include_obj.path
            CQyx.check_obj_is_str_else_panic(f"includes[{index}].path", include_path, path_to_root_qyx_file)
            provided_symbol_list = include_obj.provides
            CQyx.check_obj_is_all_str_list_else_panic(f"includes[{index}].path", provided_symbol_list, path_to_root_qyx_file)
            abs_include_path = include_path if os.path.isabs(include_path) else os.path.join(qyx_dir_path, include_path)
            abs_include_path = os.path.normpath(abs_include_path)
            c_source_file = CSourceFile.load(abs_include_path, provided_symbol_list, is_header=True)
            header_c_source_files.append(c_source_file)
            header_src_path_list.append(abs_include_path)

        # loading implementation sources (just referenced, never read) in 2 parallel lists:
        impl_c_source_files = []
        impl_src_path_list = []
        for index, src_obj in enumerate(sources_objs):
            src_path = src_obj
            CQyx.check_obj_is_str_else_panic(f"sources[{index}]", src_path, path_to_root_qyx_file)
            abs_src_path = src_path if os.path.isabs(src_path) else os.path.join(qyx_dir_path, src_path)
            abs_src_path = os.path.normpath(abs_src_path)
            c_source_file = CSourceFile.load(abs_src_path, [], is_header=False)
            impl_c_source_files.append(c_source_file)
            impl_src_path_list.append(abs_src_path)

        # combining headers and sources:
        c_source_files = header_c_source_files + impl_c_source_files
        src_path_list = header_src_path_list + impl_src_path_list

        # checking that all symbols claimed to be provided in the JSON were found:
        all_provided_symbols = functools.reduce(
            lambda a, b: a | b, 
            (set(csf.this_file_provided_symbol_set) for csf in header_c_source_files)
        )
        missing_symbols = set(provided_symbol_list) - all_provided_symbols
        if missing_symbols:
            panic.because(
                panic.ExitCode.CompilationFailed,
                f"CQyx: could not find all provided symbols in project file when scanning headers. Missing symbols:\n" +
                '- ' + '\n- '.join(sorted(missing_symbols)),
                opt_file_path=path_to_root_qyx_file
            )
        
        # returning:
        return CQyx(
            path_to_root_qyx_file,
            qyx_dir_path,
            js_map["name"],
            js_map["author"],
            js_map["help"],
            src_path_list,
            js_map.get("deps", []),
            c_source_files
        )

    @staticmethod
    def check_binder_args_obj(top_level_key, arg_obj, required_per_obj_keys):
        if not isinstance(arg_obj, list):
            panic.because(
                panic.ExitCode.BadProjectFile,
                f"Qyx: in object mapped to '{top_level_key}': expected mapped value to be a list of objects, got:\n"
                f"{repr(arg_obj)}"
            )
        
        for index, include_obj in enumerate(arg_obj):
            CQyx.check_args_obj(f"{top_level_key}[{index}]", include_obj, required_per_obj_keys, set())

    @staticmethod
    def check_args_obj(top_level_key, args_obj, required_keys, optional_keys):
        provided_keys = set(args_obj.keys())
        missing_keys = required_keys - provided_keys
        extra_keys = provided_keys - required_keys - optional_keys
        
        if missing_keys:
            panic.because(
                panic.ExitCode.BadProjectFile,
                f"Qyx: in object mapped to '{top_level_key}': missing {len(missing_keys)} keys:\n"
                f"missing keys: " + ', '.join(map(repr, missing_keys))
            )
        if extra_keys:
            panic.because(
                panic.ExitCode.BadProjectFile,
                f"Qyx: in object mapped to 'binder-args': {len(extra_keys)} unused keys:\n"
                f"unused keys: " + ', '.join(map(repr, extra_keys))
            )    
        
    @staticmethod
    def check_obj_is_str_else_panic(usage: str, obj: object, path_to_file: str):
        if not isinstance(obj, str):
            panic.because(
                panic.ExitCode.BadProjectFile,
                f"Invalid args to '{usage}': expected a single string literal",
                opt_file_path=path_to_file
            )

    @staticmethod
    def check_obj_is_all_str_list_else_panic(usage: str, obj: object, path_to_file: str):
        if not isinstance(obj, list) or not all((isinstance(it, str) for it in obj)):
            panic.because(
                panic.ExitCode.BadProjectFile,
                f"Invalid args to '{usage}': expected a list of string literals",
                opt_file_path=path_to_file
            )


class CQyxV1_CompilerArgs(object):
    default = None
    
    @staticmethod
    def from_json_obj(path_to_root_qyx_file, target_platform, json_obj):
        usage_prefix = f"cc-args[{repr(target_platform.name)}]"
        CQyx.check_args_obj(
            usage_prefix, json_obj, set(), 
            {"c-flags", "sources", "headers"}
        )

        # parsing 'c-flags' field:
        c_flags = []
        opt_c_flags_obj = json_obj.get("c-flags", None)
        if opt_c_flags_obj is not None:
            CQyx.check_obj_is_all_str_list_else_panic(
                f"{usage_prefix}.c-flags",
                opt_c_flags_obj,
                path_to_root_qyx_file
            )
            c_flags = opt_c_flags_obj

        # parsing 'sources' field:
        sources = []
        opt_sources_obj = json_obj.get("sources", None)
        if opt_sources_obj is not None:
            CQyx.check_obj_is_all_str_list_else_panic(
                f"{usage_prefix}.sources",
                opt_sources_obj,
                path_to_root_qyx_file
            )
            sources = opt_sources_obj

        # parsing 'headers' field:
        headers = []
        opt_headers_obj = json_obj.get("headers", None)
        if opt_headers_obj is not None:
            headers = [
                CQyxV1_CompilerArgs_Header.from_json_obj(path_to_root_qyx_file, target_platform, json_header_obj, header_obj_index)
                for header_obj_index, json_header_obj in enumerate(opt_headers_obj)
            ]
        
        # tying it together:
        return CQyxV1_CompilerArgs(c_flags, sources, headers)
        
    def __init__(
        self, 
        c_flags: t.List[str],
        sources: t.List[str],
        headers: "CQyxV1_CompilerArgs_Header"
    ) -> None:
        """
        WARNING: do not invoke this constructor directly: instead, use `from_json_obj`
        """
        super().__init__()
        self.c_flags = c_flags
        self.sources = sources
        self.headers = headers

CQyxV1_CompilerArgs.default = CQyxV1_CompilerArgs([], [], [])


class CQyxV1_CompilerArgs_Header(object):
    @staticmethod
    def from_json_obj(path_to_root_qyx_file, target_platform, json_obj, header_index: int):
        usage_prefix = f"cc-args.{target_platform.name}.headers[{header_index}]"
        CQyx.check_args_obj(
            usage_prefix, json_obj, set(), 
            {"path", "provides"}
        )
        
        opt_path_obj = json_obj.get("path", None)
        if opt_path_obj is not None:
            CQyx.check_obj_is_str_else_panic(f"{usage_prefix}.path", opt_path_obj, path_to_root_qyx_file)
        
        opt_provides_obj = json_obj.get("provides", None)
        if opt_provides_obj is not None:
            CQyx.check_obj_is_all_str_list_else_panic(f"{usage_prefix}.provides", opt_provides_obj, path_to_root_qyx_file)
        
        return CQyxV1_CompilerArgs_Header(json_obj["path"], json_obj["provides"])

    def __init__(self, path: str, provides: t.List[str]):
        super().__init__()
        self.path = path
        self.provides = provides


base_qyp_required_keys = {
    "name", "author", "help"
}
base_qyp_optional_keys = {
    "deps"
}

qyp_required_keys = base_qyp_required_keys | {"src"}
qyp_optional_keys = base_qyp_optional_keys

qyp_supported_keys = qyp_required_keys | qyp_optional_keys

qyx_required_keys = base_qyp_required_keys | {"binder"}
qyx_optional_keys = base_qyp_optional_keys


#
#
# Source files
#
#

class BaseSourceFile(object, metaclass=abc.ABCMeta):
    def __init__(self, source_file_path: str, stmt_list: t.List[ast1.BaseStatement]) -> None:
        assert all((isinstance(it, ast1.BaseStatement) for it in stmt_list))
        assert os.path.isabs(source_file_path)
        
        super().__init__()
        self.file_path = source_file_path
        self.stmt_list = stmt_list

        # writeback properties: properties computed over the course of evaluation and 'written back' for later:
        self.wb_typer_ctx = None

        self.extern_str = self.get_extern_str()

    @classmethod
    @abc.abstractmethod
    def get_extern_str(cls) -> t.Optional[str]:
        return None


class QySourceFile(BaseSourceFile):
    @staticmethod
    def load(source_file_path: str) -> "QySourceFile":
        if not source_file_path.endswith(config.QY_SOURCE_FILE_EXTENSION):
            panic.because(
                panic.ExitCode.BadProjectFile, 
                f"expected source file path to end with '{config.QY_SOURCE_FILE_EXTENSION}', got:", 
                source_file_path
            )
        if not os.path.isfile(source_file_path):
            panic.because(
                panic.ExitCode.BadProjectFile,
                "source file path does not refer to a file:",
                source_file_path
            )
        stmt_list = qy_parser.parse_one_file(source_file_path)
        return QySourceFile(source_file_path, stmt_list)

    @classmethod
    def get_extern_str(cls) -> t.Optional[str]:
        return None


class CSourceFile(BaseSourceFile):
    def __init__(
        self, 
        source_file_path: str, 
        stmt_list: t.List[ast1.BaseStatement],
        this_file_provided_symbol_set: t.Set[str],
        is_header: bool
    ) -> None:
        super().__init__(source_file_path, stmt_list)
        self.this_file_provided_symbol_set = this_file_provided_symbol_set
        self.is_header = is_header

    @staticmethod
    def load(source_file_path: str, provided_symbol_list: t.List[str], is_header) -> "CSourceFile":
        if is_header:
            if not source_file_path.endswith(config.C_HEADER_FILE_EXTENSION):
                panic.because(
                    panic.ExitCode.BadProjectFile,
                    f"expected C header file path to end with '{config.C_HEADER_FILE_EXTENSION}', but got:",
                    source_file_path
                )
        else:
            for ext in config.C_SOURCE_FILE_EXTENSIONS:
                if source_file_path.endswith(ext):
                    break
            else:
                panic.because(
                    panic.ExitCode.BadProjectFile,
                    f"expected C source file path to end with any of '{config.C_SOURCE_FILE_EXTENSIONS}', but got:",
                    source_file_path
                )
        if not os.path.isfile(source_file_path):
            panic.because(
                panic.ExitCode.BadProjectFile,
                "source file path does not refer to an existing file:",
                source_file_path
            )
        stmt_list, this_provided_symbol_set = c_parser.parse_one_file(source_file_path, set(provided_symbol_list), is_header)
        assert isinstance(stmt_list, list)
        return CSourceFile(source_file_path, stmt_list, this_provided_symbol_set, is_header)

    @classmethod
    def get_extern_str(cls) -> t.Optional[str]:
        return "C"


#
#
# Reference to Qy Standard Library (QSL)
#
#


qc_dir = os.path.dirname(sys.argv[0])
qsl_dir = os.path.join(qc_dir, "qsl")
qsl_qyp_filepath = os.path.join(qsl_dir, "qsl.qyp.jsonc")
qsl_qyp_dep_path = f"${qsl_qyp_filepath}"
