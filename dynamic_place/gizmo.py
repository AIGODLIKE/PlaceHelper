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


class CreateGizmo:
    view_move = None
    gizmo_move_list = None
    gizmo_scale_list = None

    def new_gizmo(self, axis: str, gizmo_type="GIZMO_GT_arrow_3d"):
        pref = get_pref()
        color, color_highlight = get_color(axis)

        gizmo = self.gizmos.new(gizmo_type)

        gizmo.color = color
        gizmo.color_highlight = color_highlight
        gizmo.alpha = pref.gizmo_alpha
        gizmo.alpha_highlight = pref.gizmo_alpha_highlight
        return gizmo

    def gizmo_move(self, context):
        from .ops import DynamicMove, DynamicScale
        pref = get_pref()

        self.gizmo_move_list = []
        self.gizmo_scale_list = []
        for index, (axis, rotate) in enumerate(axis_items.items()):
            # 移动
            gizmo = self.new_gizmo(axis)
            gizmo.transform = {"CONSTRAIN"}
            gizmo.draw_style = "NORMAL"
            gizmo.length = 0
            ops = gizmo.target_set_operator(DynamicMove.bl_idname)
            ops.axis = axis
            self.gizmo_move_list.append(gizmo)

            # 缩放
            gizmo = self.new_gizmo(axis)
            gizmo.transform = {"CONSTRAIN"}
            gizmo.draw_style = "BOX"
            gizmo.length = .5
            ops = gizmo.target_set_operator(DynamicScale.bl_idname)
            ops.axis = axis
            self.gizmo_scale_list.append(gizmo)

            # # 旋转
            # gizmo = self.new_gizmo(axis, matrix)
            # gizmo.transform = {"CONSTRAIN"}
            # gizmo.draw_style = "BOX"
            # gizmo.length = .5
            # ops = gizmo.target_set_operator(DynamicRotate.bl_idname)
            # ops.axis = axis


    def gizmo_rotate(self, context):
        ...

    def gizmo_scale(self, context):
        ...

    def create_gizmos(self, context):
        self.gizmo_move(context)
        self.gizmo_rotate(context)
        self.gizmo_scale(context)

        gizmo = self.gizmos.new("GIZMO_GT_dial_3d")
        # gizmo.draw_options = {"CLIP"}
        # gizmo.color = color
        # gizmo.color_highlight = color_highlight
        gizmo.alpha = pref.gizmo_alpha
        gizmo.alpha_highlight = pref.gizmo_alpha_highlight
        gizmo.line_width = 2
        gizmo.scale_basis = pref.transform_gizmo_circle_size

        ops = gizmo.target_set_operator(DynamicMove.bl_idname)
        ops.axis = "VIEW"

        self.view_move = gizmo

    def update_gizmos_matrix(self, context):
        q = view_matrix(context)[2]
        self.view_move.matrix_basis = Matrix.LocRotScale(Vector((0, 0, 0)), q, Vector((1, 1, 1)))

        loc = get_selected_objects_center_translation(context)
        for gizmo in self.gizmos:
            gizmo.matrix_basis.translation = loc

        # pref = get_pref()
        # view_distance = context.space_data.region_3d.view_distance
        # distance = view_distance * pref.transform_gizmo_circle_size * pref.transform_gizmo_arrow_offset
        #
        # def get_offset(axis_index, offset, rot) -> Matrix:
        #     off = Vector()
        #     off[axis_index] = distance + offset
        #     offset_matrix = Matrix.Translation(off)
        #     rotate_matrix = rot.to_matrix().to_4x4()
        #     matrix = offset_matrix @ rotate_matrix
        #     return matrix
        #
        # get_offset(index, 2.2, rotate)


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
