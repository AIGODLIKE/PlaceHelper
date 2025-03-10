import bpy
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

# 以下物体检测bbox
C_OBJECT_TYPE_HAS_BBOX = {"MESH", "CURVE", "FONT", "LATTICE", "LIGHT"}
# 创建bbox的面顶点顺序
faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (4, 0, 3, 7)]


def DebugWrapper(func):
    def wrapper(*args, **kwargs):
        # func name
        print(func.__name__)
        return func(*args, **kwargs)

    return wrapper


class AlignObject:

    def __init__(self, obj: bpy.types.Object, mode: str = "ACCURATE", is_local: bool = False,
                 build_instance: bool = True):
        """
        :param obj:
        :param mode: 用于bvh检测的模式，FAST或者ACCURATE ,DRAW 模式下无数据写入
        :param is_local: 返回数值为物体/世界坐标
        """
        self.obj = obj
        self.mode = mode  # "FAST" or "ACCURATE" or "DRAW"
        self.is_local = is_local
        self.build_instance = build_instance

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
        # print("calc_bbox")

        def default_bbox():
            # print("default_bbox")
            bbox_points = [Vector(v) for v in self.obj.bound_box]

            self.max_x = max(bbox_points, key=lambda v: v.x).x
            self.max_y = max(bbox_points, key=lambda v: v.y).y
            self.max_z = max(bbox_points, key=lambda v: v.z).z

            self.min_x = min(bbox_points, key=lambda v: v.x).x
            self.min_y = min(bbox_points, key=lambda v: v.y).y
            self.min_z = min(bbox_points, key=lambda v: v.z).z

        def mesh_bbox(me):
            vertices = np.empty(len(me.vertices) * 3, dtype="f")
            me.vertices.foreach_get("co", vertices)
            vertices = vertices.reshape(len(me.vertices), 3)

            max_xyz_id = np.argmax(vertices, axis=0)
            min_xyz_id = np.argmin(vertices, axis=0)

            return vertices, max_xyz_id, min_xyz_id

        if self.obj.type != "MESH":
            return default_bbox()

        if self.mode != "ACCURATE":
            return default_bbox()
        # single mesh
        # ----------------
        me = self.eval_obj.data
        if len(me.vertices) != 0:
            vertices, max_xyz_id, min_xyz_id = mesh_bbox(me)
            self.max_x = float(vertices[max_xyz_id[0], 0])
            self.max_y = float(vertices[max_xyz_id[1], 1])
            self.max_z = float(vertices[max_xyz_id[2], 2])
            self.min_x = float(vertices[min_xyz_id[0], 0])
            self.min_y = float(vertices[min_xyz_id[1], 1])
            self.min_z = float(vertices[min_xyz_id[2], 2])
            return

        # instance
        # ----------------
        if not self.build_instance: return default_bbox()

        find = False
        deps = bpy.context.view_layer.depsgraph

        pts = []
        for ob_inst in deps.object_instances:
            if not ob_inst.is_instance: continue
            if ob_inst.parent is not self.eval_obj: continue
            matrix_world = ob_inst.matrix_world
            try:  # 只评估网格物体实例
                me = ob_inst.object.to_mesh()
            except:
                continue
            if len(me.vertices) == 0: continue
            find = True

            vertices, max_xyz_id, min_xyz_id = mesh_bbox(me)
            max_x = float(vertices[max_xyz_id[0], 0])
            max_y = float(vertices[max_xyz_id[1], 1])
            max_z = float(vertices[max_xyz_id[2], 2])
            min_x = float(vertices[min_xyz_id[0], 0])
            min_y = float(vertices[min_xyz_id[1], 1])
            min_z = float(vertices[min_xyz_id[2], 2])

            v_max_x = Vector((max_x, 0, 0))
            v_max_y = Vector((0, max_y, 0))
            v_max_z = Vector((0, 0, max_z))
            v_min_x = Vector((min_x, 0, 0))
            v_min_y = Vector((0, min_y, 0))
            v_min_z = Vector((0, 0, min_z))

            pts.append(matrix_world @ v_max_x)
            pts.append(matrix_world @ v_max_y)
            pts.append(matrix_world @ v_max_z)
            pts.append(matrix_world @ v_min_x)
            pts.append(matrix_world @ v_min_y)
            pts.append(matrix_world @ v_min_z)
            ob_inst.object.to_mesh_clear()

        if not find:
            print("did not find any instance")
            return default_bbox()

        # calc max and min
        if len(pts) == 0: return default_bbox()
        # print(pts)

        # invert matrix_world back to object parent"s matrix_world
        pts = [self.mx.inverted() @ pt for pt in pts]

        # use numpy to calc max and min
        pts = np.array(pts)
        max_xyz_id = np.argmax(pts, axis=0)
        min_xyz_id = np.argmin(pts, axis=0)
        self.max_x = float(pts[max_xyz_id[0], 0])
        self.max_y = float(pts[max_xyz_id[1], 1])
        self.max_z = float(pts[max_xyz_id[2], 2])
        self.min_x = float(pts[min_xyz_id[0], 0])
        self.min_y = float(pts[min_xyz_id[1], 1])
        self.min_z = float(pts[min_xyz_id[2], 2])

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
        :param axis: "X", "Y", "Z"
        :param invert: True or False
        :return:
        """
        pts = self._bbox_pts
        if axis == "X":
            if invert:
                pts = pts[4:6] + pts[0:2]
            else:
                pts = pts[0:2] + pts[4:6]
        elif axis == "Y":
            if invert:
                pts = pts[2:4] + pts[6:8]
            else:
                pts = pts[6:8] + pts[2:4]
        elif axis == "Z":
            if invert:
                pts = pts[0:2] + pts[6:8]
            else:
                pts = pts[6:8] + pts[0:2]
        return pts

    @property
    def size(self):
        return self.max_x - self.min_x, self.max_y - self.min_y, self.max_z - self.min_z

    # Bounding box Max and min

    def min(self, axis="Z") -> float:
        _axis = "_" + axis.lower()
        return getattr(self, "min" + _axis)

    def max(self, axis="Z") -> float:
        _axis = "_" + axis.lower()
        return getattr(self, "max" + _axis)

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

    def get_bbox_center_offset(self, axis="Z", invert_axis=False) -> Vector:
        """获取物体碰撞盒中心点相对于物体位置的偏移"""
        offset = self.get_bbox_center(is_local=False) - self.mx.translation
        if axis == "X":
            offset.x = 0
        elif axis == "Y":
            offset.y = 0
        elif axis == "Z":
            offset.z = 0

        if invert_axis:
            offset = Vector((-offset.x, -offset.y, -offset.z))

        return offset

    def get_pos_z_center(self, is_local: bool) -> Vector:
        """获取物体碰撞盒顶部中心点"""
        pt = self.get_bbox_center(is_local=True)
        pt.z += self.size[2] / 2

        if is_local:
            return pt
        else:
            return self.mx @ pt

    def get_neg_z_center(self, is_local: bool) -> Vector:

        pt = self.get_bbox_center(is_local=True)
        pt.z -= self.size[2] / 2

        if is_local:
            return pt
        else:
            return self.mx @ pt

    def get_axis_center(self, axis: str, invert_axis: bool, is_local: bool) -> Vector:
        """获取物体碰撞盒顶部中心点"""
        pt = self.get_bbox_center(is_local=True)
        _axis = {"X": 0, "Y": 1, "Z": 2}
        invert = 1 if invert_axis else -1
        pt[_axis[axis]] += self.size[_axis[axis]] / 2 * invert

        if is_local:
            return pt
        else:
            return self.mx @ pt


class AlignObjects:
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
