import bpy
import math
from mathutils import Vector, Color, Euler, Matrix

from ..util.gz import GizmoInfo, GZGBase
from ..util.get_position import get_objs_bbox_center, get_objs_bbox_top
from ..util.get_gz_matrix import local_matrix

from ._runtime import ALIGN_OBJ, ALIGN_OBJS
from ..get_addon_pref import get_addon_pref


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

            x, y, z, xD, yD, zD =  local_matrix()
            axis = context.scene.place_tool.axis
            invert = context.scene.place_tool.invert_axis
            if  axis =='X':
                q = x if not invert else xD
            elif axis =='Y':
                q = y if not invert else yD
            elif axis =='Z':
                q = z if not invert else zD

            m = Matrix.LocRotScale(Vector((0, 0, 0)), q, Vector((1, 1, 1)))

            self.rotate_gz.matrix_basis = m
            self.scale_gz.matrix_basis = m

            self.rotate_gz.matrix_basis.translation = obj_A.get_pos_z_center(is_local=False)
            self.scale_gz.matrix_basis.translation = obj_A.get_pos_z_center(is_local=False)

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
