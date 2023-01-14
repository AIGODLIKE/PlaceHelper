import math
import bpy

from mathutils import Vector, Matrix, Euler
from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty

from contextlib import contextmanager

from ..utils import C_OBJECT_TYPE_HAS_BBOX
from ..util.obj_bbox import AlignObject, AlignObjects
from ..util.raycast import ray_cast

from ..get_addon_pref import get_addon_pref
from .draw_bbox import draw_bbox_callback

from ._runtime import SCENE_OBJS, ALIGN_OBJ, OVERLAP_OBJ, ALIGN_OBJS

# 工具属性设置
place_tool_props = lambda: bpy.context.scene.place_tool


@contextmanager
def exclude_ray_cast(obj_list: list[bpy.types.Object]):
    """光线投射时排除物体"""
    ori_child_vis = {}
    for obj in obj_list:
        for child in obj.children_recursive:
            if child in obj_list: continue
            ori_child_vis[child] = child.hide_get()
            child.hide_set(True)
        obj.hide_set(True)
    yield  # 执行上下文管理器中的代码（光线投射）
    for obj in obj_list:
        obj.hide_set(False)
        obj.select_set(True)

    for child,ori_vis in ori_child_vis.items():
        child.hide_set(ori_vis)

@contextmanager
def store_objs_mx(obj_list: list[bpy.types.Object], restore: bool) -> dict:
    """保存物体的原始矩阵，并将物体的矩阵恢复到原始矩阵"""
    mx_dict = {}
    for obj in obj_list:
        mx_dict[obj] = obj.matrix_world.copy()
    yield mx_dict  # 执行上下文管理器中的代码
    if restore:
        for obj, mx in mx_dict.items():
            obj.matrix_world = mx


@contextmanager
def mouse_offset(op, event, scale=0.01, scale_shift=0.0025):
    op.mouseDX -= event.mouse_x
    op.mouseDY -= event.mouse_y
    scale_factor = scale_shift if event.shift else scale
    yield (op.mouseDX * scale_factor, op.mouseDY * scale_factor)
    op.mouseDX = event.mouse_x
    op.mouseDY = event.mouse_y


class CheckBVHTree:
    has_bbox = False

    overlap = False

    active_mode = 'ACCURATE'
    scene_mode = 'FAST'

    def obj_has_bbox(self, context):
        """确认物体是否有碰撞盒，将影响到绘制/碰撞检测"""
        if context.object.type in C_OBJECT_TYPE_HAS_BBOX:
            self.has_bbox = True
        else:
            self.has_bbox = False

    def init_bbox_pref(self):
        pref = get_addon_pref()
        # 获取构建精度
        self.active_mode = pref.place_tool.bbox.active_bbox_calc_mode
        self.scene_mode = pref.place_tool.bbox.other_bbox_calc_mode

    def build_bbox_bvh(self, context):
        """预计算bvh，用于检测是否碰撞"""
        self.clear_bbox_bvh()

        if not self.has_bbox: return

        for obj in context.view_layer.objects:
            if obj.hide_get():
                continue
            elif obj.type not in C_OBJECT_TYPE_HAS_BBOX:
                continue
            elif obj in context.object.children_recursive:
                continue

            if obj is context.object:
                obj_A = AlignObject(obj, self.active_mode)
                SCENE_OBJS[obj] = obj_A
                ALIGN_OBJ['active'] = obj_A

            else:
                SCENE_OBJS[obj] = AlignObject(obj, self.scene_mode)

    def check_bbox_overlap(self, context, exclude_obj_list=None):
        """检测是否有碰撞"""

        obj = context.object
        if not obj or not self.has_bbox: return

        ALIGN_OBJ['active'].bvh_tree_update()
        # 检测是否更新了激活物体
        for key, obj_A in SCENE_OBJS.items():
            if obj_A.obj == ALIGN_OBJ['active'].obj:
                continue
            elif exclude_obj_list and key in exclude_obj_list:
                continue
            elif ALIGN_OBJ['active'].bvh_tree.overlap(obj_A.bvh_tree):
                OVERLAP_OBJ['obj'] = obj_A
                return True

        OVERLAP_OBJ.clear()

    def check_objects_overlap(self, context, exclude_obj_list=None):
        if not hasattr(self, 'objs_A'): return

        for key, obj_A in SCENE_OBJS.items():
            if key in exclude_obj_list:
                continue
            if self.objs_A.bvh_tree.overlap(obj_A.bvh_tree):
                OVERLAP_OBJ['obj'] = obj_A
                return True

        OVERLAP_OBJ.clear()

    def clear_bbox_bvh(self):
        OVERLAP_OBJ.clear()
        SCENE_OBJS.clear()


