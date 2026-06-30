import bpy
from mathutils import Vector

from .. import __package__ as base_package

# 框选工具的按键映射。
# 早期版本用字符串 "3D View Tool: Select Box" 借用 Blender 内置键位，
# 但在部分版本/键位配置下该键位映射尚未存在，会刷出
# "Warning keymap '3D View Tool: Select Box' not found" 的警告。
# 这里直接给出等价的键位定义，行为一致且不再产生警告。
SELECT_BOX_KEYMAP = (
    ("view3d.select_box",
     {"type": "LEFTMOUSE", "value": "CLICK_DRAG"},
     {"properties": [("mode", "SET")]}),
    ("view3d.select_box",
     {"type": "LEFTMOUSE", "value": "CLICK_DRAG", "shift": True},
     {"properties": [("mode", "ADD")]}),
    ("view3d.select_box",
     {"type": "LEFTMOUSE", "value": "CLICK_DRAG", "ctrl": True},
     {"properties": [("mode", "SUB")]}),
)

# 所有工具通用：按 Esc 退出当前工具并切换到内置框选工具。
EXIT_TO_SELECT_BOX_KEYMAP = (
    ("wm.tool_set_by_id",
     {"type": "ESC", "value": "PRESS"},
     {"properties": [("name", "builtin.select_box")]}),
)


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
    if len(selected_objects) == 0:
        return center
    for obj in selected_objects:
        center += obj.matrix_world.translation

    center /= len(selected_objects)
    return center


def is_contains_chinese(text: str):
    """通过re检查"""
    if not isinstance(text, str):
        return False
    import re
    pattern = re.compile(r'[\u4e00-\u9fff]+')
    return bool(pattern.search(text))
