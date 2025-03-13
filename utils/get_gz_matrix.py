from math import radians, sqrt

import bmesh
import bpy
import numpy
from mathutils import Matrix, Quaternion, Vector

from .get_gz_position import get_bmesh_active

# blender 坐标系
arc_angle = (0.0, 0.0, 90.0)


def global_matrix(reverse_zD=False):
    x = Quaternion((0.0, 1.0, 0.0), radians(90))
    y = Quaternion((1.0, 0.0, 0.0), radians(-90))
    z = Quaternion((0.0, 0.0, 1.0), radians(-90))

    xD = Quaternion((0.0, 1.0, 0.0), radians(-90)) @ Quaternion((0.0, 0.0, 1.0), radians(arc_angle[0]))
    yD = Quaternion((1.0, 0.0, 0.0), radians(90)) @ Quaternion((0.0, 0.0, 1.0), radians(arc_angle[1]))
    zD = Quaternion((0.0, 0.0, 1.0), radians(arc_angle[2]))
    if reverse_zD:
        zD = Quaternion((0.0, 1.0, 0), radians(-180))

    return x, y, z, xD, yD, zD


def local_matrix(obj=None, reverse_zD=False):
    if obj:
        rot = obj.matrix_world.decompose()[1]
    else:
        rot = bpy.context.object.matrix_world.decompose()[1]

    x = rot @ Quaternion((0.0, 1.0, 0.0), radians(90))
    y = rot @ Quaternion((1.0, 0.0, 0.0), radians(-90))
    z = rot @ Quaternion((0.0, 0.0, 1.0), radians(-90))

    xD = rot @ Quaternion((0.0, 1.0, 0.0), radians(-90)) @ Quaternion((0.0, 0.0, 1.0), radians(arc_angle[0]))
    yD = rot @ Quaternion((1.0, 0.0, 0.0), radians(90)) @ Quaternion((0.0, 0.0, 1.0), radians(arc_angle[1]))
    zD = rot @ Quaternion((0.0, 0.0, 1.0), radians(arc_angle[2]))
    if reverse_zD:
        zD = rot @ Quaternion((0.0, 1.0, 0), radians(-180))

    return x, y, z, xD, yD, zD


def gimbal_matrix(reverse_zD=False):
    ob = bpy.context.object
    rot = ob.matrix_world.decompose()[1]

    x = rot @ Quaternion((0.0, 1.0, 0.0), radians(90))
    y = Quaternion((0.0, 0.0, 1.0), ob.rotation_euler[2]) @ Quaternion((1.0, 0.0, 0.0), radians(-90))
    z = Quaternion((0.0, 0.0, 1.0), radians(-90))

    xD = rot @ Quaternion((0.0, 1.0, 0.0), radians(-90)) @ Quaternion((0.0, 0.0, 1.0), radians(arc_angle[0]))

    yD = Quaternion((0.0, 0.0, 1.0), ob.rotation_euler[2]) @ Quaternion((1.0, 0.0, 0.0), radians(90)) @ Quaternion(
        (0.0, 0.0, 1.0), radians(arc_angle[1]))
    zD = Quaternion((0.0, 0.0, 1.0), radians(arc_angle[2]))
    if reverse_zD:
        zD = Quaternion((0.0, 1.0, 0), radians(-180))

    return x, y, z, xD, yD, zD


def view_matrix(context=None, reverse_zD=False):
    if context:
        view_inv = context.region_data.view_matrix.inverted()
    else:
        view_inv = bpy.context.region_data.view_matrix.inverted()
    rot = view_inv.decompose()[1]

    x = rot @ Quaternion((0.0, 1.0, 0.0), radians(90))
    y = rot @ Quaternion((1.0, 0.0, 0.0), radians(-90))
    z = rot @ Quaternion((0.0, 0.0, 1.0), radians(-90))

    xD = rot @ Quaternion((0.0, 1.0, 0.0), radians(-90)) @ Quaternion((0.0, 0.0, 1.0), radians(arc_angle[0]))
    yD = rot @ Quaternion((1.0, 0.0, 0.0), radians(90)) @ Quaternion((0.0, 0.0, 1.0), radians(arc_angle[1]))
    zD = rot @ Quaternion((0.0, 0.0, 1.0), radians(arc_angle[2]))

    if reverse_zD:
        zD = Quaternion((0.0, 1.0, 0), radians(-180))

    return x, y, z, xD, yD, zD


