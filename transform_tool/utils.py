import numpy
from math import sqrt
from mathutils import Vector

def is_zero_v3(v):
    return v[0] == 0.0 and v[1] == 0.0 and v[2] == 0.0


def add_v3_v3(r, a):
    r[0] += a[0]
    r[1] += a[1]
    r[2] += a[2]


def mul_v3_v3fl(r, a, f):
    r[0] = a[0] * f
    r[1] = a[1] * f
    r[2] = a[2] * f


def normalize_v3_v3_length(r, a, unit_length):
    d = a.dot(a)
    if d > numpy.log1p(1.0e-35):
        d = sqrt(d)
        mul_v3_v3fl(r, a, unit_length / d)
        # print(numpy.log1p(1.0e-35))
    else:
        r.zero()
        d = 0.0
        # print(2)
    return d


def normalize_v3_v3(r, a):
    return normalize_v3_v3_length(r, a, 1.0)


def normalize_v3(n):
    return normalize_v3_v3(n, n)


def normal_tri_v3(n, v1, v2, v3):
    n1 = Vector()
    n2 = Vector()

    n1[0] = v1[0] - v2[0]
    n2[0] = v2[0] - v3[0]
    n1[1] = v1[1] - v2[1]
    n2[1] = v2[1] - v3[1]
    n1[2] = v1[2] - v2[2]
    n2[2] = v2[2] - v3[2]
    n[0] = n1[1] * n2[2] - n1[2] * n2[1]
    n[1] = n1[2] * n2[0] - n1[0] * n2[2]
    n[2] = n1[0] * n2[1] - n1[1] * n2[0]

    return normalize_v3(n)
