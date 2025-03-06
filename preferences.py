import bpy
from bpy.props import IntProperty, BoolProperty, FloatProperty, EnumProperty, FloatVectorProperty, \
    PointerProperty
from bpy.types import AddonPreferences, PropertyGroup

from .place_tool.gzg import update_gzg_pref


class PlaceToolBBoxProps(PropertyGroup):
    offset: FloatProperty(name="Geometry Offset", default=0.00001, min=0.0, max=0.001, step=1, precision=5)
    # display
    width: FloatProperty(name="Width", min=1, max=5, default=2)
    coll_alert: BoolProperty(name="Collision Alert", default=False)
    color: FloatVectorProperty(name="Color", subtype="COLOR", size=4, default=(0.8, 0.8, 0.1, 1.0), max=1, min=0)
    color_alert: FloatVectorProperty(name="Collision", subtype="COLOR", size=4,
                                     default=(1.0, 0.0, 0.0, 1.0), max=1, min=0)


class PlaceToolGizmoProps(PropertyGroup):
    scale_basis: FloatProperty(name="Scale", default=0.5, min=0.1, max=2, update=update_gzg_pref)
    color: FloatVectorProperty(name="Color", subtype="COLOR", size=3, default=(0.48, 0.4, 1), update=update_gzg_pref)
    color_highlight: FloatVectorProperty(name="Highlight", subtype="COLOR", size=3, default=(1, 1, 1),
                                         update=update_gzg_pref)


class PlaceToolProps(PropertyGroup):
    bbox: PointerProperty(type=PlaceToolBBoxProps)
    gz: PointerProperty(name="Gizmo", type=PlaceToolGizmoProps)


class DynamicPlaceToolProps(PropertyGroup):
    use_color: BoolProperty(name="Use Color When Moving", default=True)
    active_color: FloatVectorProperty(name="Active", subtype="COLOR", size=4, default=(1, 0.095, 0.033, 1.0), max=1,
                                      min=0)
    passive_color: FloatVectorProperty(name="Passive", subtype="COLOR", size=4, default=(0.023, 0.233, 0.776, 1.0),
                                       max=1,
                                       min=0)


