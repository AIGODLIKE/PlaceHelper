import bpy
import math
from mathutils import Vector, Color, Euler, Matrix

from dataclasses import dataclass, field

from ..utils import AlignObject, get_objs_bbox_center, get_objs_bbox_top
from .op import C_OBJECT_TYPE_HAS_BBOX

from ._runtime import ALIGN_OBJ, ALIGN_OBJS
from ..get_addon_pref import get_addon_pref


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


class PH_GZG_place_tool(GZGBase, bpy.types.GizmoGroup):
    bl_label = "Test Widget"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    # 'TOOL_INIT' also sounds appropriate, but then the gizmo doesn't appear!
    bl_options = {'3D'}

    def setup(self, context):
        self.add_rotate_gz(context)
        self.add_scale_gz(context)
        self.correct_gz_loc(context)

    def add_rotate_gz(self, context):
        gzObject = GizmoInfo(scale_basis=get_addon_pref().place_tool.gz.scale_basis,
                             color=get_addon_pref().place_tool.gz.color,
                             color_highlight=get_addon_pref().place_tool.gz.color_highlight, )

        self.rotate_gz = gzObject.set_up(self, 'TEST_GT_custom_rotate_z_3d')
        prop = self.rotate_gz.target_set_operator(
            "ph.rotate_object", index=0)
        prop.axis = 'Z'

    def add_scale_gz(self, context):
        gzObject = GizmoInfo(scale_basis=get_addon_pref().place_tool.gz.scale_basis,
                             color=get_addon_pref().place_tool.gz.color,
                             color_highlight=get_addon_pref().place_tool.gz.color_highlight, )
        self.scale_gz = gzObject.set_up(self, 'TEST_GE_custom_scale_3d')
        prop = self.scale_gz.target_set_operator("ph.scale_object", index=0)

    def correct_gz_loc(self, context):
        self.rotate_gz.matrix_basis = context.object.matrix_world.normalized()
        self.scale_gz.matrix_basis = context.object.matrix_world.normalized()

        obj_A = ALIGN_OBJ.get('active')

        if obj_A and len(context.selected_objects) == 1:
            z = Vector((0, 0, 1))
            norm = z
            norm.rotate(context.object.matrix_world.to_euler('XYZ'))

            self.rotate_gz.matrix_basis.translation = obj_A.get_top_center(is_local=False)
            self.scale_gz.matrix_basis.translation = obj_A.get_top_center(is_local=False)

        elif obj_A and len(context.selected_objects) > 1:
            try:
                top = ALIGN_OBJS['top']
                z = get_objs_bbox_top(
                    [obj for obj in context.selected_objects if obj.type == 'MESH'])

                self.rotate_gz.matrix_basis.translation = Vector((top.x, top.y, z))
                self.scale_gz.matrix_basis.translation = Vector((top.x, top.y, z))

                # self.rotate_gz.matrix_basis = Matrix(Vector((top.x, top.y, z)))
                # self.scale_gz.matrix_basis = Matrix(Vector((top.x, top.y, z)))

            except (ZeroDivisionError, AttributeError):
                pass

    def refresh(self, context):
        if context.object:
            self.correct_gz_loc(context)


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
                             use_draw_modal=False)

        gz = gzObject.set_up(self, 'GIZMO_GT_arrow_3d')
        prop = gz.target_set_operator("test.move_view_object", index=0)
        prop.axis = axis

        self._move_gz[gz] = axis

    def correct_gz_loc(self, context):
        for gz, axis in self._move_gz.items():
            if axis == 'X':
                rotate = Euler((math.radians(90), math.radians(
                    180), math.radians(90)), 'XYZ')  # 奇怪的数值

            elif axis == 'Y':
                rotate = Euler((math.radians(-90), 0, 0), 'XYZ')

            else:
                rotate = Euler((0, 0, math.radians(90)), 'XYZ')

            mx = context.object.matrix_world

            # local
            # rotate.rotate(mx.to_euler('XYZ'))
            gz.matrix_basis = rotate.to_matrix().to_4x4()
            gz.matrix_basis.translation = mx.translation

    def refresh(self, context):
        if context.object:
            self.correct_gz_loc(context)


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

            if context.scene.dynamic_place_tool.mode == 'FORCE':
                if self.gravity_gz:
                    self.gizmos.remove(self.gravity_gz)
                    self.gravity_gz = None

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
        gz.draw_style = 'BOX'
        prop = gz.target_set_operator("test.dynamic_place", index=0)
        prop.axis = axis

        self._move_gz[gz] = axis

    def correct_gz_loc(self, context):
        try:
            self.center = get_objs_bbox_center(
                [obj for obj in context.selected_objects if obj.type == 'MESH'])

        except ZeroDivisionError:
            pass

        for gz, axis in self._move_gz.items():
            if axis == 'X':
                rotate = Euler((math.radians(90), math.radians(
                    180), math.radians(90)), 'XYZ')  # 奇怪的数值

            elif axis == 'Y':
                rotate = Euler((math.radians(-90), 0, 0), 'XYZ')

            else:
                rotate = Euler((0, 0, math.radians(90)), 'XYZ')

            mx = context.object.matrix_world

            # local
            # rotate.rotate(mx.to_euler('XYZ'))
            gz.matrix_basis = rotate.to_matrix().to_4x4()
            gz.matrix_basis.translation = self.center

        if self.gravity_gz:
            rotate = Euler((math.radians(180), 0, 0), 'XYZ')
            self.gravity_gz.matrix_basis = rotate.to_matrix().to_4x4()
            self.gravity_gz.matrix_basis.translation = self.center

    def refresh(self, context):
        if context.object:
            self.correct_gz_loc(context)
            self.update_gz_type(context)


classes = (
    PH_GZG_place_tool,
    TEST_GGT_test_group2,
    TEST_GGT_test_group3
)

register, unregister = bpy.utils.register_classes_factory(classes)


def update_gzg_pref(self, context):
    try:
        unregister()
    except:
        pass

    register()