class ModalBase(CheckBVHTree):
    bl_options = {'REGISTER', 'UNDO'}

    _handle = None  # 绘制
    cursor_modal = None  # 鼠标指针

    old_obj = None  # 原物体
    new_obj = None  # 复制物体

    # 光线投射
    tg_obj = None  # tg_obj: BVHTree.FromObject
    tg_bvh = None
    tmp_parent = None

    # 多物体
    ori_mx = {}
    off_cen_mx = {}
    off_bot_mx = {}
    dis = None

    @classmethod
    def poll(cls, context):
        return context.object and context.object.select_get()

    # STATE
    # -------------------------------------------------------

    def stop_moving(self, exclude_obj_list=None):
        """物体是否需要停止移动"""
        if exclude_obj_list and len(exclude_obj_list) > 1:
            check = self.check_objects_overlap
        else:
            check = self.check_bbox_overlap

        return check(bpy.context, exclude_obj_list) and place_tool_props().coll_stop  # 先后顺序

    def invoke(self, context, event):
        self.clear_target()
        self.init_bbox_pref()

        self.handle_copy_event(context, event)

        self.init_mouse(event)

        self.init_context_obj(context)

        if context.object and len(context.selected_objects) > 1:
            self.store_muil_obj_info(context)
        else:
            self.selected_objs = [context.object]
        # 预构建
        self.build_bbox_bvh(bpy.context)
        self.append_handles()
        # 初始化颜色
        self.check_bbox_overlap(bpy.context)

        return {'RUNNING_MODAL'}

    # INIT
    # -------------------------------------------------------

    def store_muil_obj_info(self, context):
        """选中多个物体时候，储存其信息"""
        self.ori_mx.clear()
        self.off_cen_mx.clear()
        self.off_bot_mx.clear()

        selected_objs = [obj for obj in context.selected_objects if obj.type in C_OBJECT_TYPE_HAS_BBOX]
        objs = [AlignObject(obj, is_local=False) for obj in selected_objs]
        objs_A = AlignObjects(objs)
        center = objs_A.get_bbox_center()
        bottom = objs_A.get_bottom_center()
        top = objs_A.get_top_center()
        self.dis = (objs_A.max_z - objs_A.min_z) / 2
        # print('dis:', self.dis)
        # print('center:', center)
        # print('bottom:', bottom)

        self.ori_bbox_pts = objs_A.get_bbox_pts()

        for obj in selected_objs:
            self.ori_mx[obj] = obj.matrix_world.copy()
            self.off_cen_mx[obj] = Matrix.Translation(obj.matrix_world.translation - center)
            self.off_bot_mx[obj] = Matrix.Translation(obj.matrix_world.translation - bottom)

        self.center = center
        self.bottom = bottom
        self.top = top
        self.selected_objs = selected_objs
        self.objs = objs
        self.objs_A = objs_A
        # 存储到全局用于绘制gz/碰撞盒
        ALIGN_OBJS['bottom'] = bottom
        ALIGN_OBJS['center'] = center
        ALIGN_OBJS['top'] = top

        self.off_bbox_pts_mx = [Matrix.Translation(pt - center) for pt in self.ori_bbox_pts]

    def clear_target(self):
        """清理临时变量"""
        self.tg_obj = None
        self.tg_bvh = None

    def init_mouse(self, event):
        """初始化鼠标"""
        self.mouse_x = event.mouse_x
        self.mouse_y = event.mouse_y
        self.mouseDX = event.mouse_x
        self.mouseDY = event.mouse_y
        # start
        self.startX = event.mouse_x
        self.startY = event.mouse_y

    def init_context_obj(self, context):
        """初始化激活物体"""
        self.obj_has_bbox(context)

        self.new_obj = None
        self.old_obj = context.object

        self.ori_matrix_world = context.object.matrix_world.copy()

    def set_cursor_modal(self, type='MOVE_X'):
        self.cursor_set = True
        bpy.context.window.cursor_set(type)

    def reset_cursor_modal(self):
        bpy.context.window.cursor_set('DEFAULT')
        bpy.context.window.cursor_modal_restore()

    # HANDLE
    # ----------------------------------------------------------------------------------------------

    def append_handles(self):
        # hide outline
        self.ori_show_outline_selected = bpy.context.space_data.overlay.show_outline_selected
        bpy.context.space_data.overlay.show_outline_selected = False

        if self.cursor_modal:
            self.set_cursor_modal(self.cursor_modal)
        self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_bbox_callback, (self, bpy.context), 'WINDOW',
                                                              'POST_PIXEL')
        # modal
        bpy.context.window_manager.modal_handler_add(self)

    def remove_handles(self):
        # show outline
        bpy.context.space_data.overlay.show_outline_selected = self.ori_show_outline_selected

        self.reset_cursor_modal()

        # clear bvh trees
        if self.has_bbox:
            self.clear_bbox_bvh()

        if hasattr(self, '_handle'):
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')

        self._handle = None

        self.clear_bbox_bvh()

    # COPY
    # ----------------------------------------------------------------------------------------------

    def copy_obj(self, context):
        if len(context.selected_objects) == 1:
            old_obj = context.object
            new_obj = context.object.copy()

            if place_tool_props().duplicate == 'COPY' and new_obj.data:
                new_data = old_obj.data.copy()
                new_obj.data = new_data

            context.collection.objects.link(new_obj)
            context.view_layer.objects.active = new_obj

            old_obj.select_set(False)
            new_obj.select_set(True)
        elif len(context.selected_objects) > 1:
            for obj in context.selected_objects:
                new_obj = obj.copy()
                if place_tool_props().duplicate == 'COPY' and new_obj.data:
                    new_data = obj.data.copy()
                    new_obj.data = new_data
                context.collection.objects.link(new_obj)
                if obj is context.object:
                    context.view_layer.objects.active = new_obj
                obj.select_set(False)
                new_obj.select_set(True)

    def handle_copy_event(self, context, event):
        if event.shift:
            self.copy_obj(context)


