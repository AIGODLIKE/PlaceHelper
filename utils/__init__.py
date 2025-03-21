import bpy
from mathutils import Vector

from .. import __package__ as base_package


def get_pref():
    return bpy.context.preferences.addons[base_package].preferences


def get_color(axis):
    ui = bpy.context.preferences.themes[0].user_interface

    axis_x = ui.axis_x[:3]
    axis_y = ui.axis_y[:3]
    axis_z = ui.axis_z[:3]

    if axis == "X":
        color = axis_x
    elif axis == "Y":
        color = axis_y
    else:
        color = axis_z

    return color, color


def get_selected_objects_center_translation(context) -> Vector:
    center = Vector()
    selected_objects = context.selected_objects
    for obj in selected_objects:
        center += obj.matrix_world.translation

    center /= len(selected_objects)
    return center
