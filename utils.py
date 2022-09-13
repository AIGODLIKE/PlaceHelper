import bpy
from bpy_extras import view3d_utils
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from bpy_extras.view3d_utils import location_3d_to_region_2d as loc3d_2_r2d
from bpy_extras.view3d_utils import region_2d_to_vector_3d as r2d_2_vec3d
from bpy_extras.view3d_utils import region_2d_to_origin_3d as r2d_2_origin3d
from bpy_extras.view3d_utils import region_2d_to_location_3d as r2d_2_loc3d

import time
import numpy as np
from dataclasses import dataclass, field
from contextlib import contextmanager

C_OBJECT_TYPE_HAS_BBOX = {'MESH', 'CURVE', 'FONT', 'LATTICE'}

faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (4, 0, 3, 7)]


@contextmanager
def timeit(name: str):
    start = time.time()
    yield
    end = time.time()
    print(f'{name} took {(end - start) * 1000} ms')


def ray_cast(context, event, start_point=None):
    mouse_pos = event.mouse_region_x, event.mouse_region_y
    scene = context.scene
    region = context.region
    region3D = context.space_data.region_3d
    viewlayer = context.view_layer.depsgraph

    # The direction indicated by the mouse position from the current view / The view point of the user
    view_vector = r2d_2_vec3d(region, region3D, mouse_pos)
    view_point = r2d_2_origin3d(region, region3D, mouse_pos)
    # The 3D location in this direction
    world_loc = r2d_2_loc3d(region, region3D, mouse_pos, view_vector)
    # first hit to get target obj
    if not start_point: start_point = view_point
    result, location, normal, index, target_obj, matrix = scene.ray_cast(viewlayer, start_point,
                                                                         view_vector)
    return result, target_obj, view_point, world_loc, normal, location, matrix


def get_objs_bbox_center(obj_list: list[bpy.types.Object]):
    # get bounding box center of all selected objects
    bbox_center = Vector((0, 0, 0))
    mx = lambda obj: obj.matrix_world

    for obj in obj_list:
        center = Vector((0, 0, 0))
        bbox_pts = [mx(obj) @ Vector(co) for co in obj.bound_box]
        for pt in bbox_pts:
            center += pt
        center = center / 8
        bbox_center += center

    return bbox_center / len(obj_list)


def get_objs_bbox_top(obj_list: list[bpy.types.Object]):
    # get bounding box center of all selected objects
    z = 0
    mx = lambda obj: obj.matrix_world

    for obj in obj_list:
        bbox_pts = [mx(obj) @ Vector(co) for co in obj.bound_box]
        max_z = max(bbox_pts, key=lambda v: v.z)
        if max_z.z > z:
            z = max_z.z

    return z


class AlignObject:

    def __init__(self, obj: bpy.types.Object, mode: str = 'ACCURATE', is_local: bool = False):
        """

        :param obj:
        :param mode: 用于bvh检测的模式，FAST或者ACCURATE ,DRAW 模式下无数据写入
        :param is_local: 返回数值为物体/世界坐标
        """
        self.obj = obj
        self.mode = mode  # 'FAST' or 'ACCURATE' or 'DRAW'
        self.is_local = is_local

        self._calc_bbox()
        self._bbox_pts = self._calc_bbox_pts()

        self.bvh_tree_update()

    # Evaluate object
    # ------------------------------------------------------------------------
    @property
    def eval_obj(self) -> bpy.types.Object:
        """
        获取物体的临时应用修改器后的id数据
        :return: bpy.types.Object
        """
        return self.obj.evaluated_get(bpy.context.view_layer.depsgraph)

    # BVH tree
    @property
    def bvh_tree(self) -> BVHTree:
        return self._bvh_tree

    def bvh_tree_update(self):
        self._bvh_tree = BVHTree.FromPolygons(self.get_bbox_pts(is_local=False), faces)

    # Matrix
    # -------------------------------------------------------------------------

    @property
    def mx(self) -> Matrix:
        return self.obj.matrix_world

    @mx.setter
    def mx(self, matrix: Matrix):
        self.obj.matrix_world = matrix

    # Bounding box
    # -------------------------------------------------------------------------

    def _calc_bbox(self):
        if self.obj.type == 'MESH' and self.mode == 'ACCURATE':
            me = self.eval_obj.data
            vertices = np.empty(len(me.vertices) * 3, dtype='f')
            me.vertices.foreach_get("co", vertices)
            vertices = vertices.reshape(len(me.vertices), 3)

            max_xyz_id = np.argmax(vertices, axis=0)
            min_xyz_id = np.argmin(vertices, axis=0)

            self.max_x = float(vertices[max_xyz_id[0], 0])
            self.max_y = float(vertices[max_xyz_id[1], 1])
            self.max_z = float(vertices[max_xyz_id[2], 2])
            self.min_x = float(vertices[min_xyz_id[0], 0])
            self.min_y = float(vertices[min_xyz_id[1], 1])
            self.min_z = float(vertices[min_xyz_id[2], 2])
        else:
            bbox_points = [Vector(v) for v in self.obj.bound_box]

            self.max_x = max(bbox_points, key=lambda v: v.x).x
            self.max_y = max(bbox_points, key=lambda v: v.y).y
            self.max_z = max(bbox_points, key=lambda v: v.z).z

            self.min_x = min(bbox_points, key=lambda v: v.x).x
            self.min_y = min(bbox_points, key=lambda v: v.y).y
            self.min_z = min(bbox_points, key=lambda v: v.z).z

    def _calc_bbox_pts(self):
        """
        pts order:
        (x_min, y_min, z_min), (x_min, y_min, z_max), (x_min, y_max, z_min), (x_min, y_max, z_max),
        (x_max, y_min, z_min), (x_max, y_min, z_max), (x_max, y_max, z_min), (x_max, y_max, z_max)
        """
        x = self.min_x, self.max_x
        y = self.min_y, self.max_y
        z = self.min_z, self.max_z

        pts = []

        for i in range(2):
            for j in range(2):
                for k in range(2):
                    pts.append(Vector((x[i], y[j], z[k])))

        return pts

    def axis_face_pts(self, axis, invert):
        """
        获取轴向的面点
        :param axis: 'X', 'Y', 'Z'
        :param invert: True or False
        :return:
        """
        pts = self._bbox_pts
        if axis == 'X':
            if invert:
                pts = pts[4:6] + pts[0:2]
            else:
                pts = pts[0:2] + pts[4:6]
        elif axis == 'Y':
            if invert:
                pts = pts[2:4] + pts[6:8]
            else:
                pts = pts[6:8] + pts[2:4]
        elif axis == 'Z':
            if invert:
                pts = pts[0:2] + pts[6:8]
            else:
                pts = pts[6:8] + pts[0:2]
        return pts

    @property
    def size(self):
        return self.max_x - self.min_x, self.max_y - self.min_y, self.max_z - self.min_z

    # Bounding box Max and min

    def min(self, axis='Z') -> float:
        _axis = '_' + axis.lower()
        return getattr(self, 'min' + _axis)

    def max(self, axis='Z') -> float:
        _axis = '_' + axis.lower()
        return getattr(self, 'max' + _axis)

    def get_bbox_pts(self, is_local: bool = False):
        """
        获取物体的包围盒的8个点
        :param mode: BboxMode
        :return: list of Vector
        """
        if is_local:
            bbox_pts = self._bbox_pts
        else:
            bbox_pts = [self.mx @ Vector(p) for p in self._bbox_pts]

        return bbox_pts

    def get_bbox_center(self, is_local: bool) -> Vector:
        """获取物体碰撞盒中心点"""
        total = Vector((0, 0, 0))
        for v in self.get_bbox_pts(is_local=is_local):
            total = total + v
        return total / 8

    def get_top_center(self, is_local: bool) -> Vector:
        """获取物体碰撞盒顶部中心点"""
        pt = self.get_bbox_center(is_local=True)
        pt.z += self.size[2] / 2

        if is_local:
            return pt
        else:
            return self.mx @ pt

    def get_bottom_center(self, is_local: bool) -> Vector:

        pt = self.get_bbox_center(is_local=True)
        pt.z -= self.size[2] / 2

        if is_local:
            return pt
        else:
            return self.mx @ pt


