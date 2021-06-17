from typing import *

from qcl import excepts

from . import definition


def def_universe(name: str) -> definition.Universe:
    for ch in name:
        if ch.isalpha():
            if ch.isupper():
                return definition.Universe.Type
            else:
                assert ch.islower()
                return definition.Universe.Value
    else:
        raise excepts.TyperCompilationError("Invalid template arg name")


def filter_in_universe(names: Iterable[str], du: definition.Universe) -> Iterable[str]:
    for name in names:
        if def_universe(name) == du:
            yield name


def filter_vals(names: Iterable[str]):
    yield from filter_in_universe(names, definition.Universe.Value)


def filter_types(names: Iterable[str]):
    yield from filter_in_universe(names, definition.Universe.Type)


def sift_type_from_val(names: Iterable[str]):
    all_v_names = []
    all_t_names = []

    for name in names:
        if def_universe(name) == definition.Universe.Value:
            all_v_names.append(name)
        elif def_universe(name) == definition.Universe.Type:
            all_t_names.append(name)

    return all_t_names, all_v_names