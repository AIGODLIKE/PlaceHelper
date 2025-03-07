from itertools import product

import bpy
from mathutils import Vector, Matrix

from ..utils.get_gz_matrix import get_matrix, view_matrix
from ..utils.get_position import get_objs_bbox_center
from ..utils.gz import GizmoInfo
from ..utils import get_pref

GZ_CENTER = Vector((0, 0, 0))
C_OBJECT_TYPE_HAS_BBOX = {'MESH', 'CURVE', 'FONT', 'LATTICE'}


class PH_GZG_dynamic_place(bpy.types.GizmoGroup):
    bl_label = "Dynamic Place Widget"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D'}

    _move_gz = {}
    mode = None
    location = None

    @classmethod
    def poll(cls, context):
        if context.mode != 'OBJECT':
            return
        elif context.object is None:
            return
        elif len(context.selected_objects) == 0:
            return

        elif context.workspace.tools.from_space_view3d_mode('OBJECT', create=False).idname != 'ph.dynamic_place_tool':
            return

        return context.object.type == 'MESH'

    def setup(self, context):
        self.cursor_gz = None
        self.mode = None
        self._move_gz.clear()

        self.update_gz_type(context)
        self.correct_gz_loc(context)

    def update_gz_type(self, context):
        if self.mode == context.scene.dynamic_place_tool.mode: return
        if self.location == context.scene.dynamic_place_tool.location: return

        self.mode = context.scene.dynamic_place_tool.mode

        if context.scene.dynamic_place_tool.mode == 'DRAG':
            # remove all gizmos
            for gz in self._move_gz.keys():
                self.gizmos.remove(gz)
            self._move_gz.clear()

            if self.cursor_gz:
                self.gizmos.remove(self.cursor_gz)
            self.cursor_gz = None

            if context.scene.dynamic_place_tool.location == 'CURSOR':
                self.add_cursor_gz(context)
            else:
                # add normal gizmos
                for axis, invert in product(['X', 'Y', 'Z'], [False, True]):
                    self.add_move_gz(context, axis, invert)

        elif context.scene.dynamic_place_tool.mode == 'FORCE':
            for gz in self._move_gz.keys():
                self.gizmos.remove(gz)
            self._move_gz.clear()
            if context.scene.dynamic_place_tool.location == 'CURSOR':
                self.add_cursor_gz(context)
            else:
                # add normal gizmos
                for axis, invert in product(['X', 'Y', 'Z'], [False, True]):
                    if context.scene.dynamic_place_tool.mode == 'FORCE' and invert: continue  # no negative force
                    self.add_move_gz(context, axis, invert)

                self.add_move_gz(context, 'VIEW', True)

    def add_cursor_gz(self, context):
        gzObject = GizmoInfo(scale_basis=1,
                             use_draw_modal=False)
        gz = gzObject.set_up(self, 'GIZMO_GT_arrow_3d')
        prop = gz.target_set_operator("ph.gravity_place", index=0)
        prop.axis = 'Z'

        gz.alpha = get_pref().gizmo_alpha
        self.cursor_gz = gz

    def add_move_gz(self, context, axis, invert_axis=False):
        ui = bpy.context.preferences.themes[0].user_interface

        axis_x = ui.axis_x[:3]
        axis_y = ui.axis_y[:3]
        axis_z = ui.axis_z[:3]

        if axis == 'X':
            color = axis_x
        elif axis == 'Y':
            color = axis_y
        elif axis == 'Z':
            color = axis_z
        else:
            color = (0.8, 0.8, 0.8)

        gzObject = GizmoInfo(scale_basis=1 if axis != 'VIEW' else 0.3,
                             color=color,
                             color_highlight=color,
                             use_draw_modal=False)

        if context.scene.dynamic_place_tool.mode == 'FORCE':
            if axis == 'VIEW':
                gz = gzObject.set_up(self, 'GIZMO_GT_dial_3d')
                gz.line_width = 3
            else:
                gz = gzObject.set_up(self, 'GIZMO_GT_arrow_3d')
                gz.draw_style = 'BOX'
        else:
            gz = gzObject.set_up(self, 'GIZMO_GT_arrow_3d')
            gz.draw_style = 'NORMAL'

        gz.alpha = get_pref().gizmo_alpha

        op = 'ph.scale_force' if context.scene.dynamic_place_tool.mode == 'FORCE' else 'ph.gravity_place'
        prop = gz.target_set_operator(op, index=0)
        prop.axis = axis
        prop.invert_axis = invert_axis

        mXW, mYW, mZW, mX_d, mY_d, mZ_d = get_matrix(reverse_zD=True)
        if axis == 'X':
            gz.matrix_basis = mXW if not invert_axis else mX_d
        elif axis == 'Y':
            gz.matrix_basis = mYW if not invert_axis else mY_d
        elif axis == 'Z':
            gz.matrix_basis = mZW if not invert_axis else mZ_d
        else:
            mXW, mYW, mZW, mX_d, mY_d, mZ_d = view_matrix()
            q = mZW
            gz.matrix_basis = Matrix.LocRotScale(Vector((0, 0, 0)), q, Vector((1, 1, 1)))
        self._move_gz[gz] = (axis, invert_axis)

    def correct_gz_loc(self, context):
        try:
            self.center = get_objs_bbox_center(
                [obj for obj in context.selected_objects if obj.type == 'MESH'])

            global GZ_CENTER
            GZ_CENTER = self.center

        except ZeroDivisionError:
            pass

        mXW, mYW, mZW, mX_d, mY_d, mZ_d = get_matrix(reverse_zD=True)

        for gz, (axis, invert_axis) in self._move_gz.items():
            if axis == 'X':
                gz.matrix_basis = mXW if not invert_axis else mX_d
            elif axis == 'Y':
                gz.matrix_basis = mYW if not invert_axis else mY_d
            elif axis == 'Z':
                gz.matrix_basis = mZW if not invert_axis else mZ_d
            else:
                mXW, mYW, mZW, mX_d, mY_d, mZ_d = view_matrix()
                q = mZW
                gz.matrix_basis = Matrix.LocRotScale(Vector((0, 0, 0)), q, Vector((1, 1, 1)))
            gz.alpha = get_pref().gizmo_alpha
            gz.matrix_basis.translation = self.center

        if self.cursor_gz:
            end = context.scene.cursor.location
            vec = end - self.center

            mx = Matrix.LocRotScale(self.center, Vector((0, 0, 1)).rotation_difference(vec), Vector((1, 1, 1)))
            self.cursor_gz.matrix_basis = mx
            self.cursor_gz.alpha = get_pref().gizmo_alpha

    def refresh(self, context):
        if context.object:
            self.correct_gz_loc(context)
            self.update_gz_type(context)

    def draw_prepare(self, context):
        self.refresh(context)


classes = (
    PH_GZG_dynamic_place,
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
    bpy.ops.wm.tool_set_by_id(name="ph.dynamic_place_tool")
