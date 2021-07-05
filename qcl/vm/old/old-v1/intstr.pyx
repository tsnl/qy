string_map = {}


cdef IntStr intern(const char* text):
    key = <bytes> text
    old_id = string_map.get(key, None)
    if old_id is not None:
        return old_id
    else:
        new_id = 1 + len(string_map)
        string_map[key] = new_id
