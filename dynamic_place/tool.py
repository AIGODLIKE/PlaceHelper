import bpy


class DynamicPlace_TL_WorkSpaceTool(bpy.types.WorkSpaceTool):
    bl_idname = "ph.dynamic_place"
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'OBJECT'
    bl_label = "Dynamic Place"
    bl_widget = "PH_GZG_Dynamic_Place"
    bl_icon = "ops.transform.transform"
    bl_keymap = "3D View Tool: Select Box"

    def draw_settings(context, layout, tool):
        prop = bpy.context.scene.dynamic_place_tool
        layout.label(text="aa")


def register():
    bpy.utils.register_tool(DynamicPlace_TL_WorkSpaceTool, separator=False)


def unregister():
    bpy.utils.unregister_tool(DynamicPlace_TL_WorkSpaceTool)
