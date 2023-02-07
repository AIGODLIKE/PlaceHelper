import bpy
import bgl
import bmesh
import numpy as np

from bpy.types import Gizmo
from mathutils import Vector
from bpy_extras import view3d_utils

from dataclasses import dataclass
from pathlib import Path

SHAPES = {}


def load_shape_geo_obj(obj_name='gz_shape_ROTATE'):
    """ 加载一个几何形状的模型，用于绘制几何形状的控件 """

    if obj_name in bpy.data.objects:
        return bpy.data.objects[obj_name]
    else:
        gz_shape_path = Path(__file__).parent.joinpath('custom_shape', 'gz_shape.blend')
        with bpy.data.libraries.load(str(gz_shape_path)) as (data_from, data_to):
            data_to.objects = [obj_name]
        SHAPES[obj_name] = data_to.objects[0]
        return SHAPES[obj_name]


def create_geo_shape(obj=None, type='TRIS', scale=1):
    """ 创建一个几何形状，默认创造球体

    :param obj:
    :return:
    """
    if obj:
        tmp_mesh = obj.data
    else:
        tmp_mesh = bpy.data.meshes.new('tmp')
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=scale / 5, calc_uvs=True)
        bm.to_mesh(tmp_mesh)
        bm.free()

    mesh = tmp_mesh
    vertices = np.zeros((len(mesh.vertices), 3), 'f')
    mesh.vertices.foreach_get("co", vertices.ravel())
    mesh.calc_loop_triangles()

    if type == 'LINES':
        edges = np.zeros((len(mesh.edges), 2), 'i')
        mesh.edges.foreach_get("vertices", edges.ravel())
        custom_shape_verts = vertices[edges].reshape(-1, 3)
    else:
        tris = np.zeros((len(mesh.loop_triangles), 3), 'i')
        mesh.loop_triangles.foreach_get("vertices", tris.ravel())
        custom_shape_verts = vertices[tris].reshape(-1, 3)

    if not obj:
        bpy.data.meshes.remove(mesh)

    return custom_shape_verts


class PH_GT_custom_move_3d(Gizmo):
    bl_idname = "PH_GT_custom_move_3d"

    def draw(self, context):
        self.draw_custom_shape(self.custom_shape)

    def draw_select(self, context, select_id):
        self.draw_custom_shape(self.custom_shape, select_id=select_id)

    def setup(self):
        if not hasattr(self, "custom_shape"):
            obj = bpy.context.object if bpy.context.object else None

            self.custom_shape = self.new_custom_shape('LINES', create_geo_shape(obj=obj,
                                                                                scale=0.1))


class PH_GT_custom_scale_3d(Gizmo):
    bl_idname = "TEST_GE_custom_scale_3d"

    def ensure_gizmo(self):
        if not hasattr(self, "custom_shape"):
            obj = load_shape_geo_obj('gz_shape_SCALE')

            self.custom_shape = self.new_custom_shape('TRIS', create_geo_shape(obj=obj,
                                                                               scale=0.1))

    def draw(self, context):
        self.ensure_gizmo()
        self.draw_custom_shape(self.custom_shape)

    def draw_select(self, context, select_id):
        self.ensure_gizmo()
        self.draw_custom_shape(self.custom_shape, select_id=select_id)

    def setup(self):
        self.ensure_gizmo()


class PH_GT_custom_rotate_z_3d(Gizmo):
    bl_idname = "PH_GT_custom_rotate_z_3d"

    def ensure_gizmo(self):
        if not hasattr(self, "custom_shape"):
            obj = load_shape_geo_obj('gz_shape_ROTATE')

            self.custom_shape = self.new_custom_shape('TRIS', create_geo_shape(obj=obj,
                                                                               scale=0.2))

    def draw(self, context):
        self.ensure_gizmo()
        self.draw_custom_shape(self.custom_shape)

    def draw_select(self, context, select_id):
        self.ensure_gizmo()
        self.draw_custom_shape(self.custom_shape, select_id=select_id)

    def setup(self):
        self.ensure_gizmo()

class PH_GT_custom_move_plane_3d(Gizmo):
    def ensure_gizmo(self):
        if not hasattr(self, "custom_shape"):
            obj = load_shape_geo_obj('gz_shape_PLANE')

            self.custom_shape = self.new_custom_shape('TRIS', create_geo_shape(obj=obj,
                                                                               scale=0.2))

    def draw(self, context):
        self.ensure_gizmo()
        self.draw_custom_shape(self.custom_shape)

    def draw_select(self, context, select_id):
        self.ensure_gizmo()
        self.draw_custom_shape(self.custom_shape, select_id=select_id)

    def setup(self):
        self.use_draw_offset_scale = True
        self.ensure_gizmo()

classes = (
    PH_GT_custom_move_3d,
    PH_GT_custom_scale_3d,
    PH_GT_custom_rotate_z_3d,
    PH_GT_custom_move_plane_3d
)

register, unregister = bpy.utils.register_classes_factory(classes)
