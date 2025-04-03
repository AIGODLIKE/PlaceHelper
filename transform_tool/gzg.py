import math

import bpy
from bpy_extras.view3d_utils import location_3d_to_region_2d
from mathutils import Vector, Matrix, Euler

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
        return mYW
    else:
        return mZW


class MoveGizmo:
    move_view_gizmo = None
    move_gizmos = {}
    move_plane_gizmos = {}

    def add_move_view_gizmo(self):
        pref = get_pref()
        color = color_highlight = (.9, .9, .9)

        gizmo = GizmoInfo(scale_basis=pref.transform_gizmo_circle_size,
                          color=color,
                          color_highlight=color_highlight,
                          use_draw_modal=False,
                          use_event_handle_all=False).set_up(self, "GIZMO_GT_dial_3d")
        gizmo.line_width = 2
        prop = gizmo.target_set_operator("ph.translate", index=0)
        prop.panel_constraint = False
        prop.axis = "VIEW"
        gizmo.alpha = pref.gizmo_alpha
        self.move_view_gizmo = gizmo

    def add_move_plane_gizmo(self, axis):
        pref = get_pref()
        color, color_highlight = get_color(axis)

        gizmo = GizmoInfo(scale_basis=.28,
                          color=color,
                          color_highlight=color_highlight,
                          use_draw_modal=False,
                          use_event_handle_all=False)
        gz = gizmo.set_up(self, "PH_GT_custom_move_plane_3d")
        gz.align_view = True
        gz.alpha = pref.gizmo_alpha

        prop = gz.target_set_operator("ph.translate", index=0)
        prop.axis = axis
        prop.panel_constraint = True

        self.move_plane_gizmos[axis] = gz

    def add_move_gizmo(self, axis):
        color, color_highlight = get_color(axis)
        pref = get_pref()

        gizmo = GizmoInfo(scale_basis=1,
                          color=color,
                          color_highlight=color_highlight,
                          use_draw_modal=False,
                          use_event_handle_all=False)

        gz = gizmo.set_up(self, "GIZMO_GT_arrow_3d")
        gz.line_width = 2
        gz.length = pref.transform_gizmo_arrow_length
        gz.alpha = pref.gizmo_alpha

        prop = gz.target_set_operator("ph.translate", index=0)
        prop.panel_constraint = False
        prop.axis = axis

        self.move_gizmos[axis] = gz

    def update_gizmos_matrix(self, context):
        loc = get_position()

        pref = get_pref()

        for axis, gz in self.move_gizmos.items():

            matrix = get_mx(axis)
            gz.matrix_basis = matrix

            # Offset
            distance = context.space_data.region_3d.view_distance * pref.transform_gizmo_circle_size * pref.transform_gizmo_arrow_offset
            off = Matrix.Translation(Vector((0, 0, distance)))
            gz.matrix_offset = off

            gz.matrix_basis.translation = loc

        for axis, gz in self.move_plane_gizmos.items():
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

    def update_gizmos_alpha_and_hide(self, context):
        """TODO If the object is too close, it will cause all axes to disappear"""
        orient_slots = context.scene.transform_orientation_slots[0].type
        pref = get_pref()

        if orient_slots == "VIEW":
            for axis, gizmo in self.move_plane_gizmos.items():
                gizmo.hide = axis != "Z"
                gizmo.alpha = pref.gizmo_alpha

            for axis, gizmo in self.move_gizmos.items():
                gizmo.hide = axis == "Z"
                gizmo.alpha = pref.gizmo_alpha
        else:
            region = context.region
            region_3d = context.space_data.region_3d
            view_distance = context.space_data.region_3d.view_distance

            hide_distance = 10
            alpha_distance = 20

            angle = math.radians(90)
            angle_45 = math.radians(45)
            axis_items = {
                "X": Euler((-angle, -angle_45, 0), "YXZ"),
                "Y": Euler((angle, 0, angle_45)),
                "Z": Euler((-angle, 0, angle_45)),
            }
            for axis, gizmo in self.move_plane_gizmos.items():
                matrix = gizmo.matrix_basis
                origin_point = matrix @ Vector()
                rot_matrix = axis_items[axis].to_matrix().to_4x4()
                axis_point = matrix @ (rot_matrix @ Vector((0, 0, view_distance * 0.1)))

                a = location_3d_to_region_2d(region, region_3d, origin_point)
                b = location_3d_to_region_2d(region, region_3d, axis_point)
                distance = (a - b).length

                gizmo.hide = distance < hide_distance
                if distance < alpha_distance:
                    factor = (distance - hide_distance) / hide_distance
                    gizmo.alpha = pref.gizmo_alpha * factor
                else:
                    gizmo.alpha = pref.gizmo_alpha

            for axis, gizmo in self.move_gizmos.items():
                matrix = gizmo.matrix_basis
                origin_point = matrix @ Vector()
                axis_point = matrix @ Vector((0, 0, view_distance * 0.1))

                a = location_3d_to_region_2d(region, region_3d, origin_point)
                b = location_3d_to_region_2d(region, region_3d, axis_point)
                distance = (a - b).length

                gizmo.hide = distance < hide_distance
                if distance < alpha_distance:
                    factor = (distance - hide_distance) / hide_distance
                    gizmo.alpha = pref.gizmo_alpha * factor
                    axis_s = ["X", "Y", "Z"]
                    axis_s.remove(axis)
                    for ax in axis_s:
                        pz = self.move_plane_gizmos[ax]
                        pz.hide = gizmo.hide
                        pz.alpha = gizmo.alpha
                else:
                    gizmo.alpha = pref.gizmo_alpha

    def update_view_move_gizmo_matrix(self, context):
        res = view_matrix(context)
        q = res[2]

        loc = get_position()

        gizmo = self.move_view_gizmo

        gizmo.matrix_basis = Matrix.LocRotScale(Vector((0, 0, 0)), q, Vector((1, 1, 1)))
        gizmo.matrix_basis.translation = loc


class PH_GZG_transform_pro(bpy.types.GizmoGroup, MoveGizmo):
    bl_label = "Transform Pro"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_options = {"3D", "PERSISTENT"}

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
        self.move_gizmos = {}
        self.move_plane_gizmos = {}

        self.add_move_view_gizmo()
        self.add_move_gizmo("X")
        self.add_move_gizmo("Y")
        self.add_move_gizmo("Z")

        self.add_move_plane_gizmo("X")
        self.add_move_plane_gizmo("Y")
        self.add_move_plane_gizmo("Z")

        self.refresh(context)

    def draw_prepare(self, context):
        self.refresh(context)

    def refresh(self, context):
        self.update_gizmos_matrix(context)
        self.update_view_move_gizmo_matrix(context)
        self.update_gizmos_alpha_and_hide(context)


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
