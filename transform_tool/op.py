from math import radians

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatVectorProperty
from bpy_extras import view3d_utils
from mathutils import Quaternion

from ..utils import get_pref

C_OBJECT_TYPE_HAS_BBOX = {"MESH", "CURVE", "FONT", "LATTICE"}

# 双击可进入编辑模式的物体类型
C_EDITABLE_TYPES = {"MESH", "CURVE", "SURFACE", "FONT", "META", "LATTICE", "ARMATURE"}


def _object_under_cursor(context, event):
    """对光标位置做场景射线检测，命中返回物体，否则返回 None。"""
    region = context.region
    rv3d = getattr(context, "region_data", None)
    if region is None or rv3d is None:
        return None
    coord = (event.mouse_region_x, event.mouse_region_y)
    try:
        view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        depsgraph = context.evaluated_depsgraph_get()
        result, _loc, _no, _idx, obj, _mx = context.scene.ray_cast(depsgraph, ray_origin, view_vector)
    except Exception:
        return None
    return obj if result else None


class PH_OT_translate(bpy.types.Operator):
    bl_idname = "object.ph_translate"
    bl_label = "Translate"
    bl_description = "Translate"
    # bl_options = {"REGISTER", "UNDO"}

    axis: EnumProperty(
        name="Axis",
        description="Axis",
        items=[
            ("X", "X", "", "", 0),
            ("Y", "Y", "", "", 1),
            ("Z", "Z", "", "", 2),
            ("VIEW", "View", "", "", 3),
        ],
        default="VIEW",
    )
    panel_constraint: BoolProperty(name="Not Moving this Axis", default=False)
    matrix_basis: FloatVectorProperty(size=(4, 4), subtype="MATRIX")
    move_event_count = None

    @property
    def constraint_axis(self):
        constraint_axis_dict = {
            "X": (True, False, False),
            "Y": (False, True, False),
            "Z": (False, False, True),
            "VIEW": (False, False, False),
        }
        axis_set = constraint_axis_dict[self.axis]
        if self.panel_constraint and axis_set != (True, True, True):
            axis_set = (not axis_set[0], not axis_set[1], not axis_set[2])
        return axis_set

    def get_translate_ops_args(self, context):
        transform_pivot_point = context.scene.tool_settings.transform_pivot_point
        orientation = context.window.scene.transform_orientation_slots[0].type

        trans_args = {
            "mode": "TRANSLATION",
            "release_confirm": True,
            "constraint_axis": self.constraint_axis,
        }

        if transform_pivot_point == "INDIVIDUAL_ORIGINS":
            ...
        else:
            if orientation == "NORMAL":
                if self.axis in ("X", "Y", "Z"):
                    trans_args["orient_axis"] = self.axis
                trans_args["orient_type"] = "NORMAL"
        return trans_args

    def get_orient_matrix(self, context):
        mat = self.matrix_basis.copy().to_3x3()

        if self.axis == "X":
            mat = mat @ Quaternion((0.0, 1.0, 0.0), radians(90)).to_matrix().to_3x3()
        elif self.axis == "Y":
            mat = mat @ Quaternion((1.0, 0.0, 0.0), radians(90)).to_matrix().to_3x3()
        return mat

    def translate(self, context, is_copy=False):
        trans_args = self.get_translate_ops_args(context)

        if is_copy:
            trans_args.pop("mode")
            bpy.ops.object.duplicate_move("INVOKE_DEFAULT",
                                          OBJECT_OT_duplicate={"linked": False if is_copy != "INSTANCE" else True,
                                                               "mode": "TRANSLATION"},
                                          TRANSFORM_OT_translate=trans_args)
        else:
            bpy.ops.transform.transform("INVOKE_DEFAULT", **trans_args)

    def translate_mesh_extrude(self, context):
        orientation = context.window.scene.transform_orientation_slots[0].type
        args = {"constraint_axis": self.constraint_axis, "release_confirm": True}
        if orientation == "NORMAL":
            args["orient_type"] = "NORMAL"
        bpy.ops.mesh.extrude_context_move(
            "INVOKE_DEFAULT",
            MESH_OT_extrude_context={"use_normal_flip": False, "mirror": False},
            TRANSFORM_OT_translate=args,
        )

    def scale(self, context, event):
        if self.axis in ("VIEW",):  # "Z"
            context.window.cursor_warp(event.mouse_x + 200, event.mouse_y + 0)
            bpy.ops.mesh.inset("INVOKE_DEFAULT", release_confirm=True, use_even_offset=True)
        else:
            bpy.ops.mesh.extrude_context("EXEC_DEFAULT")
            bpy.ops.transform.resize("INVOKE_DEFAULT", constraint_axis=self.constraint_axis, release_confirm=True)

    def move(self, context, event):
        if context.mode == "OBJECT":
            # Shift 或 Alt 拖动时复制（复制类型由工具栏的 Duplicate 决定）
            is_copy = context.scene.move_view_tool.duplicate if (event.shift or event.alt) else False
            self.translate(context, is_copy=is_copy)
        elif context.mode == "EDIT_MESH":
            if event.shift:
                self.translate_mesh_extrude(context)
            else:
                self.translate(context, is_copy=False)

    def invoke(self, context, event):
        self.move_event_count = 0
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        pref = get_pref()
        if event.value == "RELEASE" and event.type == "LEFTMOUSE":
            # PASS select operator 选择网格
            bpy.ops.view3d.select("INVOKE_DEFAULT", extend=event.shift, enumerate=event.alt)
            return {"FINISHED"}
        elif event.type == "MOUSEMOVE":
            self.move_event_count += 1
            if self.move_event_count > pref.transform_gizmo_move_event_count:
                if context.mode == "EDIT_MESH" and event.ctrl:
                    self.scale(context, event)
                else:
                    self.move(context, event)
                return {"FINISHED"}
        return {"RUNNING_MODAL"}


