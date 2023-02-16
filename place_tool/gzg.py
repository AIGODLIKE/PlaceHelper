import bpy
import math
from mathutils import Vector, Color, Euler, Matrix

from ..util.gz import GizmoInfo, C_OBJECT_TYPE_HAS_BBOX
from ..util.get_position import get_objs_bbox_center, get_objs_bbox_top
from ..util.get_gz_matrix import local_matrix

from ._runtime import ALIGN_OBJ, ALIGN_OBJS
from ..get_addon_pref import get_addon_pref

from itertools import product


class PH_GZG_place_tool(bpy.types.GizmoGroup):
    bl_label = "Test Widget"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D'}

    set_axis_gzs = []

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

    def setup(self, context):
        self.add_rotate_gz(context)
        self.add_scale_gz(context)
        self.correct_gz_loc(context)

    def remove_set_axis_gz(self):
        if len(self.set_axis_gzs) == 0:
            return
        for gz in self.set_axis_gzs:
            self.gizmos.remove(gz)
        self.set_axis_gzs.clear()

    def add_set_axis_gz(self, context):
        if len(self.set_axis_gzs) != 0: return

        gzObject = GizmoInfo(scale_basis=get_addon_pref().place_tool.gz.scale_basis,
                             color=get_addon_pref().place_tool.bbox.color[:3])

        x, y, z, xD, yD, zD = local_matrix(reverse_zD=True)

        def add_axis_gz(axis, invert):
            gz = gzObject.set_up(self, 'GIZMO_GT_arrow_3d')
            prop = gz.target_set_operator("ph.set_place_axis")
            prop.axis = axis
            prop.invert_axis = invert
            obj_A = ALIGN_OBJ.get('active')

            if obj_A:
                pos = obj_A.get_bbox_center(is_local=False)
            else:
                pos = context.object.matrix_world.translation

            if axis == 'X':
                q = x if not invert else xD
            elif axis == 'Y':
                q = y if not invert else yD
            elif axis == 'Z':
                q = z if not invert else zD

            scale = Vector((2, 2, 2))

            mx = Matrix.LocRotScale(pos, q, scale)
            gz.matrix_basis = mx
            return gz

        prop = context.scene.place_tool
        exist_axis = prop.axis
        exist_invert = prop.invert_axis

        # not add the axis and invert direction that already exist
        set_axis_gzs = []
        for axis, invert in product(['X', 'Y', 'Z'], [False, True]):
            if axis == exist_axis and invert == exist_invert:
                continue
            gz = add_axis_gz(axis, invert)
            set_axis_gzs.append(gz)

        self.set_axis_gzs = set_axis_gzs

    def add_rotate_gz(self, context):
        gzObject = GizmoInfo(scale_basis=get_addon_pref().place_tool.gz.scale_basis,
                             color=get_addon_pref().place_tool.gz.color,
                             color_highlight=get_addon_pref().place_tool.gz.color_highlight, )

        self.rotate_gz = gzObject.set_up(self, 'PH_GT_custom_rotate_z_3d')
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

            x, y, z, xD, yD, zD = local_matrix(reverse_zD=True)
            axis = context.scene.place_tool.axis
            invert = context.scene.place_tool.invert_axis
            if axis == 'X':
                q = x if not invert else xD
            elif axis == 'Y':
                q = y if not invert else yD
            elif axis == 'Z':
                q = z if not invert else zD

            pos = obj_A.get_axis_center(axis, not invert, is_local=False)
            scale = Vector((1, 1, 1))
            mx = Matrix.LocRotScale(pos, q, scale)

            self.rotate_gz.matrix_basis = mx
            self.scale_gz.matrix_basis = mx

        elif obj_A and len(context.selected_objects) > 1:
            try:
                top = ALIGN_OBJS['top']
                z = get_objs_bbox_top(
                    [obj for obj in context.selected_objects if obj.type == 'MESH'])

                # 统一gizmo朝上
                self.rotate_gz.matrix_basis = Matrix()
                self.scale_gz.matrix_basis = Matrix()

                self.rotate_gz.matrix_basis.translation = Vector((top.x, top.y, z))
                self.scale_gz.matrix_basis.translation = Vector((top.x, top.y, z))

                # self.rotate_gz.matrix_basis = Matrix(Vector((top.x, top.y, z)))
                # self.scale_gz.matrix_basis = Matrix(Vector((top.x, top.y, z)))

            except (ZeroDivisionError, AttributeError):
                pass

    def refresh(self, context):
        if context.object:
            self.correct_gz_loc(context)

        prop = context.scene.place_tool

        if prop.setting_axis:
            self.add_set_axis_gz(context)
        else:
            self.remove_set_axis_gz()

    def draw_prepare(self, context):
        self.refresh(context)


classes = (
    PH_GZG_place_tool,

)


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except:
            pass


def unregister():
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass


def update_gzg_pref(self, context):
    unregister()
    register()
