import math
import bpy

from mathutils import Vector, Matrix, Euler
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty, IntProperty
from bpy_extras.view3d_utils import location_3d_to_region_2d as loc3d_2_r2d
from bpy.app.translations import pgettext_iface as iface_
from ..utils import get_objs_bbox_center

C_OBJECT_TYPE_HAS_BBOX = {'MESH', 'CURVE', 'FONT', 'LATTICE'}


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

            context.scene.frame_set(self.frame)
            bpy.ops.ptcache.bake_all(bake=False)

            if not event.ctrl:
                self.frame += multiplier
            else:
                self.frame -= multiplier

            self.mouseDX = event.mouse_x
            self.mouseDY = event.mouse_y

        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self.free(context)
            return {'FINISHED'}

        return {'RUNNING_MODAL'}

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

    def init_force(self, context):
        self.force = None
        active = context.object
        bpy.ops.object.effector_add(type='FORCE')
        self.force = context.active_object
        self.force.select_set(False)

        if self.axis == 'X':
            euler = Euler((0, math.radians(90), 0))
        elif self.axis == 'Y':
            euler = Euler((math.radians(90), 0, 0))
        else:
            euler = Euler((0, 0, 0))

        self.force.rotation_euler = euler
        self.force.field.strength = -200
        # if TEST_OT_dynamic_place.invert:
        #     self.force.field.strength = -1 * self.force.field.strength
        self.force.matrix_world.translation = get_objs_bbox_center(self.objs)

        context.view_layer.objects.active = active

classes = (
    TEST_OT_dynamic_place,
)

register, unregister = bpy.utils.register_classes_factory(classes)
