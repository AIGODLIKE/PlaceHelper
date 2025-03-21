import bpy
from mathutils import Vector


def get_objs_bbox_center(obj_list: list[bpy.types.Object]):
    # get bounding box center of all selected objects
    bbox_center = Vector((0, 0, 0))
    mx = lambda obj: obj.matrix_world

    for obj in obj_list:
        center = Vector((0, 0, 0))
        bbox_pts = [mx(obj) @ Vector(co) for co in obj.bound_box]
        for pt in bbox_pts:
            center += pt
        center = center / 8
        bbox_center += center

    return bbox_center / len(obj_list)

def get_objs_bbox_top(obj_list: list[bpy.types.Object]):
    # get bounding box center of all selected objects
    z = 0
    mx = lambda obj: obj.matrix_world

    for obj in obj_list:
        bbox_pts = [mx(obj) @ Vector(co) for co in obj.bound_box]
        max_z = max(bbox_pts, key=lambda v: v.z)
        if max_z.z > z:
            z = max_z.z

    return z


def get_objs_bbox_bottom(obj_list: list[bpy.types.Object]):
    # get bounding box center of all selected objects
    z = 0
    mx = lambda obj: obj.matrix_world

    for obj in obj_list:
        bbox_pts = [mx(obj) @ Vector(co) for co in obj.bound_box]
        min_z = min(bbox_pts, key=lambda v: v.z)
        if min_z.z < z:
            z = min_z.z

    return z


def get_objs_axis_aligned_bbox(obj_list: list[bpy.types.Object]):
    # get bounding box center of all selected objects
    mx = lambda obj: obj.matrix_world

    min_x = min_y = min_z = 1000000
    max_x = max_y = max_z = -1000000

    for obj in obj_list:
        bbox_pts = [mx(obj) @ Vector(co) for co in obj.bound_box]
        min_x = min(min_x, min(bbox_pts, key=lambda v: v.x).x)
        min_y = min(min_y, min(bbox_pts, key=lambda v: v.y).y)
        min_z = min(min_z, min(bbox_pts, key=lambda v: v.z).z)
        max_x = max(max_x, max(bbox_pts, key=lambda v: v.x).x)
        max_y = max(max_y, max(bbox_pts, key=lambda v: v.y).y)
        max_z = max(max_z, max(bbox_pts, key=lambda v: v.z).z)

    return min_x, min_y, min_z, max_x, max_y, max_z
