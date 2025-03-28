import math

import bpy
from mathutils import Vector, Matrix, Euler

from ..utils import get_pref, get_color, get_selected_objects_center_translation
from ..utils.get_gz_matrix import view_matrix

angle = math.radians(90)
axis_items = {
    "X": Euler((0, angle, 0)),
    "Y": Euler((-angle, 0, 0)),
    "Z": Euler((0, 0, angle)),
}


def get_offset(axis_index, offset, rot) -> Matrix:
    off = Vector()
    off[axis_index] = offset
    offset_matrix = Matrix.Translation(off)
    rotate_matrix = rot.to_matrix().to_4x4()
    matrix = offset_matrix @ rotate_matrix
    return matrix


class CreateGizmo:
    gizmo_view_move = None
    gizmo_view_rotate = None
    gizmo_view_rotate_gimbal = None

    gizmo_move_list = None
    gizmo_scale_list = None
    gizmo_rotate_list = None

    def new_gizmo(self, axis: str, gizmo_type="GIZMO_GT_arrow_3d"):
        pref = get_pref()
        color, color_highlight = get_color(axis)

        gizmo = self.gizmos.new(gizmo_type)

        gizmo.color = color
        gizmo.color_highlight = color_highlight
        gizmo.alpha = pref.gizmo_alpha
        gizmo.alpha_highlight = pref.gizmo_alpha_highlight
        return gizmo

    def create_view_move_gizmo(self):
        from .ops import DynamicMove

        pref = get_pref()

        gizmo = self.gizmos.new("GIZMO_GT_dial_3d")
        gizmo.draw_options = {"FILL_SELECT"}
        # gizmo.color = color
        # gizmo.color_highlight = color_highlight
        gizmo.alpha = pref.gizmo_alpha
        gizmo.alpha_highlight = pref.gizmo_alpha_highlight
        gizmo.line_width = 2
        gizmo.scale_basis = pref.transform_gizmo_circle_size

        ops = gizmo.target_set_operator(DynamicMove.bl_idname)
        ops.axis = "VIEW"

        self.gizmo_view_move = gizmo

    def create_view_rotate_gizmo(self):
        from .ops import DynamicRotate

        pref = get_pref()

        gizmo = self.gizmos.new("GIZMO_GT_dial_3d")
        # gizmo.draw_options = {"CLIP"}
        gizmo.alpha = pref.gizmo_alpha
        gizmo.alpha_highlight = pref.gizmo_alpha_highlight
        gizmo.line_width = 2
        gizmo.scale_basis = 1.2

        ops = gizmo.target_set_operator(DynamicRotate.bl_idname)
        ops.axis = "VIEW"

        self.gizmo_view_rotate = gizmo

        # gizmo = self.gizmos.new("GIZMO_GT_dial_3d")
        # gizmo.draw_options = {
        #     "ANGLE_START_Y",
        #     # "FILL",
        #     # "FILL_SELECT"
        # }
        # gizmo.alpha = pref.gizmo_alpha
        # gizmo.alpha_highlight = pref.gizmo_alpha_highlight
        # gizmo.line_width = 2
        # gizmo.scale_basis = 0.5
        #
        # ops = gizmo.target_set_operator(DynamicRotate.bl_idname)
        # ops.axis = "VIEW"
        #
        # self.gizmo_view_rotate_gimbal = gizmo

    def create_gizmos(self, context):
        from .ops import DynamicMove, DynamicScale, DynamicRotate
        self.gizmo_move_list = {}
        self.gizmo_scale_list = {}
        self.gizmo_rotate_list = {}
        for index, (axis, rotate) in enumerate(axis_items.items()):
            key = index, axis, rotate.freeze()

            # 移动
            gizmo = self.new_gizmo(axis)
            gizmo.transform = {"CONSTRAIN"}
            gizmo.draw_style = "NORMAL"
            gizmo.length = 0
            ops = gizmo.target_set_operator(DynamicMove.bl_idname)
            ops.axis = axis
            self.gizmo_move_list[key] = gizmo

            # 缩放
            gizmo = self.new_gizmo(axis)
            gizmo.transform = {"CONSTRAIN"}
            gizmo.draw_style = "BOX"
            gizmo.length = .3
            gizmo.line_width = 2
            ops = gizmo.target_set_operator(DynamicScale.bl_idname)
            ops.axis = axis
            self.gizmo_scale_list[key] = gizmo

            # 旋转
            gizmo = self.new_gizmo(axis, gizmo_type="GIZMO_GT_dial_3d")
            gizmo.draw_options = {"CLIP"}
            # gizmo.transform = {"CONSTRAIN"}
            # gizmo.draw_style = "BOX"
            # gizmo.length = .5
            ops = gizmo.target_set_operator(DynamicRotate.bl_idname)
            gizmo.line_width = 3
            ops.axis = axis
            self.gizmo_rotate_list[key] = gizmo

        self.create_view_move_gizmo()
        self.create_view_rotate_gizmo()

    def update_gizmos_matrix(self, context):
        self.update_gizmos_offset_matrix(context)

        q = view_matrix(context)[2]
        view = Matrix.LocRotScale(Vector((0, 0, 0)), q, Vector((1, 1, 1)))
        self.gizmo_view_move.matrix_basis = view
        self.gizmo_view_rotate.matrix_basis = view
        # self.gizmo_view_rotate_gimbal.matrix_basis = view

        loc = get_selected_objects_center_translation(context)
        for gizmo in self.gizmos:
            gizmo.matrix_basis.translation = loc

    def update_gizmos_offset_matrix(self, context):
        view_distance = context.space_data.region_3d.view_distance * .089
        for (index, axis, rotate), gizmo in self.gizmo_move_list.items():
            matrix = get_offset(index, view_distance, rotate)
            gizmo.matrix_offset = matrix
        for (index, axis, rotate), gizmo in self.gizmo_scale_list.items():
            matrix = get_offset(index, view_distance * 0.2, rotate)
            gizmo.matrix_offset = matrix
        for (index, axis, rotate), gizmo in self.gizmo_rotate_list.items():
            matrix = get_offset(index, 0, rotate)
            gizmo.matrix_offset = matrix


class PH_GZG_Dynamic_Place(bpy.types.GizmoGroup, CreateGizmo):
    bl_label = "Dynamic Place"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D'}

    @classmethod
    def poll(cls, context):
        if context.mode != 'OBJECT':
            return
        elif len(context.selected_objects) == 0:
            return

        elif context.workspace.tools.from_space_view3d_mode('OBJECT', create=False).idname != 'ph.dynamic_place':
            return

        return True

    def setup(self, context):
        self.create_gizmos(context)
        self.update_gizmos_matrix(context)

    def refresh(self, context):
        if context.object:
            self.update_gizmos_matrix(context)

    def draw_prepare(self, context):
        self.refresh(context)


def register():
    bpy.utils.register_class(PH_GZG_Dynamic_Place)


def unregister():
    bpy.utils.unregister_class(PH_GZG_Dynamic_Place)
