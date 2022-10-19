import math
import bpy

from mathutils import Vector, Matrix, Euler
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty, IntProperty
from bpy_extras.view3d_utils import location_3d_to_region_2d as loc3d_2_r2d
from bpy.app.translations import pgettext_iface as iface_
from ..utils import get_objs_bbox_center, get_objs_axis_aligned_bbox
from ..transform_tool.get_gz_matrix import get_matrix

C_OBJECT_TYPE_HAS_BBOX = {'MESH', 'CURVE', 'FONT', 'LATTICE'}

from bpy_extras.view3d_utils import location_3d_to_region_2d


def get_2d_loc(loc, context):
    r3d = context.space_data.region_3d

    x, y = location_3d_to_region_2d(context.region, r3d, loc)
    return x, y


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
                # if self.startX > event.mouse_x:
                #     self.force.matrix_world.translation = self.get_bbox_pos(max=True)
                # else:
                #     self.force.matrix_world.translation = self.get_bbox_pos(max=False)

                self.force.field.strength = context.scene.dynamic_place_tool.strength

        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self.free(context)
            return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def handle_drag_direction(self, context, event):
        from .gzg import GZ_CENTER

        mode = context.scene.dynamic_place_tool.mode

        x, y = get_2d_loc(GZ_CENTER, context)
        value = abs(self.force.field.strength)

        if mode == 'FORCE':
            if self.axis in {'X', 'Y'}:
                self.force.field.strength = - value if self.startX - x > event.mouse_x - x else value
            else:
                self.force.field.strength = - value if self.startY - y > event.mouse_y - y else value
        elif mode == 'DRAG':
            if self.axis in {'X', 'Y'}:
                self.force.field.strength = value if self.startX - x > event.mouse_x - x else - value
            else:
                self.force.field.strength = value if self.startY - y > event.mouse_y - y else - value

    def invoke(self, context, event):
        self.mode = context.scene.dynamic_place_tool.mode

        self.mouseDX = event.mouse_x
        self.mouseDY = event.mouse_y
        self.startX = event.mouse_x
        self.startY = event.mouse_y

        self.init_obj(context)
        self.init_force(context)
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

    def init_obj(self, context):
        self.objs.clear()

        for obj in context.selected_objects:
            if obj.type != 'MESH':
                obj.select_set(False)
            else:
                self.objs.append(obj)

        bpy.ops.rigidbody.object_add()
        context.object.rigid_body.collision_collections[0] = False
        context.object.rigid_body.collision_collections[self.coll_index] = True
        context.object.rigid_body.mesh_source = 'FINAL'

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

    def init_force(self, context):
        self.force = None
        active = context.object
        bpy.ops.object.effector_add(type='FORCE')
        self.force = context.active_object
        self.force.select_set(False)
        # shape
        self.force.field.shape = 'PLANE'
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

        self.force.field.falloff_power = 1

        context.view_layer.objects.active = active


classes = (
    TEST_OT_dynamic_place,
)

register, unregister = bpy.utils.register_classes_factory(classes)
