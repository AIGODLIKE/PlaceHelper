import bpy
import os
from pathlib import Path

from bpy.types import PropertyGroup
from bpy.props import StringProperty, BoolProperty, IntProperty, FloatProperty, EnumProperty, PointerProperty
from bpy.app.translations import pgettext_iface as tips_

from .gzg import update_gzg_pref


class PlaceToolProps(PropertyGroup):
    orient: EnumProperty(name="Orientation",
                         items=[("OBJECT", "Default", "Keep Object Rotation", "ORIENTATION_GLOBAL", 0),
                                ("NORMAL", "Surface", "Set Object Rotation to Hit Normal", "SNAP_NORMAL", 1)],
                         default="NORMAL")

    axis: EnumProperty(name="Axis",
                       items=[("X", "X", ''),
                              ("Y", "Y", ''),
                              ("Z", "Z", '')],
                       default="Z", update=update_gzg_pref)
    setting_axis: BoolProperty(name="Setting Axis", default=False)

    invert_axis: BoolProperty(name="Invert Axis", default=False, update=update_gzg_pref)
    # coll_hide: BoolProperty(name='Keep Color When Intersecting', default=False)
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

    other_bbox_calc_mode: EnumProperty(name='Scene Objects',
                                       items=[('ACCURATE', 'Final', 'Use visual obj bounding box, slower'),
                                              ('FAST', 'Base', 'Use basic mesh bounding box, faster'), ],
                                       default='ACCURATE')
    build_active_inst: BoolProperty(name='Active Instance Bounding Box', default=True)
    build_other_inst: BoolProperty(name='Consider Scene Geo Nodes Instance', default=False)


class PH_TL_PlaceTool(bpy.types.WorkSpaceTool):
    bl_idname = "ph.place_tool"
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'OBJECT'
    bl_label = "Place"
    bl_icon = Path(__file__).parent.parent.joinpath("icons", "place_tool").as_posix()
    bl_widget = "PH_GZG_place_tool"
    bl_keymap = (
        ("ph.wrap_view3d_select",
         {"type": "LEFTMOUSE", "value": "CLICK"},
         {"properties": []},  # [("deselect_all", True)]
         ),

        ("ph.move_object",
         {"type": 'LEFTMOUSE', "value": 'CLICK_DRAG', "shift": False},
         {"properties": []}),

        ("ph.move_object",
         {"type": 'LEFTMOUSE', "value": 'CLICK_DRAG', "shift": True},
         {"properties": []}),

        ("ph.show_place_axis",
         {"type": 'LEFTMOUSE', "value": 'CLICK', "alt": True},
         {"properties": []}),

        ("test.test_place",
         {"type": 'LEFTMOUSE', "value": 'CLICK_DRAG', "ctrl": True},
         {"properties": []}),
    )

    def draw_settings(context, layout, tool):
        prop = bpy.context.scene.place_tool
        layout.prop(prop, "orient")
        if prop.orient == "NORMAL":
            layout.prop(prop, "axis")
            layout.prop(prop, "invert_axis")
        layout.prop(prop, "duplicate")

        layout.popover(panel="PH_PT_PlaceTool", text='', icon='PREFERENCES')


class PH_TL_ScatterTool(bpy.types.WorkSpaceTool):
    bl_idname = "ph.scatter_tool"
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'OBJECT'
    bl_label = "Scatter"
    bl_icon = Path(__file__).parent.parent.joinpath("icons", "place_tool").as_posix()
    # bl_widget = "PH_GZG_place_tool"
    bl_keymap = (
        ("view3d.select",
         {"type": "LEFTMOUSE", "value": "CLICK"},
         {"properties": [("deselect_all", True)]},
         ),

        ("ph.scatter_single",
         {"type": 'LEFTMOUSE', "value": 'CLICK_DRAG', "shift": False},
         {"properties": []}),
    )

    def draw_settings(context, layout, tool):
        pass


