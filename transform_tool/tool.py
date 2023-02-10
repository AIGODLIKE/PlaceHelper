import bpy
import os
from pathlib import Path

from bpy.types import PropertyGroup
from bpy.props import StringProperty, BoolProperty, IntProperty, FloatProperty, EnumProperty

from bpy.utils.toolsystem import ToolDef


class MoveToolProps(PropertyGroup):
    orient: EnumProperty(name="Orientation",
                         items=[("OBJECT", "Default", "Keep Object Rotation", "ORIENTATION_GLOBAL", 0),
                                ("NORMAL", "Surface", "Set Object Rotation to Hit Normal", "SNAP_NORMAL", 1)],
                         default="NORMAL")

    duplicate: EnumProperty(name='Duplicate',
                            items=[("INSTANCE", "Instance", "Create a Instance of the Active Object"),
                                   ("COPY", "Object", "Create a Full Copy of the Active Object"), ],
                            default="COPY")


class PH_TL_TransformPro(bpy.types.WorkSpaceTool):
    bl_idname = "ph.transform_pro"
    bl_space_type = 'VIEW_3D'
    bl_context_mode = "OBJECT"
    bl_label = "Transform Pro"
    bl_widget = "PH_GZG_transform_pro"
    bl_icon = Path(__file__).parent.parent.joinpath("icons", "move_view").as_posix()
    bl_keymap = "3D View Tool: Select Box"

    def draw_settings(context, layout, tool):
        prop = bpy.context.scene.move_view_tool
        layout.prop(prop, "duplicate")

class PH_TL_TransformPro_edit(bpy.types.WorkSpaceTool):
    bl_idname = "ph.transform_pro_edit"
    bl_space_type = 'VIEW_3D'
    bl_context_mode = "EDIT_MESH"
    bl_label = "Transform Pro"
    bl_widget = "PH_GZG_transform_pro"
    bl_icon = Path(__file__).parent.parent.joinpath("icons", "move_view").as_posix()
    bl_keymap = "3D View Tool: Select Box"

    def draw_settings(context, layout, tool):
        prop = bpy.context.scene.move_view_tool
        layout.prop(prop, "duplicate")

def register():
    bpy.utils.register_class(MoveToolProps)
    bpy.types.Scene.move_view_tool = bpy.props.PointerProperty(type=MoveToolProps)

    bpy.utils.register_tool(PH_TL_TransformPro, separator=False)
    bpy.utils.register_tool(PH_TL_TransformPro_edit, separator=False)


def unregister():
    bpy.utils.unregister_tool(PH_TL_TransformPro)
    bpy.utils.unregister_tool(PH_TL_TransformPro_edit)

    del  bpy.types.Scene.place_tool
    bpy.utils.unregister_class(MoveToolProps)