class Preferences(AddonPreferences):
    bl_idname = __package__

    tool_type: EnumProperty(name="Tool", items=[("PLACE_TOOL", "Place", ""), ("TRANSFORM_TOOL", "Transform", ""),
                                                ("DYNAMIC_PLACE_TOOL", "Dynamic Place", "")], default="PLACE_TOOL")

    place_tool: PointerProperty(type=PlaceToolProps)
    dynamic_place_tool: PointerProperty(type=DynamicPlaceToolProps)
    #
    use_event_handle_all: BoolProperty(name="Gizmo Handle All Event", default=False)
    debug: BoolProperty(name="Debug", default=False)

    event_normal_adsorption_angle: IntProperty(name="General", default=15, min=1, max=180, subtype="ANGLE")
    event_ctrl_adsorption_angle: IntProperty(name="Ctrl", default=1, min=1, max=180, subtype="ANGLE")
    event_alt_adsorption_angle: IntProperty(name="Alt", default=45, min=1, max=180, subtype="ANGLE")

    event_normal_adsorption_z_offset: FloatProperty(name="General", default=1, min=0.01, max=180)
    event_ctrl_adsorption_z_offset: FloatProperty(name="Ctrl", default=0.1, min=0.1, max=180)
    event_alt_adsorption_z_offset: FloatProperty(name="Alt", default=5, min=0.1, max=180)

    gizmo_alpha: FloatProperty(name="Gizmo Alpha", default=0.5, min=0.1, max=1)

    def draw(self, context):
        layout = self.layout

        row_all = layout.split(factor=0.2)

        col = row_all.column(align=True)
        col.prop(self, "tool_type", expand=True)
        col.separator()

        col = row_all.column()

        if self.tool_type == "PLACE_TOOL":
            self.draw_place_tool(context, col)
        elif self.tool_type == "TRANSFORM_TOOL":
            pass
        elif self.tool_type == "DYNAMIC_PLACE_TOOL":
            self.draw_dynamic_place_tool(context, col)
        col.separator()
        column = col.box().column(align=True)
        column.prop(self, "use_event_handle_all")
        column.prop(self, "gizmo_alpha")
        # layout.prop(self, "debug")

    def draw_event_adsorption_angle(self, context, layout):
        column = layout.column(align=True)
        column.label(text="Adsorption Angle")
        column.prop(self, "event_ctrl_adsorption_angle")
        column.prop(self, "event_normal_adsorption_angle")
        column.prop(self, "event_alt_adsorption_angle")

    def draw_event_adsorption_z_offset(self, context, layout):
        column = layout.column(align=True)
        column.label(text="Adsorption Z Offset")
        column.prop(self, "event_ctrl_adsorption_z_offset")
        column.prop(self, "event_normal_adsorption_z_offset")
        column.prop(self, "event_alt_adsorption_z_offset")

    def draw_dynamic_place_tool(self, context, layout):
        col = layout.box().column()
        col.use_property_split = True

        col.label(text="Display")
        tool = self.dynamic_place_tool
        col.active = tool.use_color
        col.prop(tool, "use_color")
        col.prop(tool, "active_color")
        col.prop(tool, "passive_color")

        self.draw_event_adsorption_angle(context, col.box())

    def draw_place_tool(self, context, layout):
        _layout = layout.column()

        col = _layout.box().column()
        col.use_property_split = True

        col.label(text="Bounding Box", icon="META_CUBE")
        col1 = col.column()
        bbox = self.place_tool.bbox
        col1.prop(bbox, "offset")

        col2 = col.column(heading="Display")
        col2.prop(bbox, "coll_alert")
        col2.prop(bbox, "width")
        col2.prop(bbox, "color")
        if bbox.coll_alert:
            col2.prop(bbox, "color_alert")

        col = _layout.box().column()
        col.use_property_split = True

        col.label(text="Gizmos", icon="GIZMO")
        col.separator()

        box = col.box().column()
        box.prop(self.place_tool.gz, "scale_basis", slider=True)
        box.prop(self.place_tool.gz, "color")
        box.prop(self.place_tool.gz, "color_highlight")
        self.draw_event_adsorption_angle(context, col.box())
        self.draw_event_adsorption_z_offset(context, col.box())

        self.draw_place_tool_keymap(context, col)

    def draw_place_tool_keymap(self, context, layout):
        column = layout.box().column(align=True)

        column.label(text="Keymaps")

        kc = context.window_manager.keyconfigs.user

        key = "3D View Tool: Object, Place Tool"
        if key in kc.keymaps:
            import rna_keymap_ui
            km = kc.keymaps[key]
            for kmi in km.keymap_items:
                col = column.column(align=True)
                if kmi.is_user_modified:
                    col.context_pointer_set("keymap", km)
                rna_keymap_ui.draw_kmi(["ADDON", "USER", "DEFAULT"], kc, km, kmi, col, 0)

        else:
            column.label(text=bpy.app.translations.pgettext_iface("Not in User Keymap Found %s") % key)


def register():
    bpy.utils.register_class(PlaceToolBBoxProps)
    bpy.utils.register_class(PlaceToolGizmoProps)
    bpy.utils.register_class(PlaceToolProps)
    bpy.utils.register_class(DynamicPlaceToolProps)
    bpy.utils.register_class(Preferences)


def unregister():
    bpy.utils.unregister_class(PlaceToolBBoxProps)
    bpy.utils.unregister_class(PlaceToolGizmoProps)
    bpy.utils.unregister_class(PlaceToolProps)
    bpy.utils.unregister_class(DynamicPlaceToolProps)
    bpy.utils.unregister_class(Preferences)
