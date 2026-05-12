# cython: language_level=3

cpdef long add_range(long n):
    cdef long i
    cdef long total = 0
    for i in range(n + 1):
        total += i
    return total


cpdef double weighted_sum(double[:] values, double weight):
    cdef Py_ssize_t i
    cdef double total = 0.0
    for i in range(values.shape[0]):
        total += values[i] * weight
    return total
