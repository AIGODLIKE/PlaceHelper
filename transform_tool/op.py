import math
from math import radians
import bpy

from mathutils import Vector, Matrix, Euler, Quaternion
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty, IntProperty, FloatVectorProperty, \
    BoolVectorProperty, PointerProperty
from bpy.app.translations import pgettext_iface as iface_
from bpy_extras.view3d_utils import location_3d_to_region_2d as loc3d_2_r2d

C_OBJECT_TYPE_HAS_BBOX = {'MESH', 'CURVE', 'FONT', 'LATTICE'}

move_view_tool_props = lambda: bpy.context.scene.move_view_tool


class TEST_OT_move_view_object(bpy.types.Operator):
    """Move"""
    bl_idname = 'test.move_view_object'
    bl_label = 'Move View'
    bl_options = {'REGISTER', 'UNDO_GROUPED', 'GRAB_CURSOR', 'BLOCKING'}

    axis: EnumProperty(items=[('X', 'X', 'X'), ('Y', 'Y', 'Y'), ('Z', 'Z', 'Z')])

    offset_display = 0

    ori_mx = {}

    def init_mouse(self, event):
        self.mouse_x = event.mouse_x
        self.mouse_y = event.mouse_y
        self.mouseDX = event.mouse_x
        self.mouseDY = event.mouse_y
        self.startX = event.mouse_x
        self.startY = event.mouse_y

    def init_context_obj(self, context):
        """初始化激活物体"""

        self.ori_mx.clear()
        for obj in context.selected_objects:
            self.ori_mx[obj] = obj.matrix_world.copy()

    def restore_old_obj(self):
        for obj, mx in self.ori_mx.items():
            obj.matrix_world = mx

        self.ori_mx.clear()

    def modal(self, context, event):

        if event.type == 'MOUSEMOVE':
            axis = self.axis.lower()
            r3d = context.space_data.region_3d
            mx = context.object.matrix_world

            self.mouseDX = self.mouseDX - event.mouse_x
            self.mouseDY = self.mouseDY - event.mouse_y

            multiplier = 0.005 if event.shift else 0.01
            offset = multiplier * (self.mouseDX if axis != 'z' else self.mouseDY)

            # 重置
            self.mouseDX = event.mouse_x
            self.mouseDY = event.mouse_y

            if axis == 'z':
                if loc3d_2_r2d(context.region, r3d, mx.translation).y < self.startY:
                    offset *= -1
            else:
                if loc3d_2_r2d(context.region, r3d, mx.translation).x < self.startX:
                    offset *= -1

            # View Moving
            setattr(r3d.view_location, axis, getattr(r3d.view_location, axis) + offset)

            # Set Position

            for obj in context.selected_objects:
                setattr(obj.matrix_world.translation, axis,
                        getattr(obj.matrix_world.translation, axis) + offset)

            self.offset_display += offset
            context.area.header_text_set(f"{iface_('Move')}: {self.offset_display:.4f}")


        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            context.area.header_text_set(None)
            return {'FINISHED'}
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            context.area.header_text_set(None)
            self.restore_old_obj()
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        self.init_mouse(event)
        self.init_context_obj(context)

        self.offset_display = 0
        bpy.context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}


