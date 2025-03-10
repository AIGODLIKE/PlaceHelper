from pathlib import Path

import bpy
from bpy.props import BoolProperty, EnumProperty
from bpy.types import PropertyGroup

from .gzg import update_gzg_pref


class PlaceToolProps(PropertyGroup):
    orient: EnumProperty(name="Orientation",
                         items=[("OBJECT", "Default", "Keep Object Rotation", "ORIENTATION_GLOBAL", 0),
                                ("NORMAL", "Surface", "Set Object Rotation to Hit Normal", "SNAP_NORMAL", 1)],
                         default="NORMAL")

    axis: EnumProperty(name="Axis",
                       items=[("X", "X", ""),
                              ("Y", "Y", ""),
                              ("Z", "Z", "")],
                       default="Z", update=update_gzg_pref)
    setting_axis: BoolProperty(name="Setting Axis", default=False)

    invert_axis: BoolProperty(name="Invert Axis", default=False, update=update_gzg_pref)
    # coll_hide: BoolProperty(name="Keep Color When Intersecting", default=False)
    coll_stop: BoolProperty(name="Stop When Intersecting", default=False)

    duplicate: EnumProperty(name="Duplicate",
                            items=[("INSTANCE", "Instance", "Create a Instance of the Active Object"),
                                   ("COPY", "Object", "Create a Full Copy of the Active Object"), ],
                            default="INSTANCE")

    # exclude_collection:PointerProperty(type = bpy.types.Collection, name = "Exclude", description = "Exclude Collection")

    active_bbox_calc_mode: EnumProperty(name="Active",
                                        items=[("ACCURATE", "Final", "Use visual obj bounding box, slower"),
                                               ("FAST", "Base", "Use basic mesh bounding box, faster"), ],
                                        default="ACCURATE")

    other_bbox_calc_mode: EnumProperty(name="Scene Objects",
                                       items=[("ACCURATE", "Final", "Use visual obj bounding box, slower"),
                                              ("FAST", "Base", "Use basic mesh bounding box, faster"), ],
                                       default="ACCURATE")
    build_active_inst: BoolProperty(name="Active Instance Bounding Box", default=True)
    build_other_inst: BoolProperty(name="Consider Scene Geo Nodes Instance", default=False)


class PH_TL_PlaceTool(bpy.types.WorkSpaceTool):
    bl_idname = "ph.place_tool"
    bl_space_type = "VIEW_3D"
    bl_context_mode = "OBJECT"
    bl_label = "Place Tool"
    bl_icon = Path(__file__).parent.parent.joinpath("icons", "place_tool").as_posix()
    bl_widget = "PH_GZG_place_tool"
    bl_keymap = (
        ("ph.wrap_view3d_select",
         {"type": "LEFTMOUSE", "value": "CLICK"},
         {"properties": []},
         ),

        ("ph.move_object",
         {"type": "LEFTMOUSE", "value": "CLICK_DRAG", "shift": False},
         {"properties": []}),

        ("ph.move_object",
         {"type": "LEFTMOUSE", "value": "CLICK_DRAG", "shift": True},
         {"properties": []}),

        ("ph.show_place_axis",
         {"type": "LEFTMOUSE", "value": "CLICK", "alt": True},
         {"properties": []}),
    )

    def draw_settings(context, layout, tool):
        prop = bpy.context.scene.place_tool
        layout.prop(prop, "orient")
        if prop.orient == "NORMAL":
            layout.prop(prop, "axis")
            layout.prop(prop, "invert_axis")
        layout.prop(prop, "duplicate")

        layout.popover(panel="PH_PT_PlaceTool", text="", icon="PREFERENCES")


class PH_PT_wrap_view3d_select(bpy.types.Operator):
    bl_idname = "ph.wrap_view3d_select"
    bl_label = "Select"

    def execute(self, context):
        bpy.ops.view3d.select("INVOKE_DEFAULT", deselect_all=True)
        if not context.object:
            return {"FINISHED"}

        from ..utils.obj_bbox import AlignObject
        from ._runtime import ALIGN_OBJ

        if context.object.type in {"MESH", "CURVE", "SURFACE", "FONT", "LIGHT"}:
            a_obj = ALIGN_OBJ.get("active", None)
            if a_obj and a_obj.obj is context.object:
                pass
            else:
                ALIGN_OBJ["active"] = AlignObject(context.object,
                                                  "ACCURATE",
                                                  True)
        return {"FINISHED"}


