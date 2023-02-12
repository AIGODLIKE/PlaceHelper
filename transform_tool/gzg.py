import bpy

from mathutils import Vector, Matrix, Quaternion, Euler
from .op import C_OBJECT_TYPE_HAS_BBOX

from ..util.gz import GizmoInfo
from ..util.get_gz_matrix import get_matrix, view_matrix
from ..util.get_gz_position import get_position


def get_color(axis):
    ui = bpy.context.preferences.themes[0].user_interface

    axis_x = ui.axis_x[:3]
    axis_y = ui.axis_y[:3]
    axis_z = ui.axis_z[:3]
    color_highlight = (1, 1, 1)

    if axis == 'X':
        color = axis_x
    elif axis == 'Y':
        color = axis_y
    else:
        color = axis_z

    return color, color_highlight


def get_mx(axis):
    mXW, mYW, mZW, mX_d, mY_d, mZ_d = get_matrix()
    if axis == 'X':
        return mXW
    elif axis == 'Y':
        return mY_d
    else:
        return mZW


class PH_GZG_transform_pro(bpy.types.GizmoGroup):
    bl_label = "Test Widget"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D'}

    _move_gz = {}
    _move_gz_plane = {}

    @classmethod
    def poll(cls, context):

        obj = context.object
        if not obj:
            return
        elif len(context.selected_objects) == 0:
            return

        elif obj.mode not in {'OBJECT', 'EDIT'}:
            return
        elif context.workspace.tools.from_space_view3d_mode(context.mode, create=False).idname not in {
            'ph.transform_pro',
            'ph.transform_pro_edit'
        }:
            return

        return True

    def setup(self, context):
        self._move_gz.clear()
        self._move_gz_plane.clear()

        self.add_move_gz(context, 'X')
        self.add_move_gz(context, 'Y')
        self.add_move_gz(context, 'Z')
        self.add_move_gz(context, 'VIEW')

        self.add_move_gz_plane(context, 'X')
        self.add_move_gz_plane(context, 'Y')
        self.add_move_gz_plane(context, 'Z')

    def add_move_gz_plane(self, context, axis):
        color, color_highlight = get_color(axis)

        gzObject = GizmoInfo(scale_basis=0.4,
                             color=color,
                             color_highlight=color_highlight,
                             use_draw_modal=False,
                             use_event_handle_all=False)
        gz = gzObject.set_up(self, 'PH_GT_custom_move_plane_3d')
        gz.align_view = True
        prop = gz.target_set_operator("ph.translate", index=0)
        prop.axis = axis
        prop.invert_constraint = True

        mXW, mYW, mZW, mX_d, mY_d, mZ_d = get_matrix()
        off = 2
        if axis == 'X':
            mx = mXW
            mx_offset = Matrix.Translation(Vector((-off, off, 0.0)))
        elif axis == 'Y':
            mx = mYW
            mx_offset = Matrix.Translation(Vector((off, -off, 0.0)))
        else:
            mx = mZW
            mx_offset = Matrix.Translation(Vector((-off, off, 0.0)))

        loc = get_position()
        gz.matrix_basis = mx
        gz.matrix_offset = mx_offset

        gz.matrix_basis.translation = loc
        self._move_gz_plane[gz] = axis

    def add_move_gz(self, context, axis):
        color, color_highlight = get_color(axis)

        if axis == 'VIEW':
            color = (0.8, 0.8, 0.8)

        gzObject = GizmoInfo(scale_basis=1 if axis != 'VIEW' else 0.3,
                             color=color,
                             color_highlight=color_highlight,
                             use_draw_modal=False,
                             use_event_handle_all=False)

        if axis == 'VIEW':
            gz = gzObject.set_up(self, 'GIZMO_GT_dial_3d')
            gz.line_width = 3
        else:
            gz = gzObject.set_up(self, 'GIZMO_GT_arrow_3d')

        prop = gz.target_set_operator("ph.translate", index=0)
        prop.invert_constraint = False
        prop.axis = axis

        mXW, mYW, mZW, mX_d, mY_d, mZ_d = get_matrix()
        if axis == 'X':
            gz.matrix_basis = mXW
        elif axis == 'Y':
            gz.matrix_basis = mY_d
        elif axis == 'Z':
            gz.matrix_basis = mZW
        else:
            mXW, mYW, mZW, mX_d, mY_d, mZ_d = view_matrix()
            q = mZW
            gz.matrix_basis = Matrix.LocRotScale(Vector((0, 0, 0)), q, Vector((1, 1, 1)))

        loc = get_position()
        gz.matrix_basis.translation = loc

        self._move_gz[gz] = axis

    def correct_gz_loc(self, context):
        mXW, mYW, mZW, mX_d, mY_d, mZ_d = get_matrix()
        loc = get_position()

        def get_mx(axis):
            if axis == 'X':
                return mXW
            elif axis == 'Y':
                return mYW
            else:
                return mZW

        for gz, axis in self._move_gz.items():
            if axis == 'VIEW':
                res = view_matrix()
                q = res[2]
                gz.matrix_basis = Matrix.LocRotScale(Vector((0, 0, 0)), q, Vector((1, 1, 1)))
            else:
                gz.matrix_basis = get_mx(axis)
            gz.matrix_basis.translation = loc

        for gz, axis in self._move_gz_plane.items():
            gz.matrix_basis = get_mx(axis)
            off = 2
            if axis == 'X':
                mx_offset = Matrix.Translation(Vector((-off, off, 0.0)))
            elif axis == 'Y':
                mx_offset = Matrix.Translation(Vector((off, -off, 0.0)))
            else:
                mx_offset = Matrix.Translation(Vector((-off, off, 0.0)))

            gz.matrix_offset = mx_offset
            gz.matrix_basis.translation = loc

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
