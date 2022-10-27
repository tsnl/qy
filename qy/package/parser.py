import os.path

import json5

from ..core import panic
from ..core import const

from .package import Package
from .version import Version
from .version_constraint import ExactVersionConstraint, MinVersionConstraint, MaxVersionConstraint
from .requirement import GitRequirement, FilesystemRequirement


#
# parse_package_from_dirpath, parse_package_from_filepath, parse_package_from_json_object
#

def parse_package_from_dirpath(qy_package_dir_path: str) -> Package:
    qy_package_json_filepath = os.path.join(qy_package_dir_path, const.QY_PACKAGE_FILENAME)
    
    if not os.path.isdir(qy_package_dir_path):
        panic.because(
            panic.ExitCode.BadProjectFile,
            f"Invalid project directory: this directory does not exist.",
            opt_file_path=qy_package_dir_path
        )

    if not os.path.isfile(qy_package_json_filepath):
        panic.because(
            panic.ExitCode.BadProjectFile,
            f"Invalid project directory: missing a '{const.QY_PACKAGE_FILENAME}' file",
            opt_file_path=qy_package_json_filepath
        )
    
    return parse_package_from_filepath(qy_package_json_filepath)


def parse_package_from_filepath(qy_package_json_path: str) -> Package:
    qy_package_json = None
    with open(qy_package_json_path) as qy_package_json_file:
        try:
            qy_package_json = json5.load(
                fp=qy_package_json_file, 
                encoding="UTF-8",
                allow_duplicate_keys=False
            )
        except ValueError as exc:
            # duplicate keys detected
            # TODO: read the 'exc' to gather information about the duplicate key
            panic.because(
                panic.ExitCode.BadProjectFile,
                f"Duplicate keys detected in 'qy-package.json5' file: {exc}"
            )
    assert qy_package_json is not None
    return parse_package_from_json_object(
        qy_package_json_path,
        qy_package_json
    )


def parse_package_from_json_object(qy_package_json_path: str, qy_package_json: object) -> Package:
    extractor = Extractor(qy_package_json_path, qy_package_json)
    return Package(
        author=extractor.get("author", str),
        description=extractor.get("description", str),
        version=parse_version(
            qy_package_json_path, 
            extractor.get("version", str), 
            "package version"
        ),
        requirements=parse_requirements_list(
            qy_package_json_path, 
            extractor.get("requires", list)
        )
    )


#
# parse_version
#

def parse_version(qy_package_json_path: str, raw_version_str: str, context_desc: str):
    assert isinstance(raw_version_str, str)

    raw_version_list = raw_version_str.split('.')
    min_component_count = Version.min_component_count
    max_component_count = Version.max_component_count

    parse_version__check_component_count(
        qy_package_json_path, 
        raw_version_list,
        min_component_count, max_component_count,
        context_desc
    )
    parse_version__check_elem_type(
        qy_package_json_path, 
        raw_version_list, 
        min_component_count, max_component_count,
        context_desc
    )
    return Version(
        major=int(raw_version_list[0]),
        minor=int(raw_version_list[1]) if len(raw_version_list) >= 2 else 0,
        patch=int(raw_version_list[2]) if len(raw_version_list) >= 3 else 0,
        revision=int(raw_version_list[3]) if len(raw_version_list) >= 4 else 0
    )


def parse_version__check_component_count(
    qy_package_json_path, 
    raw_version_list,
    min_component_count, max_component_count,
    context_desc
):
    if len(raw_version_list) == 0:
        panic.because(
            panic.ExitCode.BadProjectFile,
            f"Invalid version specifier for {context_desc}: "
            f"expected a non-empty string.",
            opt_file_path=qy_package_json_path
        )
    component_count_ok = min_component_count <= len(raw_version_list) <= max_component_count
    if not component_count_ok:
        list_len = len(raw_version_list)
        panic.because(
            panic.ExitCode.BadProjectFile,
            f"Invalid version specifier for {context_desc}: "
            f"expected a string with {min_component_count} to {max_component_count} components, "
            f"but got length {list_len} components instead.",
            opt_file_path=qy_package_json_path
        )


def parse_version__check_elem_type(
    qy_package_json_path, 
    raw_version_list, 
    min_component_count, max_component_count, 
    context_desc
):
    assert min_component_count <= len(raw_version_list) <= max_component_count
    for i, x in enumerate(raw_version_list):
        try:
            int(x)
        except ValueError as exc:
            panic.because(
                panic.ExitCode.BadProjectFile,
                f"Invalid version specifier for {context_desc}: "
                f"In component {1+i} of {max_component_count}, expected an integer number, "
                f"but instead got: {repr(x)}",
                opt_file_path=qy_package_json_path,
                outer_exc=exc
            )


#
# parse_requirements_list, parse_requirement
#

def parse_requirements_list(qy_package_json_path: str, raw_requirements_list: list):
    assert isinstance(raw_requirements_list, list)

    parse_requirements_list__check_elem_type(qy_package_json_path, raw_requirements_list)
    
    total_requirement_count = len(raw_requirements_list)
    return [
        parse_requirement(
            qy_package_json_path, 
            raw_requirement_obj,
            f"requirement {1+i} of {total_requirement_count}"
        )
        for i, raw_requirement_obj in enumerate(raw_requirements_list)
    ]
        

def parse_requirements_list__check_elem_type(
    qy_package_json_path: str, 
    raw_requirements_list: list
):
    for i, raw_requirement_obj in enumerate(raw_requirements_list):
        if not isinstance(raw_requirement_obj, dict):
            panic.because(
                panic.ExitCode.BadProjectFile,
                f"In requirement {1+i} of {len(raw_requirements_list)}, expected a JSON object, "
                f"but got: {raw_requirement_obj}",
                opt_file_path=qy_package_json_path
            )