def cursor_matrix(reverse_zD=False):
    cursor_mat = bpy.context.scene.cursor.matrix
    rot = cursor_mat.decompose()[1]

    x = rot @ Quaternion((0.0, 1.0, 0.0), radians(90))
    y = rot @ Quaternion((1.0, 0.0, 0.0), radians(-90))
    z = rot @ Quaternion((0.0, 0.0, 1.0), radians(-90))

    xD = rot @ Quaternion((0.0, 1.0, 0.0), radians(-90)) @ Quaternion((0.0, 0.0, 1.0), radians(arc_angle[0]))
    yD = rot @ Quaternion((1.0, 0.0, 0.0), radians(90)) @ Quaternion((0.0, 0.0, 1.0), radians(arc_angle[1]))
    zD = rot @ Quaternion((0.0, 0.0, 1.0), radians(arc_angle[2]))

    if reverse_zD:
        zD = rot @ Quaternion((0.0, 1.0, 0), radians(-180))

    return x, y, z, xD, yD, zD


def custom_matrix(reverse_zD=False):
    custom_mat = bpy.context.scene.transform_orientation_slots[0].custom_orientation.matrix.to_4x4()
    rot = custom_mat.decompose()[1]

    x = rot @ Quaternion((0.0, 1.0, 0.0), radians(90))
    y = rot @ Quaternion((1.0, 0.0, 0.0), radians(-90))
    z = rot @ Quaternion((0.0, 0.0, 1.0), radians(-90))

    xD = rot @ Quaternion((0.0, 1.0, 0.0), radians(-90)) @ Quaternion((0.0, 0.0, 1.0), radians(arc_angle[0]))
    yD = rot @ Quaternion((1.0, 0.0, 0.0), radians(90)) @ Quaternion((0.0, 0.0, 1.0), radians(arc_angle[1]))
    zD = rot @ Quaternion((0.0, 0.0, 1.0), radians(arc_angle[2]))
    if reverse_zD:
        zD = rot @ Quaternion((0.0, 1.0, 0), radians(-180))

    return x, y, z, xD, yD, zD


