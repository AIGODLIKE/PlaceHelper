import bpy

from bpy_extras.view3d_utils import region_2d_to_vector_3d as r2d_2_vec3d
from bpy_extras.view3d_utils import region_2d_to_origin_3d as r2d_2_origin3d
from bpy_extras.view3d_utils import region_2d_to_location_3d as r2d_2_loc3d

from contextlib import contextmanager


def ray_cast(context, event, start_point=None):
    mouse_pos = event.mouse_region_x, event.mouse_region_y
    scene = context.scene
    region = context.region
    region3D = context.space_data.region_3d
    viewlayer = context.view_layer.depsgraph

    # The direction indicated by the mouse position from the current view / The view point of the user
    view_vector = r2d_2_vec3d(region, region3D, mouse_pos)
    view_point = r2d_2_origin3d(region, region3D, mouse_pos)
    # The 3D location in this direction
    world_loc = r2d_2_loc3d(region, region3D, mouse_pos, view_vector)
    # first hit to get target obj
    if not start_point: start_point = view_point
    result, location, normal, index, target_obj, matrix = scene.ray_cast(viewlayer, start_point,
                                                                         view_vector)
    return result, target_obj, view_point, world_loc, normal, location, matrix

@contextmanager
def exclude_ray_cast(obj_list: list[bpy.types.Object]):
    """光线投射时排除物体"""
    for obj in obj_list:
        obj.hide_set(True)
    yield  # 执行上下文管理器中的代码（光线投射）
    for obj in obj_list:
        obj.hide_set(False)
        obj.select_set(True)