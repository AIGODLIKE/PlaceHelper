import math

import bpy
from mathutils import Vector, Matrix

from ..utils import get_pref
from ..utils.get_gz_matrix import get_matrix, view_matrix
from ..utils.get_gz_position import get_position
from ..utils.gz import GizmoInfo


def get_color(axis):
    ui = bpy.context.preferences.themes[0].user_interface

    axis_x = ui.axis_x[:3]
    axis_y = ui.axis_y[:3]
    axis_z = ui.axis_z[:3]

    if axis == "X":
        color = axis_x
    elif axis == "Y":
        color = axis_y
    else:
        color = axis_z

    return color, color


def get_mx(axis):
    mXW, mYW, mZW, mX_d, mY_d, mZ_d = get_matrix()
    if axis == "X":
        return mXW
    elif axis == "Y":
        return mY_d
    else:
        return mZW


class PH_GZG_transform_pro(bpy.types.GizmoGroup):
    bl_label = "Test Widget"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_options = {"3D", "PERSISTENT"}

    _move_gz = {}
    _move_gz_plane = {}

    @classmethod
    def poll(cls, context):

        obj = context.object
        if not obj:
            return
        elif len(context.selected_objects) == 0:
            return

        elif obj.mode not in {"OBJECT", "EDIT"}:
            return
        elif context.workspace.tools.from_space_view3d_mode(context.mode, create=False).idname not in {
            "ph.transform_pro",
            "ph.transform_pro_edit"
        }:
            return

        return True

    def setup(self, context):
        self._move_gz.clear()
        self._move_gz_plane.clear()

        self.add_move_gz(context, "X")
        self.add_move_gz(context, "Y")
        self.add_move_gz(context, "Z")
        self.add_move_gz(context, "VIEW")

        self.add_move_gz_plane(context, "X")
        self.add_move_gz_plane(context, "Y")
        self.add_move_gz_plane(context, "Z")

    def add_move_gz_plane(self, context, axis):
        pref = get_pref()
        color, color_highlight = get_color(axis)

        gzObject = GizmoInfo(scale_basis=.28,
                             color=color,
                             color_highlight=color_highlight,
                             use_draw_modal=False,
                             use_event_handle_all=False)
        gz = gzObject.set_up(self, "PH_GT_custom_move_plane_3d")
        gz.align_view = True
        prop = gz.target_set_operator("ph.translate", index=0)
        prop.axis = axis
        prop.invert_constraint = True

        mXW, mYW, mZW, mX_d, mY_d, mZ_d = get_matrix()
        off = 0.1
        if axis == "X":
            mx = mXW
            mx_offset = Matrix.Translation(Vector((-off, off, 0.0)))
        elif axis == "Y":
            mx = mYW
            mx_offset = Matrix.Translation(Vector((off, -off, 0.0)))
        else:
            mx = mZW
            mx_offset = Matrix.Translation(Vector((-off, off, 0.0)))

        loc = get_position()
        gz.matrix_basis = mx
        gz.matrix_offset = mx_offset
        gz.alpha = pref.gizmo_alpha

        gz.matrix_basis.translation = loc
        self._move_gz_plane[gz] = axis

    def add_move_gz(self, context, axis):
        color, color_highlight = get_color(axis)
        pref = get_pref()

        if axis == "VIEW":
            color = color_highlight = (.9, .9, .9)

        gzObject = GizmoInfo(scale_basis=pref.transform_gizmo_circle_size if axis == "VIEW" else 1,
                             color=color,
                             color_highlight=color_highlight,
                             use_draw_modal=False,
                             use_event_handle_all=False)

        if axis == "VIEW":
            gz = gzObject.set_up(self, "GIZMO_GT_dial_3d")
            gz.line_width = 2
        else:
            gz = gzObject.set_up(self, "GIZMO_GT_arrow_3d")
            gz.line_width = 2
            gz.length = pref.transform_gizmo_arrow_length

        prop = gz.target_set_operator("ph.translate", index=0)
        prop.invert_constraint = False
        prop.axis = axis

        mXW, mYW, mZW, mX_d, mY_d, mZ_d = get_matrix()
        if axis == "X":
            gz.matrix_basis = mXW
        elif axis == "Y":
            gz.matrix_basis = mY_d
        elif axis == "Z":
            gz.matrix_basis = mZW
        else:
            mXW, mYW, mZW, mX_d, mY_d, mZ_d = view_matrix()
            q = mZW
            gz.matrix_basis = Matrix.LocRotScale(Vector((0, 0, 0)), q, Vector((1, 1, 1)))
        gz.alpha = pref.gizmo_alpha

        self._move_gz[gz] = axis

    def correct_gz_loc(self, context):
        mXW, mYW, mZW, mX_d, mY_d, mZ_d = get_matrix()
        loc = get_position()

        pref = get_pref()

        def get_mx(axis):
            if axis == "X":
                return mXW
            elif axis == "Y":
                return mYW
            else:
                return mZW

        view_vector = context.space_data.region_3d.view_matrix.inverted() @ Vector((0, 0, 1))
        print(f"view = {view_vector.__repr__()}")
        hide_info = {

        }

        alpha_angle = 30
        hide_angle = 15
        for gz, axis in self._move_gz.items():
            if axis == "VIEW":
                res = view_matrix()
                q = res[2]
                gz.matrix_basis = Matrix.LocRotScale(Vector((0, 0, 0)), q, Vector((1, 1, 1)))
            else:
                matrix = get_mx(axis)
                gz.matrix_basis = matrix

                # Offset
                distance = context.space_data.region_3d.view_distance * pref.transform_gizmo_circle_size * pref.transform_gizmo_arrow_offset
                off = Matrix.Translation(Vector((0, 0, distance)))
                if axis == "X":
                    gz.matrix_offset = off
                elif axis == "Y":
                    gz.matrix_offset = off
                elif axis == "Z":
                    gz.matrix_offset = off

                # Angle Alpha
                base_loc = matrix @ Vector()
                view_v = base_loc - view_vector
                view_v.normalize()
                gizmo_vector = gz.matrix_world @ Vector((0, 0, 1))
                gizmo_vector.normalize()
                angle = math.degrees(gizmo_vector.angle(view_v))
                if angle > 90:
                    angle = 180 - angle
                hide_info[axis] = angle

                gz.hide = angle < hide_angle
                if gz.hide is False and alpha_angle > angle:
                    gz.alpha = pref.gizmo_alpha * ((angle - hide_angle) / (alpha_angle - hide_angle))
                else:
                    gz.alpha = pref.gizmo_alpha
            gz.matrix_basis.translation = loc

        alpha_angle = 15
        hide_angle = 10
        for gz, axis in self._move_gz_plane.items():
            gz.matrix_basis = get_mx(axis)
            off = 2
            if axis == "X":
                mx_offset = Matrix.Translation(Vector((-off, off, 0.0)))
            elif axis == "Y":
                mx_offset = Matrix.Translation(Vector((off, -off, 0.0)))
            else:
                mx_offset = Matrix.Translation(Vector((-off, off, 0.0)))

            gz.matrix_offset = mx_offset
            gz.matrix_basis.translation = loc

            angle = 90 - hide_info[axis]

            gz.hide = angle < hide_angle
            if gz.hide is False and alpha_angle > angle:
                gz.alpha = pref.gizmo_alpha * ((angle - hide_angle) / (alpha_angle - hide_angle))
            else:
                gz.alpha = pref.gizmo_alpha

    def draw_prepare(self, context):
        self.refresh(context)

    def refresh(self, context):
        self.correct_gz_loc(context)


classes = (
    PH_GZG_transform_pro,
)

register, unregister = bpy.utils.register_classes_factory(classes)


def update_gzg_pref(self, context):
    try:
        unregister()
    except:
        pass

    register()