def normal_mesh_matrix(reverse_zD=False):
    def mul_v3_v3fl(r, a, f):
        r[0] = a[0] * f
        r[1] = a[1] * f
        r[2] = a[2] * f

    def normalize_v3_v3_length(r, a, unit_length=1.0):
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

    def get_face_tangent(f):
        if len(f.verts) == 3 or len(f.verts) == 4:
            r_tangent = f.calc_tangent_edge_pair()
        else:
            r_tangent = f.calc_tangent_edge()

        return r_tangent

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

        return n

    def editselection_normal(sha):
        select_mode = bpy.context.scene.tool_settings.mesh_select_mode
        r_normal = Vector((0, 0, 0))
        if sha is None:
            return r_normal

        if select_mode[0] or select_mode[2]:
            r_normal = sha.normal

        elif select_mode[1]:
            v1 = sha.verts[0]
            v2 = sha.verts[1]
            normal = v1.normal + v2.normal

            plane = v2.co - v1.co

            vec = normal.cross(plane)
            r_normal = plane.cross(vec)
            r_normal.normalize()

        return r_normal

    def editselection_plane(ese):
        r_plane = Vector()
        if isinstance(ese, bmesh.types.BMVert):
            vec = Vector((0, 0, 0))

            if ese.normal[0] < 0.5:
                vec[0] = 1.0
            elif ese.normal[1] < 0.5:
                vec[1] = 1.0
            else:
                vec[2] = 1.0

            r_plane = ese.normal.cross(vec)
            r_plane.normalize()

        elif isinstance(ese, bmesh.types.BMEdge):
            v1 = ese.verts[0]
            v2 = ese.verts[1]

            if ese.is_boundary:
                r_plane = v1 - v2
            else:
                r_plane = v2.co - v1.co if v2.co[1] > v1.co[1] else v1.co - v2.co

            r_plane.normalize()


        elif isinstance(ese, bmesh.types.BMFace):
            r_plane = get_face_tangent(ese)

        return r_plane

    def vert_tri_find_unique_edge(verts):
        difs = Vector()

        if len(verts) < 4:
            return 0

        i_next = 0
        while i_next < 3:
            if i_next == 0:
                i_prev = 1
                i_curr = 2

            elif i_next == 1:
                i_prev = 2
                i_curr = 0

            elif i_next == 2:
                i_prev = 0
                i_curr = 1

            co = verts[i_curr].co
            co_other = [verts[i_prev].co, verts[i_next].co]

            proj_dir = co_other[0].lerp(co_other[1])
            proj_dir = proj_dir - co

            proj_pair = [Vector(), Vector()]
            proj_pair[0] = co_other[0].project(proj_dir)
            proj_pair[1] = co_other[1].project(proj_dir)

            difs[i_next] = (proj_pair[0] - proj_pair[1]).dot(proj_pair[0] - proj_pair[1])

            i_next += 1

        order = Vector((0, 1, 2))

        def axis_sort_v3(axis_values, order):
            v = axis_values
            if v[0] < v[1]:
                if v[2] < v[0]:
                    order[0], order[2] = order[2], order[0]
            else:
                if v[1] < v[2]:
                    order[0], order[1] = order[1], order[0]
                else:
                    order[0], order[2] = order[2], order[0]

            if v[2] < v[1]:
                order[1], order[2] = order[2], order[1]

        axis_sort_v3(difs, order)

        return order[0]

    def vert_tri_calc_tangent_edge(verts):  # BM
        i = vert_tri_find_unique_edge(verts)
        i = int(i)

        r_tangent = Vector()

        def sub_v3_v3v3(r, a, b):
            r[0] = a[0] - b[0]
            r[1] = a[1] - b[1]
            r[2] = a[2] - b[2]

        sub_v3_v3v3(r_tangent, verts[i].co, verts[(i + 1) % 3].co)

        r_tangent.normalize()
        return r_tangent

    def copy_v3_v3(r, a):
        r[0] = a[0]
        r[1] = a[1]
        r[2] = a[2]

    def is_zero_v3(v):
        return v[0] == 0.0 and v[1] == 0.0 and v[2] == 0.0

    def cross_v3_v3v3(r, a, b):
        r[0] = a[1] * b[2] - a[2] * b[1]
        r[1] = a[2] * b[0] - a[0] * b[2]
        r[2] = a[0] * b[1] - a[1] * b[0]

    def negate_v3_v3(r, a):
        r[0] = -a[0]
        r[1] = -a[1]
        r[2] = -a[2]

    def createSpaceNormal(mat, normal):
        tangent = Vector((0, 0, 1))

        copy_v3_v3(mat[2], normal)

        if normalize_v3_v3_length(mat[2], mat[2]) == 0:
            return False

        cross_v3_v3v3(mat[0], mat[2], tangent)
        if is_zero_v3(mat[0]):
            tangent = Vector((1, 0, 0))
            cross_v3_v3v3(mat[0], tangent, mat[2])

        cross_v3_v3v3(mat[1], mat[2], mat[0])

        return True

    def createSpaceNormalTangent(mat, normal, tangent):
        if normalize_v3_v3_length(mat[2], normal) == 0.0:
            return False

        negate_v3_v3(mat[1], tangent)
        if is_zero_v3(mat[1]):
            mat[1][2] = 1.0

        cross_v3_v3v3(mat[0], mat[2], mat[1])

        if normalize_v3_v3_length(mat[0], mat[0]) == 0.0:
            return False

        cross_v3_v3v3(mat[1], mat[2], mat[0])
        normalize_v3_v3_length(mat[1], mat[1])

        return True

    context = bpy.context

    """ ob = context.active_object
    if ob is None: """
    ob = context.object

    obmat = ob.matrix_world.copy()
    imat = obmat.inverted()
    mat = imat.transposed()

    normal = Vector()
    plane = Vector()

    tpp = context.scene.tool_settings.transform_pivot_point

    em = bmesh.from_edit_mesh(ob.data)

    result = 'ORIENTATION_VERT'

    bm = bmesh.from_edit_mesh(ob.data)
    el = get_bmesh_active(bm)

    if tpp == 'ACTIVE_ELEMENT':  # transform_orientation.c 770

        normal = editselection_normal(el)
        plane = editselection_plane(el)

        if isinstance(el, bmesh.types.BMVert):
            result = 'ORIENTATION_VERT'
        elif isinstance(el, bmesh.types.BMEdge):
            result = 'ORIENTATION_EDGE'
        elif isinstance(el, bmesh.types.BMFace):
            result = 'ORIENTATION_FACE'


    else:
        v = [v for v in em.verts if v.select]
        e = [e for e in em.edges if e.select]
        f = [f for f in em.faces if f.select]

        if len(f) >= 1:
            for fs in f:
                vec = get_face_tangent(fs)
                normal = normal + fs.normal
                plane = plane + vec
            result = 'ORIENTATION_FACE'

        elif len(v) == 3:  # TODO
            no_test = Vector()

            normal_tri_v3(normal, v[0].co, v[1].co, v[2].co)

            no_test[0] = v[0].normal[0] + v[1].normal[0] + v[2].normal[0]
            no_test[1] = v[0].normal[1] + v[1].normal[1] + v[2].normal[1]
            no_test[2] = v[0].normal[2] + v[1].normal[2] + v[2].normal[2]

            if no_test.dot(normal) < 0:
                normal.negate()

            """ if len(e) >= 1:
                e_length = 0
                j = 0

                while j < 3:
                    e_test = 0

                    j += 1 """

            plane = vert_tri_calc_tangent_edge(v)

            result = 'ORIENTATION_FACE'

        elif len(e) == 1 or len(v) == 2:
            result = 'ORIENTATION_EDGE'

        elif len(v) == 1:
            normal = editselection_normal(v[0])
            plane = editselection_plane(v[0])
            result = 'ORIENTATION_VERT'  # is_zero_v3(plane) ? ORIENTATION_VERT : ORIENTATION_EDGE;

        elif len(v) > 3:
            normal.zero()

            for vs in v:
                normal = normal + vs.normal

            normal.normalize()
            result = 'ORIENTATION_VERT'

    plane.negate()  # not needed but this matches 2.68 and older behavior

    if result == 'ORIENTATION_EDGE':
        if el is not None:
            # TODO 需要重构算法,有点太复杂了
            if isinstance(el, bmesh.types.BMEdge):
                v1, v2 = [v for v in el.verts]
            else:
                v1 = el
                v2 = [v for v in em.verts if v.select and v != v1][0]

            avrNormal = ((v1.normal + v2.normal) * 0.5)
            plane = obmat @ Vector(v1.co) - obmat @ Vector(v2.co)
            avrNormal = mat @ avrNormal
            perpVec = plane.cross(avrNormal).normalized()
            normal = plane.cross(perpVec).normalized()
            normal.negate()
    else:
        normal = mat @ normal
        plane = mat @ plane

    if plane == Vector((0, 0, 0)):
        result = 'ORIENTATION_VERT'

    r_orientation_mat = Matrix()
    if result == 'ORIENTATION_VERT':
        createSpaceNormal(r_orientation_mat, normal)
    else:
        createSpaceNormalTangent(r_orientation_mat, normal, plane)

    r_orientation_mat.invert_safe()
    rot = r_orientation_mat.decompose()[1]

    x = rot @ Quaternion((0.0, 1.0, 0.0), radians(90))
    y = rot @ Quaternion((1.0, 0.0, 0.0), radians(-90))
    z = rot @ Quaternion((0.0, 0.0, 1.0), radians(-90))

    xD = rot @ Quaternion((0.0, 1.0, 0.0), radians(-90)) @ Quaternion((0.0, 0.0, 1.0), radians(arc_angle[0]))
    yD = rot @ Quaternion((1.0, 0.0, 0.0), radians(90)) @ Quaternion((0.0, 0.0, 1.0), radians(arc_angle[1]))
    zD = rot @ Quaternion((0.0, 0.0, 1.0), radians(arc_angle[2]))

    if reverse_zD:
        zD = rot @ Quaternion((0.0, 1.0, 0), radians(-180))

    return x, y, z, xD, yD, zD


