import bpy
import os
from pathlib import Path

from bpy.types import PropertyGroup
from bpy.props import StringProperty, BoolProperty, IntProperty, FloatProperty, EnumProperty,PointerProperty
from bpy.app.translations import pgettext_iface as tips_


class PlaceToolProps(PropertyGroup):
    orient: EnumProperty(name="Orientation",
                         items=[("OBJECT", "Default", "Keep Object Rotation", "ORIENTATION_GLOBAL", 0),
                                ("NORMAL", "Surface", "Set Object Rotation to Hit Normal", "SNAP_NORMAL", 1)],
                         default="NORMAL")

    axis: EnumProperty(name="Axis",
                       items=[("X", "X", ''),
                                ("Y", "Y", ''),
                                ("Z", "Z", '')],
                          default="Z")
    invert_axis: BoolProperty(name="Invert Axis", default=False)
    coll_hide: BoolProperty(name='Keep Color When Intersecting', default=False)
    coll_stop: BoolProperty(name="Stop When Intersecting", default=False)

    duplicate: EnumProperty(name='Duplicate',
                            items=[("INSTANCE", "Instance", "Create a Instance of the Active Object"),
                                   ("COPY", "Object", "Create a Full Copy of the Active Object"), ],
                            default="INSTANCE")

    # exclude_collection:PointerProperty(type = bpy.types.Collection, name = "Exclude", description = "Exclude Collection")

    active_bbox_calc_mode: EnumProperty(name='Active',
                                        items=[('ACCURATE', 'Final', 'Use visual obj bounding box, slower'),
                                               ('FAST', 'Base', 'Use basic mesh bounding box, faster'), ],
                                        default='ACCURATE')

    other_bbox_calc_mode: EnumProperty(name='Others',
                                       items=[('ACCURATE', 'Final', 'Use visual obj bounding box, slower'),
                                              ('FAST', 'Base', 'Use basic mesh bounding box, faster'), ],
                                       default='ACCURATE')



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
         {"type": 'LEFTMOUSE', "value": 'CLICK_DRAG', "shift": False},
         {"properties": []}),

        ("ph.move_object",
         {"type": 'LEFTMOUSE', "value": 'CLICK_DRAG',"shift":True},
         {"properties": []}),
    )

    def draw_settings(context, layout, tool):
        prop = bpy.context.scene.place_tool
        layout.prop(prop, "orient")
        if prop.orient == "NORMAL":
            layout.prop(prop, "axis")
            layout.prop(prop, "invert_axis")
        layout.prop(prop, "duplicate")


        layout.popover(panel="PH_PT_PlaceTool", text = '',icon = 'PREFERENCES')

class PH_PT_PlaceToolPanel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_label = "Place"
    bl_idname = "PH_PT_PlaceTool"

    def draw(self, context):
        layout = self.layout

        prop = context.scene.place_tool

        layout.label(text= 'Performance')
        col = layout.column()
        col.use_property_split = True
        col.use_property_decorate = False

        row = col.row(align=True)
        row.prop(prop, "active_bbox_calc_mode")
        row = col.row(align=True)
        row.prop(prop, "other_bbox_calc_mode")
        layout.separator()

        layout.label(text= 'Collisions')
        layout.prop(prop, "coll_stop")
        layout.prop(prop, "coll_hide")



def register():
    bpy.utils.register_class(PlaceToolProps)
    bpy.types.Scene.place_tool = bpy.props.PointerProperty(type=PlaceToolProps)

    bpy.utils.register_tool(PH_TL_PlaceTool, separator=True)
    bpy.utils.register_class(PH_PT_PlaceToolPanel)



def unregister():
    bpy.utils.unregister_tool(PH_TL_PlaceTool)
    bpy.utils.unregister_class(PH_PT_PlaceToolPanel)
    # del bpy.types.Scene.place_tool
    bpy.utils.unregister_class(PlaceToolProps)
