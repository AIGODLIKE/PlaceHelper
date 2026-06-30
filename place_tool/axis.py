"""放置轴向解析（独立模块，避免 tool <-> gzg 循环导入）。"""

import bpy

AXIS_ITEMS = [
    ("X", "X", ""),
    ("Y", "Y", ""),
    ("Z", "Z", ""),
]


def resolve_place_axis(context, obj=None):
    """Return (axis, invert_axis), honoring scene.use_object_axis."""
    prop = context.scene.place_tool
    if obj is None:
        obj = context.object
    if prop.use_object_axis and obj is not None:
        return obj.ph_place_tool_axis, obj.ph_place_tool_invert_axis
    return prop.axis, prop.invert_axis
