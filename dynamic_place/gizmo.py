import math

import bpy
from mathutils import Vector, Matrix, Euler

from ..utils import get_pref, get_color, get_selected_objects_center_translation

angle = math.radians(90)
axis_items = {
    "X": Euler((0, angle, 0)),
    "Y": Euler((-angle, 0, 0)),
    "Z": Euler((0, 0, angle)),
}


class CreateGizmo:

    def gizmo_move(self, context):
        from .ops import DynamicMove
        pref = get_pref()
        distance = context.space_data.region_3d.view_distance * pref.transform_gizmo_circle_size * pref.transform_gizmo_arrow_offset
        for index, (axis, rotate) in enumerate(axis_items.items()):
            color, color_highlight = get_color(axis)

            off = Vector()
            off[index] = distance
            offset_matrix = Matrix.Translation(off)
            rotate_matrix = rotate.to_matrix().to_4x4()

            gizmo = self.gizmos.new("GIZMO_GT_arrow_3d")
            gizmo.matrix_offset = offset_matrix @ rotate_matrix
            gizmo.transform = {"CONSTRAIN"}

            gizmo.length = .5
            gizmo.draw_style = "BOX"
            gizmo.color = color
            gizmo.color_highlight = color_highlight
            gizmo.alpha = pref.gizmo_alpha
            gizmo.alpha_highlight = 0.5

            ops = gizmo.target_set_operator(DynamicMove.bl_idname)
            ops.axis = axis

    def gizmo_rotate(self, context):
        ...

    def gizmo_scale(self, context):
        ...

    def create_gizmos(self, context):
        self.gizmo_move(context)
        self.gizmo_rotate(context)
        self.gizmo_scale(context)

    def update_gizmos_matrix(self, context):

        loc = get_selected_objects_center_translation(context)
        for gizmo in self.gizmos:
            gizmo.matrix_basis.translation = loc


class PH_GZG_Dynamic_Place(bpy.types.GizmoGroup, CreateGizmo):
    bl_label = "Dynamic Place"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D'}

    @classmethod
    def poll(cls, context):
        if context.mode != 'OBJECT':
            return
        elif context.object is None:
            return
        elif len(context.selected_objects) == 0:
            return

        elif context.workspace.tools.from_space_view3d_mode('OBJECT', create=False).idname != 'ph.dynamic_place':
            return

        return context.object.type == 'MESH'

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
