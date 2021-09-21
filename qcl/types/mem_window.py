import typing as t

from . import identity

mutable_tid_set = set()


def init(ptr_tid: identity.TID, is_mutable):
    if is_mutable:
        mutable_tid_set.add(ptr_tid)


def is_mut(tid: identity.TID):
    return tid in mutable_tid_set
