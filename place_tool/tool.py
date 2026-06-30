from pathlib import Path

import bpy
from bpy.props import BoolProperty, EnumProperty
from bpy.types import PropertyGroup

from .gzg import update_gzg_pref
from .axis import AXIS_ITEMS
from ..utils import EXIT_TO_SELECT_BOX_KEYMAP


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
    use_object_axis: BoolProperty(
        name="Use Object Axis",
        description="Use the per-object up axis instead of the scene axis",
        default=True,
        update=update_gzg_pref)
    # coll_hide: BoolProperty(name="Keep Color When Intersecting", default=False)
    coll_stop: BoolProperty(name="Stop When Intersecting", default=False)
    limit_to_ground: BoolProperty(name="Limit to Ground",
                                  description="Prevent placed objects from going below the Z=0 ground plane "
                                              "while moving",
                                  default=False)

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
        ("object.ph_wrap_view3d_select",
         {"type": "LEFTMOUSE", "value": "CLICK"},
         {"properties": []},
         ),

        # Alt + 拖动：框选（即使已选中物体也可用，不与移动手势冲突）
        ("object.ph_place_box_select",
         {"type": "LEFTMOUSE", "value": "CLICK_DRAG", "alt": True},
         {"properties": []}),

        ("object.ph_move_object",
         {"type": "LEFTMOUSE", "value": "CLICK_DRAG", "shift": False},
         {"properties": []}),

        ("object.ph_move_object",
         {"type": "LEFTMOUSE", "value": "CLICK_DRAG", "shift": True},
         {"properties": []}),

        ("object.ph_show_place_axis",
         {"type": "LEFTMOUSE", "value": "CLICK", "alt": True},
         {"properties": []}),
    ) + EXIT_TO_SELECT_BOX_KEYMAP

    def draw_settings(context, layout, tool):
        from ..help_overlay import draw_help_toggle
        draw_help_toggle(layout)
        prop = bpy.context.scene.place_tool
        layout.prop(prop, "orient")
        if prop.orient == "NORMAL":
            layout.prop(prop, "use_object_axis")
            obj = context.object
            if prop.use_object_axis and obj is not None:
                layout.prop(obj, "ph_place_tool_axis", text="Axis")
                layout.prop(obj, "ph_place_tool_invert_axis")
            else:
                layout.prop(prop, "axis")
                layout.prop(prop, "invert_axis")
        layout.prop(prop, "duplicate")
        layout.prop(prop, "limit_to_ground", text="", icon="CON_FLOOR", toggle=True)

        layout.popover(panel="PH_PT_PlaceTool", text="", icon="PREFERENCES")


class PH_OT_place_box_select(bpy.types.Operator):
    bl_idname = "object.ph_place_box_select"
    bl_label = "Box Select"
    bl_description = "Box select objects by dragging on empty space"

    _timer = None
    _finishing = False

    def invoke(self, context, event):
        self._finishing = False
        try:
            bpy.ops.view3d.select_box("INVOKE_DEFAULT")
        except Exception:
            return {"CANCELLED"}
        # 用定时器等待 select_box 模态结束后再补设活动物体
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.01, window=context.window)
        wm.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        # select_box 在左键释放（确认）或右键/ESC（取消）时结束
        if event.type == "LEFTMOUSE" and event.value == "RELEASE":
            self._finishing = True
        elif event.type in {"RIGHTMOUSE", "ESC"} and event.value == "PRESS":
            self._finishing = True

        # 让事件继续传递给 select_box，待其处理完选择后于下一个 TIMER 收尾
        if self._finishing and event.type == "TIMER":
            self._ensure_active(context)
            self._cleanup(context)
            return {"FINISHED"}
        return {"PASS_THROUGH"}

    @staticmethod
    def _ensure_active(context):
        """若没有有效的活动物体，则把第一个选中物体设为活动物体。"""
        view_layer = context.view_layer
        active = view_layer.objects.active
        try:
            if active is not None and active.select_get():
                return
        except Exception:
            pass
        selected = context.selected_objects
        if selected:
            view_layer.objects.active = selected[0]
            if context.area:
                context.area.tag_redraw()

    def _cleanup(self, context):
        if self._timer is not None:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None


class PH_PT_wrap_view3d_select(bpy.types.Operator):
    bl_idname = "object.ph_wrap_view3d_select"
    bl_label = "Select"

    def execute(self, context):
        bpy.ops.view3d.select("INVOKE_DEFAULT", deselect_all=True)
        if not context.object:
            return {"FINISHED"}

        from ..utils.obj_bbox import AlignObject
        from ._runtime import ALIGN_OBJ, SCENE_OBJS

        if context.object.type in {"MESH", "CURVE", "SURFACE", "FONT", "LIGHT"}:
            active_name = ALIGN_OBJ.get("active_name")
            if active_name and active_name == context.object.name:
                pass
            else:
                align_obj = AlignObject(context.object, "ACCURATE", True)
                SCENE_OBJS[context.object.name] = align_obj
                ALIGN_OBJ["active_name"] = context.object.name
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
        layout.separator()

        layout.label(text="Ground")
        layout.prop(prop, "limit_to_ground")


class PT_OT_show_place_axis(bpy.types.Operator):
    bl_idname = "object.ph_show_place_axis"
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
    bl_idname = "object.ph_set_place_axis"
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
        if prop.use_object_axis and context.object is not None:
            context.object.ph_place_tool_axis = self.axis
            context.object.ph_place_tool_invert_axis = self.invert_axis
        else:
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
    bpy.types.Object.ph_place_tool_axis = EnumProperty(
        name="Axis",
        items=AXIS_ITEMS,
        default="Z",
        update=update_gzg_pref,
    )
    bpy.types.Object.ph_place_tool_invert_axis = BoolProperty(
        name="Invert Axis",
        default=False,
        update=update_gzg_pref,
    )

    bpy.utils.register_class(PH_PT_PlaceToolPanel)
    bpy.utils.register_class(PH_PT_wrap_view3d_select)
    bpy.utils.register_class(PH_OT_place_box_select)
    bpy.utils.register_class(PH_OT_set_place_axis)
    bpy.utils.register_class(PT_OT_show_place_axis)

    bpy.utils.register_tool(PH_TL_PlaceTool, separator=True)


def unregister():
    bpy.utils.unregister_tool(PH_TL_PlaceTool)

    bpy.utils.unregister_class(PH_PT_PlaceToolPanel)
    bpy.utils.unregister_class(PH_PT_wrap_view3d_select)
    bpy.utils.unregister_class(PH_OT_place_box_select)
    bpy.utils.unregister_class(PH_OT_set_place_axis)
    bpy.utils.unregister_class(PT_OT_show_place_axis)
    bpy.utils.unregister_class(PlaceToolProps)

    del bpy.types.Scene.place_tool
    del bpy.types.Object.place_tool_rotation
    del bpy.types.Object.place_tool_z_offset
    del bpy.types.Object.ph_place_tool_axis
    del bpy.types.Object.ph_place_tool_invert_axis
