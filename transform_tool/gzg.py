import bpy
import math
from mathutils import Vector, Color, Euler, Matrix

from dataclasses import dataclass, field

from .op import C_OBJECT_TYPE_HAS_BBOX
from ..get_addon_pref import get_addon_pref
from .get_gz_matrix import get_matrix
from .get_gz_position import get_position


@dataclass
class GizmoInfo:
    # color
    alpha: float = 0.9
    color: Color = (0.48, 0.4, 1)
    alpha_highlight: float = 1
    color_highlight: Color = (1.0, 1.0, 1.0)

    # settings
    use_draw_modal: bool = True
    use_event_handle_all: bool = True
    scale_basis: float = 1
    use_tooltip: bool = True

    def set_up(self, gzg, type):
        self.gz = gzg.gizmos.new(type)
        for key in self.__annotations__.keys():
            self.gz.__setattr__(key, self.__getattribute__(key))

        return self.gz


class GZGBase():
    @classmethod
    def poll(cls, context):
        obj = context.object
        if not obj:
            return
        elif obj.mode != 'OBJECT':
            return
        elif context.workspace.tools.from_space_view3d_mode('OBJECT', create=False).idname != 'ph.place_tool':
            return
        elif obj.select_get() and obj.type in C_OBJECT_TYPE_HAS_BBOX:
            return True


class TEST_GGT_test_group2(GZGBase, bpy.types.GizmoGroup):
    bl_label = "Test Widget"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    # 'TOOL_INIT' also sounds appropriate, but then the gizmo doesn't appear!
    bl_options = {'3D'}

    _move_gz = {}

    @classmethod
    def poll(cls, context):
        return context.object and len(context.selected_objects) > 0

    def setup(self, context):
        self._move_gz.clear()

        self.add_move_gz(context, 'X')
        self.add_move_gz(context, 'Y')
        self.add_move_gz(context, 'Z')

    def add_move_gz(self, context, axis):
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

        gzObject = GizmoInfo(scale_basis=1,
                             color=color,
                             color_highlight=color_highlight,
                             use_draw_modal=False,
                             use_event_handle_all=False)

        gz = gzObject.set_up(self, 'GIZMO_GT_arrow_3d')
        prop = gz.target_set_operator("ph.translate", index=0)
        prop.axis = axis

        mXW, mYW, mZW, mX_d, mY_d, mZ_d = get_matrix()

        if axis == 'X':
            gz.matrix_basis = mXW
        elif axis == 'Y':
            gz.matrix_basis = mYW
        else:
            gz.matrix_basis = mZW

        loc = get_position()
        gz.matrix_basis.translation = loc

        self._move_gz[gz] = axis

    def correct_gz_loc(self, context):
        mXW, mYW, mZW, mX_d, mY_d, mZ_d = get_matrix()

        loc = get_position()

        for gz, axis in self._move_gz.items():
            if axis == 'X':
                gz.matrix_basis = mXW
            elif axis == 'Y':
                gz.matrix_basis = mYW
            else:
                gz.matrix_basis = mZW

            gz.matrix_basis.translation = loc

    def refresh(self, context):
        self.correct_gz_loc(context)


classes = (
    TEST_GGT_test_group2,
)

register, unregister = bpy.utils.register_classes_factory(classes)


def update_gzg_pref(self, context):
    try:
        unregister()
    except:
        pass

    register()