class PH_PT_wrap_view3d_select(bpy.types.Operator):
    bl_idname = 'ph.wrap_view3d_select'
    bl_label = 'Select'

    def execute(self, context):
        bpy.ops.view3d.select('INVOKE_DEFAULT', deselect_all=True)
        if not context.object: return {'FINISHED'}

        from ..util.obj_bbox import AlignObject
        from ._runtime import ALIGN_OBJ

        if context.object.type in {'MESH', 'CURVE', 'SURFACE', 'FONT'}:
            a_obj = ALIGN_OBJ.get('active', None)
            if a_obj and a_obj.obj is context.object:
                pass
            else:
                ALIGN_OBJ['active'] = AlignObject(context.object,
                                                  'ACCURATE',
                                                  True)
            # context.scene.place_tool.active_bbox_calc_mode,
            # context.scene.place_tool.build_active_inst)

        return {'FINISHED'}


class PH_PT_PlaceToolPanel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_label = "Place"
    bl_idname = "PH_PT_PlaceTool"

    def draw(self, context):
        layout = self.layout

        prop = context.scene.place_tool

        layout.label(text='Performance')
        col = layout.column()
        col.use_property_split = True
        col.use_property_decorate = False

        # row = col.row(align=True)
        # row.prop(prop, "active_bbox_calc_mode")
        layout.prop(prop, "other_bbox_calc_mode")
        # row = col.row(align=True)
        # row.prop(prop, "build_active_inst")
        layout.prop(prop, "build_other_inst")
        layout.separator()

        layout.label(text='Collisions')
        layout.prop(prop, "coll_stop")
        # layout.prop(prop, "coll_hide")


class PT_OT_show_place_axis(bpy.types.Operator):
    bl_idname = 'ph.show_place_axis'
    bl_label = 'Show Place Axis'
    bl_description = 'Show Place Axis'

    def invoke(self, context, event):
        prop = context.scene.place_tool
        prop.setting_axis = True if not prop.setting_axis else False
        from .gzg import update_gzg_pref
        update_gzg_pref(None, context)
        return {'FINISHED'}


class PH_OT_set_place_axis(bpy.types.Operator):
    bl_idname = 'ph.set_place_axis'
    bl_label = 'Set Place Axis'
    bl_description = 'Set Place Axis'

    axis: EnumProperty(name="Axis",
                       items=[("X", "X", ''),
                              ("Y", "Y", ''),
                              ("Z", "Z", '')],
                       default="Z")
    invert_axis: BoolProperty(name="Invert Axis", default=False)

    def invoke(self, context, event):
        prop = context.scene.place_tool
        prop.axis = self.axis
        prop.invert_axis = self.invert_axis
        prop.setting_axis = False
        from .gzg import update_gzg_pref
        update_gzg_pref(None, context)
        return {'FINISHED'}


def register():
    bpy.utils.register_class(PlaceToolProps)
    bpy.types.Scene.place_tool = bpy.props.PointerProperty(type=PlaceToolProps)

    bpy.utils.register_tool(PH_TL_PlaceTool, separator=True)
    # bpy.utils.register_tool(PH_TL_ScatterTool, separator=False)

    bpy.utils.register_class(PH_PT_wrap_view3d_select)
    bpy.utils.register_class(PH_PT_PlaceToolPanel)
    bpy.utils.register_class(PH_OT_set_place_axis)
    bpy.utils.register_class(PT_OT_show_place_axis)


def unregister():
    bpy.utils.unregister_tool(PH_TL_PlaceTool)
    # bpy.utils.unregister_tool(PH_TL_ScatterTool)

    bpy.utils.unregister_class(PH_PT_PlaceToolPanel)
    bpy.utils.unregister_class(PH_PT_wrap_view3d_select)
    bpy.utils.unregister_class(PH_OT_set_place_axis)
    bpy.utils.unregister_class(PT_OT_show_place_axis)
    # del bpy.types.Scene.place_tool
    bpy.utils.unregister_class(PlaceToolProps)
