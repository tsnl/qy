from typing import *

from . import identity

scalar_width_map: Dict[identity.TID, "ScalarWidthComponent"] = {}


ScalarWidthComponent = int


def init(tid, tid_width):
    assert tid_width in (1, 8, 16, 32, 64, 128)
    scalar_width_map[tid] = tid_width


def of(tid):
    return scalar_width_map.get(tid, None)
