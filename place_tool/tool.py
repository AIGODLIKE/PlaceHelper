import bpy
import os
from pathlib import Path

from bpy.types import PropertyGroup
from bpy.props import StringProperty, BoolProperty, IntProperty, FloatProperty, EnumProperty
from bpy.app.translations import pgettext_iface as tips_


class PlaceToolProps(PropertyGroup):
    orient: EnumProperty(name="Orientation",
                         items=[("OBJECT", "Default", "Keep Object Rotation", "ORIENTATION_GLOBAL", 0),
                                ("NORMAL", "Surface", "Set Object Rotation to Hit Normal", "SNAP_NORMAL", 1)],
                         default="NORMAL")

    coll_hide: BoolProperty(name='Hide', default=False)
    coll_stop: BoolProperty(name="Collision", default=False)

    duplicate: EnumProperty(name='Duplicate',
                            items=[("INSTANCE", "Instance", "Create a Instance of the Active Object"),
                                   ("COPY", "Object", "Create a Full Copy of the Active Object"), ],
                            default="INSTANCE")


class DynamicPlaceProps(PropertyGroup):
    mode: EnumProperty(name='Mode', items=[('GRAVITY', 'Gravity', 'Gravity'), ('FORCE', 'Force', 'Force')],
                       default='FORCE')


class PH_TL_PlaceTool(bpy.types.WorkSpaceTool):
    bl_idname = "ph.place_tool"
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'OBJECT'
    bl_label = "Place"
    bl_icon = Path(__file__).parent.parent.joinpath("icons", "place_tool").as_posix()
    bl_widget = "PH_GZG_place_tool"
    bl_keymap = (
        ("view3d.select",
         {"type": "LEFTMOUSE", "value": "CLICK"},
         {"properties": [("deselect_all", True)]},
         ),

        ("ph.move_object",
         {"type": 'LEFTMOUSE', "value": 'CLICK_DRAG'},
         {"properties": []}),
    )

    def draw_settings(context, layout, tool):
        prop = bpy.context.scene.place_tool
        layout.prop(prop, "orient")
        layout.prop(prop, "duplicate")

        row = layout.row(align=True)
        row.label(text=tips_('Collision') + ':')
        row.prop(prop, "coll_stop", icon='OBJECT_ORIGIN', text='Stop')
        row.prop(prop, "coll_hide", icon='ERROR' if not prop.coll_hide else 'PIVOT_BOUNDBOX', text='')




def register():
    bpy.utils.register_class(PlaceToolProps)
    bpy.utils.register_class(DynamicPlaceProps)
    bpy.types.Scene.place_tool = bpy.props.PointerProperty(type=PlaceToolProps)
    bpy.types.Scene.dynamic_place_tool = bpy.props.PointerProperty(type=DynamicPlaceProps)

    bpy.utils.register_tool(PH_TL_PlaceTool, separator=True)


def unregister():
    bpy.utils.unregister_tool(PH_TL_PlaceTool)

    bpy.utils.unregister_class(DynamicPlaceProps)
    bpy.utils.unregister_class(PlaceToolProps)
