# distutils: language=c

cdef:
    ctypedef int IntStr

    cdef IntStr intern(const char* text)
