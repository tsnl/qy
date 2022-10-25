import json5

from ..core import panic
from .package import Package
from .version import Version
from .version_constraint import ExactVersionConstraint
from .requirement import GitRequirement, FilesystemRequirement


def parse_project_from_filepath(qy_package_json_path: str):
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
    return parse_project_from_json_object(
        qy_package_json_path,
        qy_package_json
    )


def parse_project_from_json_object(qy_package_json_path: str, qy_package_json: object):
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


def parse_version(qy_package_json_path: str, raw_version_str: str, context_desc: str):
    assert isinstance(raw_version_str, str)

    expected_max_len = 4
    raw_version_list = raw_version_str.split('.')

    parse_version__check_length(
        qy_package_json_path, 
        raw_version_list, 
        expected_max_len, 
        context_desc
    )
    parse_version__check_elem_type(
        qy_package_json_path, 
        raw_version_list, 
        expected_max_len, 
        context_desc
    )
    return Version(
        major=int(raw_version_list[0]),
        minor=int(raw_version_list[1]) if len(raw_version_list) >= 2 else 0,
        patch=int(raw_version_list[2]) if len(raw_version_list) >= 3 else 0,
        revision=int(raw_version_list[3]) if len(raw_version_list) >= 4 else 0
    )


def parse_version__check_length(
    qy_package_json_path, 
    raw_version_list, 
    expected_max_len, 
    context_desc
):
    if len(raw_version_list) == 0:
        panic.because(
            panic.ExitCode.BadProjectFile,
            f"Invalid version specifier for {context_desc}: "
            f"expected a non-empty string.",
            opt_file_path=qy_package_json_path
        )
    if len(raw_version_list) > expected_max_len:
        list_len = len(raw_version_list)
        panic.because(
            panic.ExitCode.BadProjectFile,
            f"Invalid version specifier for {context_desc}: "
            f"expected a string with {expected_max_len} components, "
            f"but got length {list_len} components instead.",
            opt_file_path=qy_package_json_path
        )


def parse_version__check_elem_type(
    qy_package_json_path, 
    raw_version_list, 
    expected_len, 
    context_desc
):
    assert len(raw_version_list) == expected_len
    for i, x in enumerate(raw_version_list):
        try:
            int(x)
        except ValueError as exc:
            panic.because(
                panic.ExitCode.BadProjectFile,
                f"Invalid version specifier for {context_desc}: "
                f"In component #{1+i}/{expected_len}, expected an integer number, "
                f"but instead got: {x}",
                opt_file_path=qy_package_json_path,
                outer_exc=exc
            )


def parse_requirements_list(qy_package_json_path: str, raw_requirements_list: list):
    assert isinstance(raw_requirements_list, list)

    parse_requirements_list__check_elem_type(qy_package_json_path, raw_requirements_list)
    
    total_requirement_count = len(raw_requirements_list)
    return [
        parse_requirement_obj(
            qy_package_json_path, 
            raw_requirement_obj,
            f"requirement #{1+i}/{total_requirement_count}"
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
                f"In requirement #{1+i}/{len(raw_requirements_list)}, expected a JSON object, "
                f"but got: {raw_requirement_obj}",
                opt_file_path=qy_package_json_path
            )


def parse_requirement_obj(
    qy_package_json_path: str, 
    raw_requirement_obj: object,
    this_requirement_desc: str
):
    extractor = Extractor(raw_requirement_obj)

    provider = extractor.get("extractor", str)

    if provider == 'git':
        return parse_requirement_obj__git_provider(extractor)

    elif provider == 'filesystem':
        return parse_requirement_obj__filesystem_provider(extractor)

    else:
        panic.because(
            panic.ExitCode.BadProjectFile,
            f"In {this_requirement_desc}, "
            f"unknown requirement provider: {repr(provider)}",
            opt_file_path=qy_package_json_path
        )


def parse_requirement_obj__git_provider(extractor):
    version_constraint_list = parse_requirement_version_constraints(
        extractor.qy_package_json_path,
        extractor.get("version")
    )
    return GitRequirement(
        location=extractor.get("location", str),
        version_constraints=version_constraint_list
    )


def parse_requirement_obj__filesystem_provider(extractor):
    version_constraint_list = parse_requirement_version_constraints(
        extractor.qy_package_json_path,
        extractor.get("version")
    )
    return FilesystemRequirement(
        location=extractor.get("location", str),
        version_constraints=version_constraint_list
    )


def parse_requirement_version_constraints(
    qy_package_json_path, 
    raw_version_obj: object,
    this_requirement_desc: str
):
    # check that raw_version_obj is either...
    # - a string denoting a version number (exact constraint specifier)
    # - a list of >=, >, <=, < version constraints
    # - the wild-card version specifier, namely '*' (default)
    
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
            f"but instead got: {raw_version_obj}",
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
    raw_version_obj: list,
    this_requirement_desc: str
):
    assert isinstance(raw_version_obj, list)
    # TODO: parse strings beginning with '>', '<', '>=', or '<='
    raise NotImplementedError()


#
# Helper:
#

class Extractor(object):
    def __init__(self, qy_package_json_path: str, qy_package_json: object) -> None:
        self.qy_package_json_path = qy_package_json_path
        self.qy_package_json = qy_package_json

    def get(self, key, expected_datatype) -> object:
        file_path = self.qy_package_json_path
        obj = self.qy_package_json
        
        if key not in obj:
            panic.because(
                panic.ExitCode.BadProjectFile,
                f"Missing key: '{key}'",
                opt_file_path=file_path
            )

        res = obj[key]

        # typechecking:
        if issubclass(expected_datatype, (int, float)):
            try:
                res = expected_datatype(res)
            except ValueError:
                panic.because(
                    panic.ExitCode.BadProjectFile,
                    f"Expected key '{key}' to map to a number, instead got: {res}",
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
                f"Expected key '{key}' to map to {expected_datatype_name}, instead got: {res}"
            )
            
        return res