def parse_requirement(
    qy_package_json_path: str, 
    raw_requirement_obj: object,
    this_requirement_desc: str
):
    extractor = Extractor(qy_package_json_path, raw_requirement_obj)

    provider = extractor.get("provider", str)

    if provider == 'git':
        return parse_requirement__git_provider(extractor, this_requirement_desc)

    elif provider == 'filesystem':
        return parse_requirement__filesystem_provider(extractor, this_requirement_desc)

    else:
        panic.because(
            panic.ExitCode.BadProjectFile,
            f"In {this_requirement_desc}, "
            f"unknown requirement provider: {repr(provider)}",
            opt_file_path=qy_package_json_path
        )


def parse_requirement__git_provider(extractor: "Extractor", this_requirement_desc):
    version_constraint_list = parse_requirement_version_constraints(
        extractor.json_path,
        extractor.get("version") if "version" in extractor.json else "*",
        this_requirement_desc
    )
    return GitRequirement(
        location=extractor.get("location", str),
        version_constraints=version_constraint_list
    )


def parse_requirement__filesystem_provider(extractor: "Extractor", this_requirement_desc):
    version_constraint_list = parse_requirement_version_constraints(
        extractor.json_path,
        extractor.get("version") if "version" in extractor.json else "*",
        this_requirement_desc
    )
    return FilesystemRequirement(
        location=extractor.get("location", str),
        version_constraints=version_constraint_list
    )


#
# parse_requirement_version_constraints
#

def parse_requirement_version_constraints(
    qy_package_json_path, 
    raw_version_obj: object,
    this_requirement_desc: str
):
    if isinstance(raw_version_obj, str):
        return parse_requirement_version_constraints__singleton_string(
            qy_package_json_path,
            raw_version_obj,
            this_requirement_desc
        )
    
    elif isinstance(raw_version_obj, list):
        return parse_requirement_version_constraints__list_of_string_constraints(
            qy_package_json_path,
            raw_version_obj,
            this_requirement_desc
        )

    else:
        panic.because(
            panic.ExitCode.BadProjectFile,
            f"In {this_requirement_desc}, "
            f"expected a list or a string for version constraints, "
            f"but instead got: {repr(raw_version_obj)}",
            opt_file_path=qy_package_json_path
        )


def parse_requirement_version_constraints__singleton_string(
    qy_package_json_path: str, 
    raw_version_obj: str,
    this_requirement_desc: str
):
    if raw_version_obj == '*':
        # no constraints
        return []
    else:
        version = parse_version(qy_package_json_path, raw_version_obj, this_requirement_desc)
        return [ExactVersionConstraint(version)]


def parse_requirement_version_constraints__list_of_string_constraints(
    qy_package_json_path: str, 
    raw_version_list: list,
    this_requirement_desc: str
):
    assert isinstance(raw_version_list, list)
    return [
        parse_requirement_version_constraint_string(
            qy_package_json_path,
            version_constraint_str,
            this_requirement_desc,
            version_constraint_index,
            len(raw_version_list)
        )
        for version_constraint_index, version_constraint_str in enumerate(raw_version_list)
    ]


#
# parse_requirement_version_constraint_string
#

def parse_requirement_version_constraint_string(
    qy_package_json_path: str,
    version_constraint_str: str,
    this_requirement_desc: str,
    version_constraint_index: int,
    version_constraint_count: int
):
    context_desc = (
        f"{this_requirement_desc}, version constraint "
        f"{1+version_constraint_index} of {version_constraint_count}"
    )

    if version_constraint_str.startswith('<'):
        raw_version_point, is_closed = (
            (version_constraint_str[len('<='):], True)
            if version_constraint_str.startswith('<=') else
            (version_constraint_str[len('<'):], False)
        )
        version_point = parse_version(qy_package_json_path, raw_version_point, context_desc)
        return MaxVersionConstraint(version_point, is_closed)

    if version_constraint_str.startswith('>'):
        raw_version_point, is_closed = (
            (version_constraint_str[len('>='):], True)
            if version_constraint_str.startswith('>=') else
            (version_constraint_str[len('>'):], False)
        )
        version_point = parse_version(qy_package_json_path, raw_version_point, context_desc)
        return MinVersionConstraint(version_point, is_closed)

    panic.because(
        panic.ExitCode.BadProjectFile,
        f"In {context_desc}, found invalid version constraint: {version_constraint_str}",
        opt_file_path=qy_package_json_path
    )


#
# Helper:
#

class Extractor(object):
    def __init__(self, qy_package_json_path: str, qy_package_json: object) -> None:
        self.json_path = qy_package_json_path
        self.json = qy_package_json

    def get(self, key, expected_datatype=object) -> object:
        file_path = self.json_path
        obj = self.json
        
        if key not in obj:
            panic.because(
                panic.ExitCode.BadProjectFile,
                f"Missing key: '{key}'",
                opt_file_path=file_path
            )

        res = obj[key]

        # typechecking:
        if expected_datatype is object:
            # no checks required here
            pass
        elif issubclass(expected_datatype, (int, float)):
            try:
                res = expected_datatype(res)
            except ValueError:
                panic.because(
                    panic.ExitCode.BadProjectFile,
                    f"Expected key '{key}' to map to a number, instead got: {repr(res)}",
                    opt_file_path=file_path
                )
        elif not isinstance(res, expected_datatype):
            expected_datatype_name = {
                type(None): "'null'",
                str: "a string",
                dict: "an object",
                list: "an array"
            }[expected_datatype]
            panic.because(
                panic.ExitCode.BadProjectFile,
                f"Expected key '{key}' to map to {expected_datatype_name}, instead got: {repr(res)}",
                opt_file_path=file_path
            )
            
        return res
