import bmesh
import bpy
from mathutils import Vector

from .get_position import get_objs_bbox_center


def get_bmesh_active(bm):
    active_last = bm.select_history.active
    bm.faces.ensure_lookup_table()
    active_current = bm.faces.active

    if active_last:
        if isinstance(active_last, bmesh.types.BMFace) and active_current:
            return active_current
        else:
            return active_last
    elif active_current:
        sv = set([v for v in bm.verts if v.select])
        svf = set([v for v in active_current.verts])

        if svf.issubset(sv):
            return active_current
        elif sv:
            return sv[0]


def get_active_face_position(obj):
    loc = Vector((0, 0, 0))
    if obj is None: return loc

    bm = bmesh.from_edit_mesh(obj.data)
    active_face = get_bmesh_active(bm)

    if isinstance(active_face, bmesh.types.BMVert):
        loc = obj.matrix_world @ active_face.co

    elif isinstance(active_face, bmesh.types.BMEdge):
        loc = obj.matrix_world @ ((active_face.verts[0].co.copy() + active_face.verts[1].co.copy()) / 2).copy()

    elif isinstance(active_face, bmesh.types.BMFace):
        loc = obj.matrix_world @ active_face.calc_center_median().copy()

    return loc


def get_median_point_position():
    sOb = bpy.context.objects_in_mode_unique_data
    verts = []
    for ob in sOb:
        bm = bmesh.from_edit_mesh(ob.data)
        verts.extend([ob.matrix_world @ v.co for v in bm.verts if v.select])

    if len(verts) > 0:
        loc = sum(verts, Vector()) / len(verts)
    else:
        loc = get_active_face_position(bpy.context.object)

    return loc


def get_bbox_mesh_position():
    sOb = bpy.context.objects_in_mode_unique_data
    verts = []
    for ob in sOb:
        bm = bmesh.from_edit_mesh(ob.data)
        verts.extend([ob.matrix_world @ v.co for v in bm.verts if v.select])

    if len(verts) > 0:
        x = (min([v.x for v in verts]) + max([v.x for v in verts])) / 2
        y = (min([v.y for v in verts]) + max([v.y for v in verts])) / 2
        z = (min([v.z for v in verts]) + max([v.z for v in verts])) / 2
        loc = Vector((x, y, z))
    else:
        loc = get_active_face_position(bpy.context.object)

    return loc


def get_edit_mesh_position():
    tpp = bpy.context.scene.tool_settings.transform_pivot_point

    if tpp == 'ACTIVE_ELEMENT':
        obj = bpy.context.object
        bm = bmesh.from_edit_mesh(obj.data)
        active = get_bmesh_active(bm)
        if active:
            loc = get_active_face_position(obj)
        else:
            loc = get_median_point_position()

    elif tpp in {'MEDIAN_POINT', 'INDIVIDUAL_ORIGINS'}:
        loc = get_median_point_position()

    elif tpp == 'BOUNDING_BOX_CENTER':
        loc = get_bbox_mesh_position()

    else:
        loc = bpy.context.scene.cursor.location

    return loc


def get_object_position():
    tpp = bpy.context.scene.tool_settings.transform_pivot_point
    loc = Vector((0, 0, 0))

    if tpp == 'ACTIVE_ELEMENT':
        loc = bpy.context.object.matrix_world.translation

    elif tpp in {'MEDIAN_POINT', 'INDIVIDUAL_ORIGINS'}:
        selected_objects = bpy.context.selected_objects
        for obj in selected_objects:
            loc += obj.matrix_world.translation
        loc /= len(selected_objects)

    elif tpp == 'BOUNDING_BOX_CENTER':
        if len(bpy.context.selected_objects) > 1:
            loc = get_objs_bbox_center(bpy.context.selected_objects)
        else:
            loc = bpy.context.object.matrix_world.translation
    else:
        loc = bpy.context.scene.cursor.location

    return loc


def get_position():
    if bpy.context.mode == 'OBJECT':
        return get_object_position()
    elif bpy.context.mode == 'EDIT_MESH':
        return get_edit_mesh_position()