def get_matrix(reverse_zD=False):
    orient_slots = bpy.context.window.scene.transform_orientation_slots[0].type

    if orient_slots == 'GLOBAL':
        res = global_matrix(reverse_zD=reverse_zD)

    elif orient_slots == 'LOCAL':
        res = local_matrix(reverse_zD=reverse_zD)

    elif orient_slots == 'GIMBAL':
        res = gimbal_matrix(reverse_zD=reverse_zD)

    elif orient_slots == 'VIEW':
        res = view_matrix(reverse_zD=reverse_zD)

    elif orient_slots == 'CURSOR':
        res = cursor_matrix(reverse_zD=reverse_zD)

    elif orient_slots == 'NORMAL':
        if bpy.context.mode == 'OBJECT':
            res = local_matrix(reverse_zD=reverse_zD)

        elif bpy.context.mode == 'EDIT_MESH':
            res = normal_mesh_matrix(reverse_zD=reverse_zD)

    elif orient_slots == 'PARENT':
        if bpy.context.object.parent:
            obj = bpy.context.object.parent
            res = local_matrix(obj=obj, reverse_zD=reverse_zD)
        else:
            res = global_matrix(reverse_zD=reverse_zD)

    else:
        res = custom_matrix()

    x, y, z, xD, yD, zD = res

    s = Vector((1.0, 1.0, 1.0))

    l = Vector((0, 0, 0))

    mX = Matrix.LocRotScale(l, x, s)
    mY = Matrix.LocRotScale(l, y, s)
    mZ = Matrix.LocRotScale(l, z, s)

    mX_d = Matrix.LocRotScale(l, xD, s)
    mY_d = Matrix.LocRotScale(l, yD, s)
    mZ_d = Matrix.LocRotScale(l, zD, s)

    mX.normalized()
    mY.normalized()
    mZ.normalized()
    mX_d.normalized()
    mY_d.normalized()
    mZ_d.normalized()

    return mX, mY, mZ, mX_d, mY_d, mZ_d
