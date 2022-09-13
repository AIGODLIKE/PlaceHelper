import math
import bpy

from mathutils import Vector, Matrix, Euler
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty, IntProperty
from bpy_extras.view3d_utils import location_3d_to_region_2d as loc3d_2_r2d
from bpy.app.translations import pgettext_iface as iface_

C_OBJECT_TYPE_HAS_BBOX = {'MESH', 'CURVE', 'FONT', 'LATTICE'}

move_view_tool_props = lambda: bpy.context.scene.move_view_tool


class ModalBase:
    old_obj = None  # 原物体
    new_obj = None  # 复制物体

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

        self.new_obj = None
        self.old_obj = context.object

        self.ori_matrix_world = context.object.matrix_world.copy()

    # COPY
    # ----------------------------------------------------------------------------------------------
    def restore_old_obj(self):
        self.old_obj.matrix_world = self.ori_matrix_world
        self.old_obj.select_set(False)

    def copy_obj(self, context):
        if self.new_obj is None:
            self.old_obj = context.object
            self.new_obj = self.old_obj.copy()

            if move_view_tool_props().duplicate == 'COPY' and self.new_obj.data:
                new_data = self.old_obj.data.copy()
                self.new_obj.data = new_data

            context.collection.objects.link(self.new_obj)
            context.view_layer.objects.active = self.new_obj
            self.new_obj.select_set(True)

    def cancel_copy_obj(self, context):
        if context.object is not self.old_obj:
            context.view_layer.objects.active = self.old_obj
            self.old_obj.select_set(True)

        if self.new_obj:
            bpy.data.objects.remove(self.new_obj)
            self.new_obj = None

    def handle_copy_event(self, context, event):
        if event.ctrl:
            self.copy_obj(context)
            self.restore_old_obj()
        else:
            self.cancel_copy_obj(context)
    # MOVE VIEW
    # ---


class TEST_OT_move_view_object(ModalBase, bpy.types.Operator):
    """Move"""
    bl_idname = 'test.move_view_object'
    bl_label = 'Move View'
    bl_options = {'REGISTER', 'UNDO', 'GRAB_CURSOR', 'BLOCKING'}

    axis: EnumProperty(items=[('X', 'X', 'X'), ('Y', 'Y', 'Y'), ('Z', 'Z', 'Z')])

    offset_display = 0

    def modal(self, context, event):
        self.handle_copy_event(context, event)

        if event.type == 'MOUSEMOVE':
            axis = self.axis.lower()
            r3d = context.space_data.region_3d
            mx = context.object.matrix_world

            self.mouseDX = self.mouseDX - event.mouse_x
            self.mouseDY = self.mouseDY - event.mouse_y

            multiplier = 0.005 if event.shift else 0.01
            offset = multiplier * (self.mouseDX if axis != 'z' else self.mouseDY)

            if axis == 'z':
                if loc3d_2_r2d(context.region, r3d, mx.translation).y < self.startY:
                    offset *= -1
            else:
                if loc3d_2_r2d(context.region, r3d, mx.translation).x < self.startX:
                    offset *= -1

            # View Moving
            # check moving direction

            # if event.alt:
            setattr(r3d.view_location, axis, getattr(r3d.view_location, axis) + offset)

            # Set Position

            for obj in context.selected_objects:
                setattr(obj.matrix_world.translation, axis,
                        getattr(obj.matrix_world.translation, axis) + offset)

            self.offset_display += offset
            context.area.header_text_set(f"{iface_('Move')}: {self.offset_display:.4f}")
            # 重置
            self.mouseDX = event.mouse_x
            self.mouseDY = event.mouse_y

        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            context.area.header_text_set(None)
            return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        self.init_mouse(event)
        self.init_context_obj(context)

        self.offset_display = 0
        bpy.context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}


class TEST_OT_rotate_view_object(bpy.types.Operator):
    """Move"""
    bl_idname = 'test.rotate_view_object'
    bl_label = 'Rotate View'
    bl_options = {'REGISTER', 'UNDO', 'GRAB_CURSOR', 'BLOCKING'}

    offset_display = 0

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            self.mouseDX = self.mouseDX - event.mouse_x
            self.mouseDY = self.mouseDY - event.mouse_y

            multiplier = 0.05 if event.shift else 0.1
            offset = multiplier * self.mouseDX

            bpy.ops.view3d.view_orbit('INVOKE_DEFAULT', angle=math.radians(-offset))

            pivot = context.object.matrix_world.translation

            rot_matrix = (
                    Matrix.Translation(pivot) @
                    Matrix.Diagonal(Vector((1,) * 3)).to_4x4() @
                    Matrix.Rotation(math.radians(offset), 4, "Z") @
                    Matrix.Translation(-pivot)
            )

            context.object.matrix_world = rot_matrix @ context.object.matrix_world

            # 重置
            self.mouseDX = event.mouse_x
            self.mouseDY = event.mouse_y

            self.offset_display += offset
            context.area.header_text_set(f"{iface_('Rotate')}: {self.offset_display:.4f}")

        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            context.area.header_text_set(None)
            return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        self.mouseDX = event.mouse_x
        self.mouseDY = event.mouse_y
        self.startX = event.mouse_x
        self.startY = event.mouse_y

        bpy.ops.view3d.view_selected('INVOKE_DEFAULT', use_all_regions=False)
        bpy.ops.view3d.zoom('INVOKE_DEFAULT', delta=-100)

        self.offset_display = 0
        bpy.context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}


classes = (
    TEST_OT_move_view_object,
    TEST_OT_rotate_view_object,
)

register, unregister = bpy.utils.register_classes_factory(classes)