class PH_OT_Clear_mesh(bpy.types.Operator):
    bl_idname = "mesh.ph_clear_mesh"
    bl_label = "Clear mesh"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == "EDIT_MESH"

    def execute(self, context):
        import bmesh

        bm = bmesh.from_edit_mesh(context.object.data)
        selected = {f.index for f in bm.faces if f.select}
        bm.free()

        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.intersect(mode='SELECT', separate_mode='CUT', solver='EXACT')

        # bm = bmesh.from_edit_mesh(context.object.data)
        # for f in bm.faces:
        #     f.select = f.index in selected
        # bmesh.update_edit_mesh(context.object.data)
        return {"FINISHED"}


class PH_OT_transform_drag(bpy.types.Operator):
    """Drag an object to move it, or drag on empty space to box select"""
    bl_idname = "object.ph_transform_drag"
    bl_label = "Move / Box Select"
    bl_options = {"REGISTER"}

    duplicate: BoolProperty(name="Duplicate", default=False)

    def invoke(self, context, event):
        obj = _object_under_cursor(context, event)

        # 空白处：框选
        if obj is None:
            try:
                bpy.ops.view3d.select_box("INVOKE_DEFAULT")
            except Exception:
                pass
            return {"FINISHED"}

        # 命中未选中的物体：先把它设为当前选择
        try:
            if not obj.select_get():
                bpy.ops.object.select_all(action="DESELECT")
                obj.select_set(True)
                context.view_layer.objects.active = obj
        except Exception:
            pass

        if self.duplicate:
            linked = context.scene.move_view_tool.duplicate == "INSTANCE"
            try:
                bpy.ops.object.duplicate_move(
                    "INVOKE_DEFAULT",
                    OBJECT_OT_duplicate={"linked": linked},
                    TRANSFORM_OT_translate={"release_confirm": True},
                )
                return {"FINISHED"}
            except Exception:
                pass

        try:
            bpy.ops.transform.translate("INVOKE_DEFAULT", release_confirm=True)
        except Exception:
            pass
        return {"FINISHED"}


class PH_OT_transform_enter_edit(bpy.types.Operator):
    """Double click an object to enter Edit Mode"""
    bl_idname = "object.ph_transform_enter_edit"
    bl_label = "Enter Edit Mode"

    def invoke(self, context, event):
        obj = _object_under_cursor(context, event)
        if obj is None:
            return {"CANCELLED"}
        try:
            if not obj.select_get():
                bpy.ops.object.select_all(action="DESELECT")
                obj.select_set(True)
            context.view_layer.objects.active = obj
        except Exception:
            pass
        if obj.type in C_EDITABLE_TYPES:
            try:
                bpy.ops.object.mode_set(mode="EDIT")
            except Exception:
                return {"FINISHED"}
            # 进入编辑模式后切换到变换加强版（编辑），保证双击退出等手势可用
            try:
                bpy.ops.wm.tool_set_by_id(name="ph.transform_pro_edit")
            except Exception:
                pass
        return {"FINISHED"}


class PH_OT_transform_exit_edit(bpy.types.Operator):
    """Double click empty space to exit Edit Mode"""
    bl_idname = "object.ph_transform_exit_edit"
    bl_label = "Exit Edit Mode"

    def invoke(self, context, event):
        obj = _object_under_cursor(context, event)
        # 空白处：退出到物体模式
        if obj is None:
            try:
                bpy.ops.object.mode_set(mode="OBJECT")
            except Exception:
                return {"FINISHED"}
            # 退回物体模式后切换到变换加强版（物体），保持工具一致
            try:
                bpy.ops.wm.tool_set_by_id(name="ph.transform_pro")
            except Exception:
                pass
            return {"FINISHED"}
        # 命中几何：执行默认选择
        try:
            bpy.ops.view3d.select("INVOKE_DEFAULT")
        except Exception:
            pass
        return {"FINISHED"}


classes = (
    PH_OT_translate,
    PH_OT_Clear_mesh,
    PH_OT_transform_drag,
    PH_OT_transform_enter_edit,
    PH_OT_transform_exit_edit,
)

register, unregister = bpy.utils.register_classes_factory(classes)