class GP_OT_transform_from_value(bpy.types.Operator):
    bl_idname = 'gp.transform_from_value'
    bl_label = 'Transform From Value'
    # bl_description = ' '
    bl_options = {'REGISTER', 'UNDO', 'GRAB_CURSOR'}

    def update_rotate(self, context):
        if self.negative:
            self.value_angle = radians(-float(self.angle))
        else:
            self.value_angle = radians(float(self.angle))

    def update_scale(self, context):
        if self.setZ:
            self.value_scale = 0.0
            self.setZ = False
        if self.setO:
            self.value_scale = 1.0
            self.setO = False

    pp: FloatVectorProperty()
    matrix_basis: FloatVectorProperty(size=(3, 3), subtype='MATRIX')
    axis: BoolVectorProperty(default=(True, True, True), size=3)
    value_transform: FloatProperty(name='Value', default=0.0, subtype='DISTANCE')

    val_x: FloatProperty(name='X', default=0.0, subtype='DISTANCE')
    val_y: FloatProperty(name='Y', default=0.0, subtype='DISTANCE')
    val_z: FloatProperty(name='Z', default=0.0, subtype='DISTANCE')

    value_angle: FloatProperty(name='Value', default=0.0, unit='ROTATION', subtype='ANGLE')
    value_scale: FloatProperty(name='Value', default=1.0)
    operator: StringProperty(default='DOT')
    negative: BoolProperty(name='-', default=False, update=update_rotate)
    setZ: BoolProperty(name='0', default=False, update=update_scale)
    setO: BoolProperty(name='1', default=False, update=update_scale)
    angle: EnumProperty(
        name='Angle',
        description='Angle Preset',
        items=[
            ('0', '0°', '', '', 0),
            ('45', '45°', '', '', 1),
            ('90', '90°', '', '', 2),
            ('135', '135°', '', '', 3),
            ('180', '180°', '', '', 4),
        ],
        default='0',
        update=update_rotate,
    )

    def execute(self, context):
        tpp = context.scene.tool_settings.transform_pivot_point
        os = context.window.scene.transform_orientation_slots[0].type

        if self.operator in {'DOT', 'TRANSLATION_PLANE', 'TRANSLATION'}:
            if self.operator == 'DOT' or self.operator == 'TRANSLATION_PLANE':
                val_final = [0.0, 0.0, 0.0, 0.0]
                if self.axis[0]:
                    val_final[0] = self.val_x
                if self.axis[1]:
                    val_final[1] = self.val_y
                if self.axis[2]:
                    val_final[2] = self.val_z
            elif self.operator == 'TRANSLATION':
                value = self.value_transform

                val_final = [0.0, 0.0, 0.0, 0.0]
                if self.axis[0]:
                    val_final[0] = value
                if self.axis[1]:
                    val_final[1] = value
                if self.axis[2]:
                    val_final[2] = value

            if tpp == 'INDIVIDUAL_ORIGINS':
                bpy.ops.transform.transform(
                    mode='TRANSLATION',
                    value=val_final,
                )
            else:
                if os == 'NORMAL':
                    bpy.ops.transform.transform(
                        mode='TRANSLATION',
                        value=val_final,
                        orient_matrix=self.matrix_basis,
                        center_override=self.pp,
                    )
                else:
                    bpy.ops.transform.transform(
                        mode='TRANSLATION',
                        value=val_final,
                        center_override=self.pp,
                    )


        elif self.operator == 'ROTATION':
            if tpp == 'INDIVIDUAL_ORIGINS':
                if self.axis[:] == (True, True, True):  # --- VIEW
                    bpy.ops.transform.rotate(
                        value=self.value_angle,
                        orient_type='VIEW',
                        orient_matrix_type='VIEW',
                    )
                else:
                    bpy.ops.transform.rotate(
                        value=self.value_angle,
                        constraint_axis=self.axis[:],
                    )
            else:
                if os == 'NORMAL':
                    if self.axis[:] == (True, True, True):  # --- VIEW
                        bpy.ops.transform.rotate(
                            value=self.value_angle,
                            orient_type='VIEW',
                            orient_matrix_type='VIEW',
                            orient_matrix=self.matrix_basis,
                            center_override=self.pp,
                        )
                    else:
                        bpy.ops.transform.rotate(
                            value=self.value_angle,
                            orient_matrix=self.matrix_basis,
                            constraint_axis=self.axis[:],
                            center_override=self.pp,
                        )
                else:
                    if self.axis[:] == (True, True, True):  # --- VIEW
                        bpy.ops.transform.rotate(
                            value=self.value_angle,
                            orient_type='VIEW',
                            orient_matrix_type='VIEW',
                            center_override=self.pp,
                        )
                    else:
                        bpy.ops.transform.rotate(
                            value=self.value_angle,
                            constraint_axis=self.axis[:],
                            center_override=self.pp,
                        )


        elif self.operator == 'RESIZE':
            if self.axis[:] == (True, True, True):  # --- VIEW
                val_final = (self.value_scale, self.value_scale, self.value_scale, 0)
            else:
                if self.axis[0]:
                    val_final = (self.value_scale, 1.0, 1.0, 0.0)
                elif self.axis[1]:
                    val_final = (1.0, self.value_scale, 1.0, 0.0)
                elif self.axis[2]:
                    val_final = (1.0, 1.0, self.value_scale, 0.0)

            if tpp == 'INDIVIDUAL_ORIGINS':
                bpy.ops.transform.transform(
                    mode='RESIZE',
                    value=val_final,
                    constraint_axis=self.axis[:],
                )
            else:
                if os == 'NORMAL':
                    bpy.ops.transform.transform(
                        mode='RESIZE',
                        value=val_final,
                        orient_matrix=self.matrix_basis,
                        constraint_axis=self.axis[:],
                        center_override=self.pp,
                    )
                else:
                    bpy.ops.transform.transform(
                        mode='RESIZE',
                        value=val_final,
                        constraint_axis=self.axis[:],
                        center_override=self.pp,
                    )

        return {'FINISHED'}

    def invoke(self, context, event):
        # return context.window_manager.invoke_props_popup(self, event)
        return self.execute(context)

    def draw(self, context):
        layout = self.layout
        if self.operator in {'DOT', 'TRANSLATION_PLANE'}:
            l = self.layout
            l.activate_init = True
            l.enabled = True

            row = l.row()
            if self.axis[0]:
                row.prop(self, 'val_x')
            if self.axis[1]:
                row.prop(self, 'val_y')
            if self.axis[2]:
                row.prop(self, 'val_z')


        elif self.operator == 'TRANSLATION':
            tra = self.layout
            tra.prop(self, 'value_transform')

        elif self.operator == 'ROTATION':
            row_all = layout.row(align=True)

            row_a = row_all.row()
            row_a.scale_x = 2
            row_a.activate_init = True
            row_a.prop(self, 'value_angle')

            row_b = row_all.row(align=True)
            row_b.prop(self, 'negative', toggle=True)
            row_b.prop(self, 'angle', expand=True)

        else:
            row_all = layout.row(align=True)

            row_a = row_all.row()
            row_a.scale_x = 2
            row_a.prop(self, 'value_scale')

            row_b = row_all.row(align=True)
            row_b.prop(self, 'setZ', toggle=True)
            row_b.prop(self, 'setO', toggle=True)


