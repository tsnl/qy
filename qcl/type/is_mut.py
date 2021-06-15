from . import elem

mutable_tid_set = set()


def init_ptr(ptr_tid, is_mutable):
    if is_mutable:
        mutable_tid_set.add(ptr_tid)


def init_array(array_tid, is_mutable):
    if is_mutable:
        mutable_tid_set.add(array_tid)


def init_slice(slice_tid, is_mutable):
    if is_mutable:
        mutable_tid_set.add(slice_tid)


def ptr_or_array_or_slice(tid):
    return tid in mutable_tid_set


def ptr(ptr_tid):
    return ptr_tid in mutable_tid_set


def array(array_tid):
    return array_tid in mutable_tid_set


def slice(slice_tid):
    return slice_tid in mutable_tid_set
