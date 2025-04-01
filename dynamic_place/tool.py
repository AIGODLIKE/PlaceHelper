import bpy


class DynamicPlace_TL_WorkSpaceTool(bpy.types.WorkSpaceTool):
    bl_idname = "ph.dynamic_place"
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'OBJECT'
    bl_label = "Force Field Dynamic Place"
    bl_widget = "PH_GZG_Dynamic_Place"
    bl_icon = "ops.transform.shrink_fatten"
    bl_keymap = "3D View Tool: Select Box"

    @staticmethod
    def draw_settings(context, layout, tool):
        context.scene.dynamic_place.draw(layout)


def register():
    bpy.utils.register_tool(DynamicPlace_TL_WorkSpaceTool, separator=False)


def unregister():
    bpy.utils.unregister_tool(DynamicPlace_TL_WorkSpaceTool)
