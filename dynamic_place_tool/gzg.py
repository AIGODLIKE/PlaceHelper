import bpy
import math
from mathutils import Vector, Color, Euler, Matrix

from dataclasses import dataclass, field

from ..utils import AlignObject, get_objs_bbox_center, get_objs_bbox_top

from .op import C_OBJECT_TYPE_HAS_BBOX
from ..get_addon_pref import get_addon_pref
from ..transform_tool.get_gz_matrix import get_matrix

GZ_CENTER = Vector((0, 0, 0))

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


class TEST_GGT_test_group3(GZGBase, bpy.types.GizmoGroup):
    bl_label = "Test Widget"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    # 'TOOL_INIT' also sounds appropriate, but then the gizmo doesn't appear!
    bl_options = {'3D'}

    _move_gz = {}
    mode = None

    @classmethod
    def poll(cls, context):
        return context.object and len(context.selected_objects) > 0 and context.object.type == 'MESH'

    def setup(self, context):
        self.gravity_gz = None
        self.mode = None
        self._move_gz.clear()

        self.update_gz_type(context)
        self.correct_gz_loc(context)

    def update_gz_type(self, context):
        if self.mode != context.scene.dynamic_place_tool.mode:
            self.mode = context.scene.dynamic_place_tool.mode

            if context.scene.dynamic_place_tool.mode in {'FORCE', 'DRAG'}:
                if self.gravity_gz:
                    self.gizmos.remove(self.gravity_gz)
                    self.gravity_gz = None

                for gz in self._move_gz.keys():
                    self.gizmos.remove(gz)

                self.add_move_gz(context, 'X')
                self.add_move_gz(context, 'Y')
                self.add_move_gz(context, 'Z')

            elif context.scene.dynamic_place_tool.mode == 'GRAVITY':
                for gz in self._move_gz.keys():
                    self.gizmos.remove(gz)
                self.add_gravity_gz(context)

    def add_gravity_gz(self, context):
        gzObject = GizmoInfo(scale_basis=1,
                             use_draw_modal=False)
        gz = gzObject.set_up(self, 'GIZMO_GT_arrow_3d')
        prop = gz.target_set_operator("test.dynamic_place", index=0)
        prop.axis = 'Z'

        self.gravity_gz = gz

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
                             use_draw_modal=False)

        gz = gzObject.set_up(self, 'GIZMO_GT_arrow_3d')

        if context.scene.dynamic_place_tool.mode == 'DRAG':
            gz.draw_style = 'NORMAL'
        else:
            gz.draw_style = 'BOX'

        prop = gz.target_set_operator("test.dynamic_place", index=0)
        prop.axis = axis

        mXW, mYW, mZW, mX_d, mY_d, mZ_d = get_matrix()
        if axis == 'X':
            gz.matrix_basis = mXW
        elif axis == 'Y':
            gz.matrix_basis = mYW
        elif axis == 'Z':
            gz.matrix_basis = mZW

        self._move_gz[gz] = axis

    def correct_gz_loc(self, context):
        try:
            self.center = get_objs_bbox_center(
                [obj for obj in context.selected_objects if obj.type == 'MESH'])

            global GZ_CENTER
            GZ_CENTER = self.center

        except ZeroDivisionError:
            pass

        mXW, mYW, mZW, mX_d, mY_d, mZ_d = get_matrix()

        for gz, axis in self._move_gz.items():
            if axis == 'X':
                gz.matrix_basis = mXW
            elif axis == 'Y':
                gz.matrix_basis = mYW
            elif axis == 'Z':
                gz.matrix_basis = mZW

            gz.matrix_basis.translation = self.center

        if self.gravity_gz:
            rotate = Euler((math.radians(180), 0, 0), 'XYZ')
            self.gravity_gz.matrix_basis = rotate.to_matrix()
            self.gravity_gz.matrix_basis.translation = self.center

    def refresh(self, context):
        if context.object:
            self.correct_gz_loc(context)
            self.update_gz_type(context)


classes = (
    TEST_GGT_test_group3,
)

register, unregister = bpy.utils.register_classes_factory(classes)


def update_gzg_pref(self, context):
    try:
        unregister()
    except:
        pass

    register()