class PH_OT_move_object(ModalBase, bpy.types.Operator):
    """Move"""
    bl_idname = "ph.move_object"
    bl_label = "Move"

    cursor_modal = 'SCROLL_XY'

    ori_mx = {}
    off_cen_mx = {}

    axis: EnumProperty(name='Axis', items=[('X', 'X', 'X'), ('Y', 'Y', 'Y'), ('Z', 'Z', 'Z')], default='Z')

    def invoke(self, context, event):
        self.clear_target()
        self.init_bbox_pref()

        self.handle_copy_event(context, event)

        self.init_mouse(event)
        self.init_context_obj(context)

        if context.object and len(context.selected_objects) > 1:
            self.store_muil_obj_info(context)
            self.create_bottom_parent()
        else:
            self.selected_objs = [context.object]
        # 预构建
        self.build_bbox_bvh(bpy.context)
        self.append_handles()
        # 初始化颜色
        self.check_bbox_overlap(bpy.context)

        return {'RUNNING_MODAL'}

    def create_bottom_parent(self):
        empty = bpy.data.objects.new('Empty', None)
        empty.name = 'TMP_PARENT'
        empty.empty_display_type = 'PLAIN_AXES'
        empty.empty_display_size = 0
        empty.location = self.bottom

        for obj in self.selected_objs:
            if obj.parent and obj.parent in self.selected_objs:
                obj.select_set(False)
                continue
            # loop over the constraints in each object
            con = obj.constraints.new('CHILD_OF')
            con.name = 'TMP_PARENT'
            con.use_rotation_x = True
            con.use_rotation_y = True
            con.use_rotation_z = True
            con.target = empty
            obj.select_set(False)

        self.tmp_parent = empty
        bpy.context.collection.objects.link(empty)
        bpy.context.view_layer.objects.active = empty
        # empty.select_set(True)

    def clear_bottom_parent(self):
        if self.tmp_parent:
            # apply constraints
            for obj in self.selected_objs:
                obj.select_set(True)
                tmp_mx = obj.matrix_world.copy()
                for con in obj.constraints:
                    if con.name == 'TMP_PARENT' and con.type == 'CHILD_OF':
                        obj.constraints.remove(con)

                obj.matrix_world = tmp_mx
            # remove empty
            bpy.data.objects.remove(self.tmp_parent)
            self.tmp_parent = None
            bpy.context.view_layer.objects.active = self.old_obj

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            if len(self.selected_objs) == 1:
                self.handle_obj(context, event)
            else:
                self.handle_multi_obj(context, event)

        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self.tg_obj = None
            self.clear_bottom_parent()
            self.remove_handles()
            return {"FINISHED"}

        return {"RUNNING_MODAL"}

    def handle_obj(self, context, event):

        with exclude_ray_cast([context.object]):
            z = Vector((0, 0, 1))
            self.normal = z
            result, target_obj, view_point, world_loc, normal, location, matrix = ray_cast(context, event)

            # get bounding box offset
            offset_axis = 0
            offset_xy = Vector((0, 0, 0))
            if self.has_bbox:
                obj_A = ALIGN_OBJ['active']
                obj_A.is_local = True

                offset_axis = getattr(obj_A, 'min_' + self.axis.lower()) * -1
                scale = getattr(obj_A.mx.to_scale(), self.axis.lower())
                offset_axis = offset_axis * scale

                offset_origin = obj_A.get_bbox_center(is_local=False)
                offset_x = obj_A.mx.translation.x - offset_origin.x
                offset_y = obj_A.mx.translation.y - offset_origin.y

                # offset_xy = Vector((offset_x, offset_y, 0)) * -1
                offset_xy = Vector((0, 0, 0))

            # ray cast calc
            self.tg_obj = None
            if result:
                self.tg_obj = target_obj
                self.normal = normal.normalized()

                bbox_offset = 1 + get_addon_pref().place_tool.bbox.offset
                world_loc = (location) + self.normal * offset_axis * bbox_offset - offset_xy
            else:
                world_loc -= offset_xy

            with store_objs_mx([context.object], self.stop_moving(exclude_obj_list=[self.tg_obj])):
                context.object.matrix_world.translation = world_loc
                if place_tool_props().orient == 'NORMAL':
                    self.clear_rotate(context.object)

    def handle_multi_obj(self, context, event):

        with exclude_ray_cast(self.selected_objs):
            z = Vector((0, 0, 1))
            self.normal = z
            result, target_obj, view_point, world_loc, normal, location, matrix = ray_cast(context, event)

            # ray cast calc
            self.tg_obj = None

            if result:
                self.tg_obj = target_obj
                self.normal = normal.normalized()

                world_loc = location

            with store_objs_mx([context.object], self.stop_moving(exclude_obj_list=[self.tg_obj] + self.selected_objs)):
                self.tmp_parent.location = world_loc
                if place_tool_props().orient == 'NORMAL':
                    self.tmp_parent.rotation_euler = z.rotation_difference(self.normal).to_euler()
                self.objs_A.bvh_tree_update()

            # draw
            offset_mx = Matrix.Translation(world_loc - self.center)
            ALIGN_OBJS['bbox_pts'] = self.objs_A.get_bbox_pts()
            ALIGN_OBJS['top'] = offset_mx @ self.top
            ALIGN_OBJS['center'] = offset_mx @ self.top  # 使用默认center容易闪烁，故改用top
            ALIGN_OBJS['bottom'] = self.tmp_parent.location
            ALIGN_OBJS['size'] = self.objs_A.size

    def clear_rotate(self, obj):
        """清除除了local z以外轴向的旋转"""
        z = Vector((0, 0, 1))
        rotate_mode = {'Z': 'ZYX', 'X': 'XYZ', 'Y': 'YXZ'}[self.axis]
        self.rotate_clear = self.ori_matrix_world.to_euler(rotate_mode)

        for a in ['x', 'y', 'z']:
            if a != self.axis.lower():
                setattr(self.rotate_clear, a, 0)

        self.rotate_clear = self.rotate_clear.to_matrix().to_euler(obj.rotation_mode)

        offset_euler = z.rotation_difference(self.normal).to_euler()
        obj.rotation_euler = (
                offset_euler.to_matrix().to_4x4() @ self.rotate_clear.to_matrix().to_4x4()).to_euler()


