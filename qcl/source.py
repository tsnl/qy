import os.path
import json
import typing as t

from . import panic
from . import feedback as fb


class Qyp(object):
    def __init__(
        self, 
        qyp_file_path, 
        name: str, author: str, help: str, 
        src_list: t.List[str], 
        dep_list: t.List[str]
    ) -> None:
        super().__init__()
        self.qyp_file_path = qyp_file_path
        self.package_dir_path = os.path.dirname(qyp_file_path)
        self.name = name
        self.author = author
        self.help = help
        self.src_list = src_list
        self.dep_list = dep_list


def load_qyp(path_to_root_qyp_file: str) -> Qyp:
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
        return  # -> never actually runs

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


package_required_keys = {
    "name", "author", "help", "src"
}
package_optional_keys = {
    "deps"
}
package_supported_keys = package_required_keys | package_optional_keys