class AlignObjects():
    def __init__(self, obj_list: list[AlignObject]):
        self.obj_list = obj_list
        self._bbox_pts = self.get_bbox_pts()
        self.bvh_tree_update()

    def _calc_bbox_pts(self):
        """计算所有物体的包围盒的8个点"""
        obj = self.obj_list[0]
        obj.is_local = False
        bbox_pts = obj.get_bbox_pts(is_local=False)

        max_x = max(bbox_pts, key=lambda v: v.x).x
        max_y = max(bbox_pts, key=lambda v: v.y).y
        max_z = max(bbox_pts, key=lambda v: v.z).z

        min_x = min(bbox_pts, key=lambda v: v.x).x
        min_y = min(bbox_pts, key=lambda v: v.y).y
        min_z = min(bbox_pts, key=lambda v: v.z).z

        for obj in self.obj_list:
            obj.is_local = False
            bbox_pts = obj.get_bbox_pts(is_local=False)

            max_x = max(max_x, max(bbox_pts, key=lambda v: v.x).x)
            max_y = max(max_y, max(bbox_pts, key=lambda v: v.y).y)
            max_z = max(max_z, max(bbox_pts, key=lambda v: v.z).z)

            min_x = min(min_x, min(bbox_pts, key=lambda v: v.x).x)
            min_y = min(min_y, min(bbox_pts, key=lambda v: v.y).y)
            min_z = min(min_z, min(bbox_pts, key=lambda v: v.z).z)

        self.min_x = min_x
        self.min_y = min_y
        self.min_z = min_z
        self.max_x = max_x
        self.max_y = max_y
        self.max_z = max_z

        x = self.min_x, self.max_x
        y = self.min_y, self.max_y
        z = self.min_z, self.max_z

        bbox_pts = []

        for i in range(2):
            for j in range(2):
                for k in range(2):
                    bbox_pts.append(Vector((x[i], y[j], z[k])))

        return bbox_pts

    def get_bbox_pts(self):
        return self._calc_bbox_pts()

    def get_bbox_center(self):
        total = Vector((0, 0, 0))
        for v in self.get_bbox_pts():
            total = total + v
        return total / 8

    def get_bottom_center(self):
        pt = self.get_bbox_center()
        pt.z -= (self.max_z - self.min_z) / 2
        return pt

    def get_top_center(self):
        pt = self.get_bbox_center()
        pt.z += (self.max_z - self.min_z) / 2
        return pt

    @property
    def size(self):
        return Vector((self.max_x - self.min_x, self.max_y - self.min_y, self.max_z - self.min_z))

    # BVH tree
    @property
    def bvh_tree(self) -> BVHTree:
        return self._bvh_tree

    def bvh_tree_update(self):
        self._bvh_tree = BVHTree.FromPolygons(self.get_bbox_pts(), faces)