class PH_PT_PlaceToolPanel(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_label = "Place"
    bl_idname = "PH_PT_PlaceTool"

    def draw(self, context):
        layout = self.layout

        prop = context.scene.place_tool

        layout.label(text="Performance")
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

        layout.label(text="Collisions")
        layout.prop(prop, "coll_stop")
        # layout.prop(prop, "coll_hide")


class PT_OT_show_place_axis(bpy.types.Operator):
    bl_idname = "ph.show_place_axis"
    bl_label = "Show Place Axis"
    bl_description = "Show Place Axis"

    def invoke(self, context, event):
        self.update_gizmo(context)
        context.window_manager.modal_handler_add(self)

        text = bpy.app.translations.pgettext_iface("Press Right or ESC to cancel setting the axis")
        context.workspace.status_text_set(text)
        context.area.header_text_set(text)
        return {"RUNNING_MODAL"}

    @staticmethod
    def update_gizmo(context, switch_show=True):
        if switch_show:
            prop = context.scene.place_tool
            prop.setting_axis = not prop.setting_axis

        from .gzg import update_gzg_pref
        update_gzg_pref(None, context)
        context.area.tag_redraw()

    @staticmethod
    def clear_text(context):
        context.workspace.status_text_set(None)
        context.area.header_text_set(None)

    def modal(self, context, event):
        if not context.scene.place_tool.setting_axis:
            self.update_gizmo(context, False)
            self.clear_text(context)
            return {"FINISHED"}

        elif event.type in ("RIGHTMOUSE", "ESC"):
            self.update_gizmo(context, True)
            self.clear_text(context)
            return {"CANCELLED"}

        return {"PASS_THROUGH"}


class PH_OT_set_place_axis(bpy.types.Operator):
    bl_idname = "ph.set_place_axis"
    bl_label = "Set Place Axis"
    bl_description = "Set Place Axis"

    axis: EnumProperty(name="Axis",
                       items=[("X", "X", ""),
                              ("Y", "Y", ""),
                              ("Z", "Z", "")],
                       default="Z")
    invert_axis: BoolProperty(name="Invert Axis", default=False)

    def invoke(self, context, event):
        prop = context.scene.place_tool
        prop.axis = self.axis
        prop.invert_axis = self.invert_axis
        prop.setting_axis = False
        from .gzg import update_gzg_pref
        update_gzg_pref(None, context)
        return {"FINISHED"}


def register():
    bpy.utils.register_class(PlaceToolProps)
    bpy.types.Scene.place_tool = bpy.props.PointerProperty(type=PlaceToolProps)
    bpy.types.Object.place_tool_rotation = bpy.props.FloatProperty(default=0, subtype="ANGLE")
    bpy.types.Object.place_tool_z_offset = bpy.props.FloatProperty(default=0)

    bpy.utils.register_class(PH_PT_PlaceToolPanel)
    bpy.utils.register_class(PH_PT_wrap_view3d_select)
    bpy.utils.register_class(PH_OT_set_place_axis)
    bpy.utils.register_class(PT_OT_show_place_axis)

    bpy.utils.register_tool(PH_TL_PlaceTool, separator=True)


def unregister():
    bpy.utils.unregister_tool(PH_TL_PlaceTool)

    bpy.utils.unregister_class(PH_PT_PlaceToolPanel)
    bpy.utils.unregister_class(PH_PT_wrap_view3d_select)
    bpy.utils.unregister_class(PH_OT_set_place_axis)
    bpy.utils.unregister_class(PT_OT_show_place_axis)
    bpy.utils.unregister_class(PlaceToolProps)

    del bpy.types.Scene.place_tool
    del bpy.types.Object.place_tool_rotation
    del bpy.types.Object.place_tool_z_offset