class PH_OT_rotate_object(ModalBase, bpy.types.Operator):
    """Rotate"""
    bl_idname = 'ph.rotate_object'
    bl_label = 'Rotate'

    cursor_modal = 'SCROLL_X'

    obj_name: StringProperty(name='Object Name')
    axis: EnumProperty(items=[('X', 'X', 'X'), ('Y', 'Y', 'Y'), ('Z', 'Z', 'Z')])

    def handle_obj(self, context, event):
        self.check_bbox_overlap(context)

        with mouse_offset(self, event) as (offset_x, offset_y):
            offset = offset_x

        rotate_mode = {'Z': 'ZYX', 'X': 'XYZ', 'Y': 'YXZ'}[self.axis]

        rot = context.object.rotation_euler.to_matrix().to_euler(rotate_mode)
        axis = self.axis.lower()
        setattr(rot, axis, getattr(rot, axis) + offset)

        obj_A = ALIGN_OBJ['active']
        pivot = obj_A.get_bbox_center(is_local=False)
        # get rotate axis
        if obj_A.size[2] != 0:
            z = pivot - obj_A.get_bottom_center(is_local=False)
        else:
            pt = obj_A.mx @ Vector((obj_A.min_x, obj_A.min_y, 0))
            pt1 = obj_A.mx @ Vector((obj_A.min_x, obj_A.max_y, 0))
            pt2 = obj_A.mx @ Vector((obj_A.max_x, obj_A.max_y, 0))
            v1 = pt1 - pt  # 垂直于x轴的向量
            v2 = pt2 - pt  # 垂直于x轴的向量
            z = -v1.cross(v2)  # 垂直于x轴的向量

        rot_matrix = (
                Matrix.Translation(pivot) @
                Matrix.Diagonal(Vector((1,) * 3)).to_4x4() @
                Matrix.Rotation(-offset, 4, z) @
                Matrix.Translation(-pivot)
        )

        with store_objs_mx([context.object], self.stop_moving()):
            context.object.matrix_world = rot_matrix @ context.object.matrix_world

    def handle_multi_obj(self, context, event):
        with mouse_offset(self, event) as (offset_x, offset_y):
            offset = offset_x

        z = Vector((0, 0, 1))
        pivot = self.bottom
        rot_matrix = (
                Matrix.Translation(pivot) @
                Matrix.Diagonal(Vector((1,) * 3)).to_4x4() @
                Matrix.Rotation(-offset, 4, z) @
                Matrix.Translation(-pivot)
        )

        with store_objs_mx(self.selected_objs,
                           self.stop_moving(exclude_obj_list=[self.tg_obj] + self.selected_objs)):
            for obj in self.selected_objs:
                obj.matrix_world = rot_matrix @ obj.matrix_world
            self.objs_A.bvh_tree_update()

        ALIGN_OBJS['top'] = rot_matrix @ ALIGN_OBJS['top']
        ALIGN_OBJS['center'] = rot_matrix @ self.center
        ALIGN_OBJS['bottom'] = rot_matrix @ self.bottom
        ALIGN_OBJS['bbox_pts'] = self.objs_A.get_bbox_pts()
        ALIGN_OBJS['size'] = self.objs_A.size

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            if context.object and len(context.selected_objects) == 1:
                self.handle_obj(context, event)
            elif context.object and len(context.selected_objects) > 1:
                self.handle_multi_obj(context, event)

        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self.remove_handles()
            return {'FINISHED'}

        return {'RUNNING_MODAL'}