class PH_OT_translate(bpy.types.Operator):
    bl_idname = 'ph.translate'
    bl_label = 'Translate'
    bl_description = 'Translate'
    # bl_options = {'REGISTER', 'UNDO'}

    axis: EnumProperty(
        name='Axis',
        description='Axis',
        items=[
            ('X', 'X', '', '', 0),
            ('Y', 'Y', '', '', 1),
            ('Z', 'Z', '', '', 2),
            ('VIEW', 'View', '', '', 3),
        ],
        default='VIEW',
    )
    invert_constraint: BoolProperty(name='Not Moving this Axis', default=False)
    matrix_basis: FloatVectorProperty(size=(4, 4), subtype='MATRIX')
    pp = None

    @staticmethod
    def get_orient_matrix(self):
        mat = self.matrix_basis.copy().to_3x3()
        if self.axis == 'X':
            mat = mat @ Quaternion((0.0, 1.0, 0.0), radians(90)).to_matrix().to_3x3()
        elif self.axis == 'Y':
            mat = mat @ Quaternion((1.0, 0.0, 0.0), radians(90)).to_matrix().to_3x3()
        return mat

    @staticmethod
    def translate(self, context, axis_set, matrix_orient, copy=None):
        tpp = context.scene.tool_settings.transform_pivot_point
        os = context.window.scene.transform_orientation_slots[0].type

        trans_args = {
            'mode': 'TRANSLATION',
            'release_confirm': True,
            'constraint_axis': axis_set,
        }

        if tpp == 'INDIVIDUAL_ORIGINS':
            pass
        else:
            if os == 'NORMAL':
                trans_args['orient_axis'] = self.axis
                trans_args['orient_matrix'] = matrix_orient
                trans_args['center_override'] = self.pp

        if copy is None:
            bpy.ops.transform.transform('INVOKE_DEFAULT', **trans_args)
        else:
            trans_args.pop('mode')
            bpy.ops.object.duplicate_move('INVOKE_DEFAULT',
                                          OBJECT_OT_duplicate={"linked": False if copy != 'COPY' else True,
                                                               "mode": 'TRANSLATION'},
                                          TRANSFORM_OT_translate=trans_args)

    def modal(self, context, event):
        if event.value == 'RELEASE' or event.type in {'RET'}:
            return {'FINISHED'}
        elif event.type in {'ESC', 'RIGHTMOUSE'}:
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        # props = context.preferences.addons['GIZMO_PRO'].preferences
        # settings = context.scene.GP_scene_set

        if self.pp is None:
            self.pp = self.matrix_basis.translation

        if self.axis == 'X':
            axis_set = (True, False, False)
        elif self.axis == 'Y':
            axis_set = (False, True, False)
        elif self.axis == 'Z':
            axis_set = (False, False, True)
        else:
            axis_set = (True, True, True)

        if self.invert_constraint and axis_set != (True, True, True):
            axis_set = (not axis_set[0], not axis_set[1], not axis_set[2])

        if context.mode == 'OBJECT':
            self.translate(self, context, axis_set, self.get_orient_matrix(self),
                           copy=None if not event.shift else context.scene.move_view_tool.duplicate)

        elif context.mode == 'EDIT_MESH':
            if event.shift:
                bpy.ops.mesh.extrude_context_move('INVOKE_DEFAULT',
                                                  MESH_OT_extrude_context={'use_normal_flip': False, 'mirror': False},
                                                  TRANSFORM_OT_translate={'constraint_axis': axis_set,
                                                                          'release_confirm': True})
            else:
                self.translate(self, context, axis_set, self.get_orient_matrix(self), copy=None)

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
    PH_OT_translate
)

register, unregister = bpy.utils.register_classes_factory(classes)
