import bpy
import os
from pathlib import Path

from bpy.types import PropertyGroup
from bpy.props import StringProperty, BoolProperty, IntProperty, FloatProperty, EnumProperty


class MoveToolProps(PropertyGroup):
    orient: EnumProperty(name="Orientation",
                         items=[("OBJECT", "Default", "Keep Object Rotation", "ORIENTATION_GLOBAL", 0),
                                ("NORMAL", "Surface", "Set Object Rotation to Hit Normal", "SNAP_NORMAL", 1)],
                         default="NORMAL")

    duplicate: EnumProperty(name='Duplicate',
                            items=[("INSTANCE", "Instance", "Create a Instance of the Active Object"),
                                   ("COPY", "Object", "Create a Full Copy of the Active Object"), ],
                            default="COPY")


class TestTool2(bpy.types.WorkSpaceTool):
    bl_idname = "TEST.test_tool2"
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'OBJECT'
    bl_label = "Test"
    bl_widget = "TEST_GGT_test_group2"
    bl_icon = Path(__file__).parent.parent.joinpath("icons", "move_view").as_posix()
    bl_keymap = "3D View Tool: Select Box"

    def draw_settings(context, layout, tool):
        prop = bpy.context.scene.move_view_tool
        layout.prop(prop, "duplicate")

def register():
    bpy.utils.register_class(MoveToolProps)
    bpy.types.Scene.move_view_tool = bpy.props.PointerProperty(type=MoveToolProps)

    bpy.utils.register_tool(TestTool2, separator=False)


def unregister():
    bpy.utils.unregister_tool(TestTool2)
    del  bpy.types.Scene.place_tool
    bpy.utils.unregister_class(MoveToolProps)