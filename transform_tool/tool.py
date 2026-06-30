from pathlib import Path

import bpy
from bpy.props import EnumProperty, BoolProperty
from bpy.types import PropertyGroup

from ..utils import get_pref, SELECT_BOX_KEYMAP, EXIT_TO_SELECT_BOX_KEYMAP


def _redraw_view3d(self, context):
    if context and context.area:
        context.area.tag_redraw()


class MoveToolProps(PropertyGroup):
    orient: EnumProperty(name="Orientation",
                         items=[("OBJECT", "Default", "Keep Object Rotation", "ORIENTATION_GLOBAL", 0),
                                ("NORMAL", "Surface", "Set Object Rotation to Hit Normal", "SNAP_NORMAL", 1)],
                         default="NORMAL")

    duplicate: EnumProperty(name='Duplicate',
                            items=[("INSTANCE", "Instance", "Create a Instance of the Active Object"),
                                   ("COPY", "Object", "Create a Full Copy of the Active Object"), ],
                            default="COPY")

    show_gizmo: BoolProperty(
        name="Show Gizmo",
        description="Show the move gizmos. When off, drag an object directly with the left mouse button to move it",
        default=False,
        update=_redraw_view3d,
    )


class PH_TL_TransformPro(bpy.types.WorkSpaceTool):
    bl_idname = "ph.transform_pro"
    bl_space_type = 'VIEW_3D'
    bl_context_mode = "OBJECT"
    bl_label = "Transform Pro"
    bl_widget = "PH_GZG_transform_pro"
    bl_icon = Path(__file__).parent.parent.joinpath("icons", "move_view").as_posix()
    bl_keymap = (
        # 双击物体：进入编辑模式
        ("object.ph_transform_enter_edit",
         {"type": "LEFTMOUSE", "value": "DOUBLE_CLICK"},
         {"properties": []}),
        # Shift / Alt + 拖动：复制并移动
        ("object.ph_transform_drag",
         {"type": "LEFTMOUSE", "value": "CLICK_DRAG", "shift": True},
         {"properties": [("duplicate", True)]}),
        ("object.ph_transform_drag",
         {"type": "LEFTMOUSE", "value": "CLICK_DRAG", "alt": True},
         {"properties": [("duplicate", True)]}),
        # 左键拖动：命中物体则移动，空白处则框选
        ("object.ph_transform_drag",
         {"type": "LEFTMOUSE", "value": "CLICK_DRAG"},
         {"properties": [("duplicate", False)]}),
        # 单击：选择
        ("view3d.select",
         {"type": "LEFTMOUSE", "value": "CLICK"},
         {"properties": [("deselect_all", True)]}),
    ) + EXIT_TO_SELECT_BOX_KEYMAP

    @staticmethod
    def draw_settings(context, layout, tool):
        from ..help_overlay import draw_help_toggle
        draw_help_toggle(layout)
        prop = bpy.context.scene.move_view_tool
        pref = get_pref()
        row = layout.row(align=True)
        row.prop(prop, "duplicate")
        row.prop(pref, "transform_gizmo_alpha_vary")
        row.prop(prop, "show_gizmo")


class PH_TL_TransformPro_edit(bpy.types.WorkSpaceTool):
    bl_idname = "ph.transform_pro_edit"
    bl_space_type = 'VIEW_3D'
    bl_context_mode = "EDIT_MESH"
    bl_label = "Transform Pro"
    bl_widget = "PH_GZG_transform_pro"
    bl_icon = Path(__file__).parent.parent.joinpath("icons", "move_view").as_posix()
    bl_keymap = (
        # 双击空白：退出编辑模式（双击几何则正常选择）
        ("object.ph_transform_exit_edit",
         {"type": "LEFTMOUSE", "value": "DOUBLE_CLICK"},
         {"properties": []}),
        # 单击：选择元素
        ("view3d.select",
         {"type": "LEFTMOUSE", "value": "CLICK"},
         {"properties": []}),
    ) + SELECT_BOX_KEYMAP + EXIT_TO_SELECT_BOX_KEYMAP

    @staticmethod
    def draw_settings(context, layout, tool):
        from .op import PH_OT_Clear_mesh

        column = layout.row(align=True)
        PH_TL_TransformPro.draw_settings(context, column, tool)
        column.operator(PH_OT_Clear_mesh.bl_idname)


def register():
    bpy.utils.register_class(MoveToolProps)
    bpy.types.Scene.move_view_tool = bpy.props.PointerProperty(type=MoveToolProps)

    bpy.utils.register_tool(PH_TL_TransformPro, separator=False)
    bpy.utils.register_tool(PH_TL_TransformPro_edit, separator=False)


def unregister():
    bpy.utils.unregister_tool(PH_TL_TransformPro)
    bpy.utils.unregister_tool(PH_TL_TransformPro_edit)

    bpy.utils.unregister_class(MoveToolProps)

    del bpy.types.Scene.move_view_tool