class PH_OT_scale_object(ModalBase, bpy.types.Operator):
    """Scale"""
    bl_idname = 'ph.scale_object'
    bl_label = 'Scale'
    bl_options = {'REGISTER', 'UNDO'}

    cursor_modal = 'MOVE_Y'

    def handle_obj(self, context, event):
        self.check_bbox_overlap(context)

        with mouse_offset(self, event, scale=0.01, scale_shift=0.005) as (offset_x, offset_y):
            offset = offset_y

        self.obj_A = ALIGN_OBJ['active']

        offset = offset * -1 + 1

        scale_factor = Vector((offset,) * 3)
        pivot = self.obj_A.get_bottom_center(is_local=False)
        scale_matrix = (
                Matrix.Translation(pivot) @
                Matrix.Diagonal(scale_factor).to_4x4() @
                Matrix.Rotation(math.radians(0), 4, Vector((0, 0, 1))) @
                Matrix.Translation(-pivot)
        )

        with store_objs_mx([self.obj_A.obj], self.stop_moving()):
            context.object.matrix_world = scale_matrix @ context.object.matrix_world

    def handle_multi_obj(self, context, event):
        with mouse_offset(self, event, scale=0.01, scale_shift=0.005) as (offset_x, offset_y):
            offset = offset_y

        self.obj_A = ALIGN_OBJ['active']

        offset = offset * -1 + 1
        # offset_mx = self.obj_A.obj.matrix_world @ self.ori_mx[self.obj_A.obj].inverted()
        scale_factor = Vector((offset,) * 3)
        pivot = self.bottom

        scale_matrix = (
                Matrix.Translation(pivot) @
                Matrix.Diagonal(scale_factor).to_4x4() @
                Matrix.Rotation(math.radians(0), 4, Vector((0, 0, 1))) @
                Matrix.Translation(-pivot)
        )

        with store_objs_mx(self.selected_objs, self.stop_moving(exclude_obj_list=[self.tg_obj] + self.selected_objs)):
            for obj in self.selected_objs:
                obj.matrix_world = scale_matrix @ obj.matrix_world
            self.objs_A.bvh_tree_update()

        ALIGN_OBJS['top'] = scale_matrix @ ALIGN_OBJS['top']
        ALIGN_OBJS['center'] = scale_matrix @ self.center
        ALIGN_OBJS['bottom'] = scale_matrix @ self.bottom
        ALIGN_OBJS['bbox_pts'] = self.objs_A.get_bbox_pts()
        ALIGN_OBJS['size'] = self.objs_A.size

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            if context.object and len(context.selected_objects) == 1:
                self.handle_obj(context, event)
            elif context.object and len(context.selected_objects) > 1:
                self.handle_multi_obj(context, event)

        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self.remove_handles()
            return {'FINISHED'}

        return {'RUNNING_MODAL'}


classes = (
    PH_OT_move_object,
    PH_OT_rotate_object,
    PH_OT_scale_object,
)

register, unregister = bpy.utils.register_classes_factory(classes)
