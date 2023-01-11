import math
import bpy

from mathutils import Vector, Matrix, Euler
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty, IntProperty
from bpy_extras import view3d_utils

from ..util.get_position import get_objs_bbox_center, get_objs_axis_aligned_bbox
from ..util.get_gz_matrix import get_matrix

C_OBJECT_TYPE_HAS_BBOX = {'MESH', 'CURVE', 'FONT', 'LATTICE'}

from bpy_extras.view3d_utils import location_3d_to_region_2d


def get_2d_loc(loc, context):
    r3d = context.space_data.region_3d

    x, y = location_3d_to_region_2d(context.region, r3d, loc)
    return x, y


def mouse_ray(context, event):
    """获取鼠标射线"""
    region = context.region
    rv3d = context.region_data
    coord = event.mouse_region_x, event.mouse_region_y
    ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
    ray_direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
    return ray_origin, ray_direction


class TEST_OT_dynamic_place(bpy.types.Operator):
    """Dynamic Place"""
    bl_idname = 'test.dynamic_place'
    bl_label = 'Dynamic Place'
    bl_options = {'REGISTER', 'UNDO', 'GRAB_CURSOR', 'BLOCKING'}

    axis: EnumProperty(name='Axis', items=[('X', 'X', 'X'), ('Y', 'Y', 'Y'), ('Z', 'Z', 'Z')])
    frame: IntProperty(default=1)
    invert: BoolProperty(name='Invert', default=False)

    force = None
    objs = []
    coll_index = 0
    coll_obj = {}

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            self.mouseDX = self.mouseDX - event.mouse_x
            self.mouseDY = self.mouseDY - event.mouse_y

            # if event.mouse_prev_x - event.mouse_x < 0:
            #     if self.force:
            #         self.force.field.strength *= -1

            multiplier = 1 if event.shift else 2

            # self.force.field.strength += offset

            # 重置
            self.mouseDX = event.mouse_x
            self.mouseDY = event.mouse_y

            self.handle_drag_direction(context, event)

            context.scene.frame_set(self.frame)
            bpy.ops.ptcache.bake_all(bake=False)

            if not event.ctrl:
                self.frame += multiplier
            else:
                self.frame -= multiplier

            self.mouseDX = event.mouse_x
            self.mouseDY = event.mouse_y

            if self.mode == 'DRAG':
                self.force.field.strength = context.scene.dynamic_place_tool.strength

        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self.free(context)
            return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def handle_drag_direction(self, context, event):
        from .gzg import GZ_CENTER

        mode = context.scene.dynamic_place_tool.mode
        ray_origin, ray_direction = mouse_ray(context, event)

        # 判断ray_origin在gz的方向
        invert_x = (Vector((1, 0, 0)) + ray_direction)[1] < 0
        invert_y = (Vector((0, 1, 0)) + ray_direction)[0] > 0
        invert_z = (Vector((0, 0, 1)) + ray_direction)[2] < 0

        x, y = get_2d_loc(GZ_CENTER, context)
        value = abs(self.force.field.strength)

        if mode == 'FORCE':
            if self.axis in {'X', 'Y'}:
                self.force.field.strength = - value if self.startX - x > event.mouse_x - x else value

                if invert_x and self.axis == 'X':
                    self.force.field.strength *= -1
                if invert_y and self.axis == 'Y':
                    self.force.field.strength *= -1
            else:
                self.force.field.strength = - value if self.startY - y > event.mouse_y - y else value

                if invert_z:
                    self.force.field.strength *= -1

        elif mode == 'DRAG':
            if self.axis in {'X', 'Y'}:
                self.force.field.strength = value if self.startX - x > event.mouse_x - x else - value
                if invert_x and self.axis == 'X':
                    self.force.field.strength *= -1
                if invert_y and self.axis == 'Y':
                    self.force.field.strength *= -1
            else:
                self.force.field.strength = value if self.startY - y > event.mouse_y - y else - value
                if invert_z:
                    self.force.field.strength *= -1

    def invoke(self, context, event):
        self.mode = context.scene.dynamic_place_tool.mode

        self.mouseDX = event.mouse_x
        self.mouseDY = event.mouse_y
        self.startX = event.mouse_x
        self.startY = event.mouse_y

        self.init_obj(context)
        self.init_collection_coll(context)
        self.init_force(context, event)
        self.init_frame(context)
        self.init_rbd_world(context)

        bpy.context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def free(self, context):
        for obj in self.objs:
            obj.select_set(True)

        bpy.ops.object.visual_transform_apply()
        bpy.ops.rigidbody.objects_remove()
        # restore
        self.restore_frame(context)
        self.restore_rbd_world(context)
        self.restore_collection_coll(context)
        # remove force field
        if self.force:
            bpy.data.objects.remove(self.force)

    def restore_rbd_world(self, context):
        context.scene.gravity = self.ori_gravity

    def restore_frame(self, context):
        context.scene.frame_start = self.ori_frame_start
        context.scene.frame_end = self.ori_frame_end
        context.scene.frame_step = self.ori_frame_step
        context.scene.frame_set(self.ori_frame_current)

        self.fit_frame_range()

    def fit_frame_range(self):
        for area in bpy.context.screen.areas:
            if area.type == 'DOPESHEET_EDITOR':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        with bpy.context.temp_override(area=area, region=region):
                            bpy.ops.action.view_all()
                        break
                break

    def init_frame(self, context):
        self.ori_frame_start = context.scene.frame_start
        self.ori_frame_end = context.scene.frame_end
        self.ori_frame_step = context.scene.frame_step
        self.ori_frame_current = context.scene.frame_current

        context.scene.frame_start = 1
        context.scene.frame_end = 1000
        context.scene.frame_step = 1

        self.fit_frame_range()
        self.frame = 1

    def init_rbd_world(self, context):
        self.ori_gravity = context.scene.gravity
        if self.mode == 'GRAVITY':
            context.scene.gravity = (0, 0, -9.81 if not self.invert else 9.81)
        else:
            context.scene.gravity = (0, 0, 0)

        self.ori_point_cache_frame_start = context.scene.rigidbody_world.point_cache.frame_start
        self.ori_point_cache_frame_end = context.scene.rigidbody_world.point_cache.frame_end

        context.scene.rigidbody_world.point_cache.frame_start = 1
        context.scene.rigidbody_world.point_cache.frame_end = 1000

    def init_collection_coll(self, context):
        self.coll_obj.clear()
        active_obj = context.active_object
        selected_objects = context.selected_objects.copy()
        # collision_shape
        passive = context.scene.dynamic_place_tool.passive

        for obj in context.collection.objects:
            obj.select_set(True)

            if obj not in selected_objects and obj.type == 'MESH':
                context.view_layer.objects.active = obj

                if hasattr(obj, 'rigid_body') and obj.rigid_body is not None:
                    self.coll_obj[obj] = obj.rigid_body.type
                else:
                    self.coll_obj[obj] = 'NONE'
                    bpy.ops.rigidbody.object_add()

                obj.rigid_body.type = 'PASSIVE'
                obj.rigid_body.mesh_source = 'FINAL'
                obj.rigid_body.collision_shape = passive

            obj.select_set(False)

        context.view_layer.objects.active = active_obj

    def restore_collection_coll(self, context):
        for obj, rigid_body_type in self.coll_obj.items():
            if rigid_body_type == 'NONE':
                context.view_layer.objects.active = obj
                bpy.ops.rigidbody.object_remove()
            else:
                obj.rigid_body.type = rigid_body_type

    def init_obj(self, context):
        self.objs.clear()

        for obj in context.selected_objects:
            if obj.type != 'MESH':
                obj.select_set(False)
            else:
                self.objs.append(obj)

        # collision_shape
        active = context.scene.dynamic_place_tool.active

        bpy.ops.rigidbody.object_add()
        context.object.rigid_body.collision_collections[0] = False
        context.object.rigid_body.collision_collections[self.coll_index] = True
        context.object.rigid_body.mesh_source = 'FINAL'
        context.object.rigid_body.collision_shape = active

        bpy.ops.rigidbody.object_settings_copy('INVOKE_DEFAULT')

    def get_bbox_pos(self, max=False):
        min_x, min_y, min_z, max_x, max_y, max_z = get_objs_axis_aligned_bbox(self.objs)

        pos = get_objs_bbox_center(self.objs)
        if self.axis == 'X':
            pos.x = min_x if not max else max_x
        elif self.axis == 'Y':
            pos.y = min_y if not max else max_y
        elif self.axis == 'Z':
            pos.z = min_z if not max else max_z

        return pos

    def init_force(self, context, event):
        self.force = None
        active = context.object
        bpy.ops.object.effector_add(type='FORCE')
        self.force = context.active_object
        self.force.select_set(False)
        # shape
        self.force.field.shape = 'PLANE'
        # location
        location_type = context.scene.dynamic_place_tool.location
        if location_type == 'CENTER':
            mXW, mYW, mZW, mX_d, mY_d, mZ_d = get_matrix()

            if self.axis == 'X':
                self.force.matrix_world = mXW
            elif self.axis == 'Y':
                self.force.matrix_world = mYW
            elif self.axis == 'Z':
                self.force.matrix_world = mZW

            if self.mode == 'DRAG':
                self.force.matrix_world.translation = self.get_bbox_pos(max=True)
                self.force.field.strength = 0
            else:
                self.force.matrix_world.translation = get_objs_bbox_center(self.objs)
                self.force.field.strength = context.scene.dynamic_place_tool.strength * -1
        else:  # 'CURSOR'
            self.force.matrix_world.translation = context.scene.cursor.location

        self.force.field.falloff_power = 1

        context.view_layer.objects.active = active


classes = (
    TEST_OT_dynamic_place,
)

register, unregister = bpy.utils.register_classes_factory(classes)
