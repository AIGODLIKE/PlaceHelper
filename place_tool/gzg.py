from itertools import product

import bpy
from mathutils import Vector, Matrix

from ._runtime import ALIGN_OBJ, ALIGN_OBJS
from ..utils import get_pref
from ..utils.get_gz_matrix import local_matrix
from ..utils.get_position import get_objs_bbox_top
from ..utils.gz import GizmoInfo, C_OBJECT_TYPE_HAS_BBOX
from ..utils.obj_bbox import AlignObject


class PH_GZG_place_tool(bpy.types.GizmoGroup):
    bl_label = "Place Tool Widget"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_options = {"3D", "PERSISTENT"}

    set_axis_gzs = {}

    @classmethod
    def poll(cls, context):
        obj = context.object
        if not obj:
            return
        elif obj.mode != "OBJECT":
            return
        elif context.workspace.tools.from_space_view3d_mode("OBJECT", create=False).idname != "ph.place_tool":
            return
        elif obj.select_get() and obj.type in C_OBJECT_TYPE_HAS_BBOX:
            return True

    def setup(self, context):
        self.add_rotate_gz(context)
        self.add_scale_gz(context)
        self.correct_gz_loc(context)
        self.add_set_axis_gz(context)

        self.refresh(context)

    def remove_set_axis_gz(self):
        if len(self.set_axis_gzs) == 0:
            return
        for gz in self.set_axis_gzs:
            self.gizmos.remove(gz)
        self.set_axis_gzs.clear()

    def add_set_axis_gz(self, context):
        if len(self.set_axis_gzs) != 0:
            return

        gzObject = GizmoInfo(scale_basis=get_pref().place_tool.gz.scale_basis,
                             color=get_pref().place_tool.bbox.color[:3])

        def add_axis_gz(axis, invert):
            gz = gzObject.set_up(self, "GIZMO_GT_arrow_3d")
            prop = gz.target_set_operator("ph.set_place_axis")
            prop.axis = axis
            prop.invert_axis = invert
            gz.alpha = get_pref().gizmo_alpha
            return gz

        prop = context.scene.place_tool
        exist_axis = prop.axis
        exist_invert = prop.invert_axis

        # not add the axis and invert direction that already exist
        set_axis_gzs = {}
        for axis, invert in product(["X", "Y", "Z"], [False, True]):
            gz = add_axis_gz(axis, invert)
            gz.alpha = get_pref().gizmo_alpha
            gz.color_highlight = gz.color
            if axis == exist_axis and invert == exist_invert:
                gz.color_highlight = gz.color = list(i * 1.3 for i in gz.color)
            set_axis_gzs[(axis, invert)] = gz

        self.set_axis_gzs = set_axis_gzs
        self.update_set_axis_gizmo_matrix(context)

    def add_rotate_gz(self, context):
        color = get_pref().place_tool.gz.color
        gzObject = GizmoInfo(scale_basis=get_pref().place_tool.gz.scale_basis,
                             color=color,
                             color_highlight=color, )

        self.rotate_gz = gzObject.set_up(self, "PH_GT_custom_rotate_z_3d")
        self.rotate_gz.alpha = get_pref().gizmo_alpha
        prop = self.rotate_gz.target_set_operator(
            "ph.rotate_object", index=0)
        prop.axis = "Z"

    def add_scale_gz(self, context):
        color = get_pref().place_tool.gz.color
        gzObject = GizmoInfo(scale_basis=get_pref().place_tool.gz.scale_basis,
                             color=color,
                             color_highlight=color, )
        self.scale_gz = gzObject.set_up(self, "PH_GT_custom_scale_3d")
        self.scale_gz.alpha = get_pref().gizmo_alpha
        prop = self.scale_gz.target_set_operator("ph.scale_object", index=0)

    def correct_gz_loc(self, context):
        self.rotate_gz.matrix_basis = context.object.matrix_world.normalized()
        self.scale_gz.matrix_basis = context.object.matrix_world.normalized()

        obj_A = ALIGN_OBJ.get("active")

        if obj_A and len(context.selected_objects) == 1:
            try:
                x, y, z, xD, yD, zD = local_matrix(reverse_zD=True)
                axis = context.scene.place_tool.axis
                invert = context.scene.place_tool.invert_axis
                if axis == "X":
                    q = x if not invert else xD
                elif axis == "Y":
                    q = y if not invert else yD
                elif axis == "Z":
                    q = z if not invert else zD

                pos = obj_A.get_axis_center(axis, not invert, is_local=False)
                scale = Vector((1, 1, 1))
                mx = Matrix.LocRotScale(pos, q, scale)

                self.rotate_gz.matrix_basis = mx
                self.scale_gz.matrix_basis = mx
            except ReferenceError as e:
                print(e.args)
                pass

        elif obj_A and len(context.selected_objects) > 1:
            try:
                top = ALIGN_OBJS["top"]
                z = get_objs_bbox_top(
                    [obj for obj in context.selected_objects if obj.type in {"MESH", "LIGHT"}])

                # 统一gizmo朝上
                self.rotate_gz.matrix_basis = Matrix()
                self.scale_gz.matrix_basis = Matrix()

                self.rotate_gz.matrix_basis.translation = Vector((top.x, top.y, z))
                self.scale_gz.matrix_basis.translation = Vector((top.x, top.y, z))
            except (ZeroDivisionError, AttributeError):
                pass

        elif not obj_A or obj_A.obj != context.object:
            if context.object.type in {"MESH", "CURVE", "SURFACE", "FONT", "LIGHT"}:
                ALIGN_OBJ["active"] = AlignObject(context.object,
                                                  "ACCURATE", True)

    def refresh(self, context):
        prop = context.scene.place_tool

        for gz in self.set_axis_gzs.values():
            gz.hide = not prop.setting_axis
        self.update_set_axis_gizmo_matrix(context)

        self.scale_gz.hide = prop.setting_axis
        self.rotate_gz.hide = prop.setting_axis or [obj.type for obj in context.selected_objects] == ["LIGHT", ]

        if context.object:
            self.correct_gz_loc(context)

    def draw_prepare(self, context):
        self.refresh(context)

    def invoke_prepare(self, context, gizmo):
        self.refresh(context)

    def update_set_axis_gizmo_matrix(self, context):
        obj_A = ALIGN_OBJ.get("active")
        if obj_A:
            try:
                pos = obj_A.get_bbox_center(is_local=False)
            except ReferenceError:
                # undo self.obj been removed
                return
        else:
            pos = context.object.matrix_world.translation

        x, y, z, xD, yD, zD = local_matrix(reverse_zD=True)

        for (axis, invert), gz in self.set_axis_gzs.items():
            if axis == "X":
                q = x if not invert else xD
            elif axis == "Y":
                q = y if not invert else yD
            elif axis == "Z":
                q = z if not invert else zD

            scale = Vector((2, 2, 2))

            mx = Matrix.LocRotScale(pos, q, scale)
            gz.matrix_basis = mx


classes = (
    PH_GZG_place_tool,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)


def update_gzg_pref(self, context):
    unregister()
    register()
