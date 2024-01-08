import bpy
from .op import ray_cast, exclude_ray_cast, mouse_offset
from mathutils import Vector, Matrix


class PH_OT_scatter_single(bpy.types.Operator):
    bl_idname = 'ph.scatter_single'
    bl_label = 'Scatter Single'
    bl_options = {'REGISTER', 'UNDO'}

    move_obj = None
    tg_matrix = None
    tg_obj = None
    tmp_parent = None

    rotate_mode = False

    first_target = None

    def modal(self, context, event):

        if event.type == 'LEFTMOUSE':
            if event.value == 'RELEASE':
                self.apply_tmp_parent()
                return {'FINISHED'}

        if event.type == 'MOUSEMOVE':
            if not self.move_obj or not self.tmp_parent:
                return {'PASS_THROUGH'}

            with mouse_offset(self, event) as (offset_x, offset_y):
                # rotate tmp_parent local z axis
                pivot = self.tmp_parent.location
                # obj local z axis
                z = self.tmp_parent.matrix_world.to_quaternion() @ Vector((0, 0, 1))
                ori_scale = self.move_obj.scale.copy()
                # new scale use offset_y
                delta_scale = -offset_x * 0.05 * ori_scale[0]
                new_scale = ori_scale + Vector((delta_scale, delta_scale, delta_scale))

                rot_matrix = (
                        Matrix.Translation(pivot) @
                        Matrix.Diagonal(new_scale).to_4x4() @
                        Matrix.Rotation(-offset_y, 4, z) @
                        Matrix.Translation(-pivot)
                )
                self.tmp_parent.matrix_world = rot_matrix @ self.tmp_parent.matrix_world

        elif event.type in {'ESC', 'RIGHTMOUSE'}:
            self.remove_tmp_parent()

            return {'CANCELLED'}

        elif event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            return {'PASS_THROUGH'}

        return {'RUNNING_MODAL'}

    def remove_tmp_parent(self):
        if self.tmp_parent:
            bpy.data.objects.remove(self.tmp_parent)
            self.tmp_parent = None
        # remove child_of constraint
        for con in self.move_obj.constraints:
            if con.name == 'TMP_PARENT':
                self.move_obj.constraints.remove(con)
                break

    def apply_tmp_parent(self):
        def apply_const(obj):
            obj.select_set(True)
            tmp_mx = obj.matrix_world.copy()
            for con in obj.constraints:
                if con.name == 'TMP_PARENT' and con.type == 'CHILD_OF':
                    obj.constraints.remove(con)

            obj.matrix_world = tmp_mx

        apply_const(self.move_obj)

        self.remove_tmp_parent()

        if hasattr(self, 'origin_obj'):
            bpy.context.view_layer.objects.active = self.origin_obj

    def create_tmp_parent(self, location, normal):
        self.remove_tmp_parent()

        empty = bpy.data.objects.new('Empty', None)
        empty.name = 'TMP_PARENT'
        empty.empty_display_type = 'PLAIN_AXES'
        empty.empty_display_size = 0

        empty.location = location
        empty.rotation_mode = 'QUATERNION'
        empty.rotation_quaternion = normal.to_track_quat('-Z', 'Y')
        bpy.context.scene.collection.objects.link(empty)

        def create_tmp_parent(obj):
            con = obj.constraints.new('CHILD_OF')
            con.name = 'TMP_PARENT'
            con.use_rotation_x = True
            con.use_rotation_y = True
            con.use_rotation_z = True
            con.target = empty
            obj.select_set(False)
            with bpy.context.temp_override(object=obj, constraint=con):
                bpy.ops.constraint.childof_clear_inverse(constraint=con.name)

        create_tmp_parent(self.move_obj)

        self.tmp_parent = empty

    def get_raycast_res(self, context, event):
        # get first raycast object and normal
        result, target_obj, view_point, world_loc, normal, location, matrix = ray_cast(context, event)
        if result:
            return target_obj, normal, location, matrix, world_loc

        return None, None, None, None, world_loc

    def init_mouse(self, event):
        """初始化鼠标"""
        self.mouse_x = event.mouse_x
        self.mouse_y = event.mouse_y
        self.mouseDX = event.mouse_x
        self.mouseDY = event.mouse_y
        # start
        self.startX = event.mouse_x
        self.startY = event.mouse_y

    def init_move_obj(self, context, event):
        # init move obj
        # move_obj, normal, location, matrix, world_loc = self.get_raycast_res(context, event)
        # if not move_obj:
        #     return {'CANCELLED'}
        # self.move_obj = move_obj

        active = context.object
        self.origin_obj = active
        new_obj = active.copy()
        new_obj.data = active.data.copy()

        self.move_obj = new_obj
        # set active object
        context.collection.objects.link(new_obj)
        # context.view_layer.objects.active = self.move_obj
        self.create_tmp_parent(new_obj.location, new_obj.rotation_quaternion.to_axis_angle()[0])
        # clear parent inverse matrix
        self.move_obj.location = (0, 0, 0)

        with exclude_ray_cast([self.move_obj]):
            tg_obj, normal, location, matrix, world_loc = self.get_raycast_res(context, event)
            if not tg_obj:
                self.tmp_parent.location = world_loc
            else:
                self.tmp_parent.location = location
                self.tg_obj = tg_obj
                self.tmp_parent.rotation_mode = 'QUATERNION'
                self.tmp_parent.rotation_quaternion = normal.to_track_quat('Z', 'Y')

    def invoke(self, context, event):
        if context.object is None:
            self.report({'ERROR'}, "没有激活项")
            return {'CANCELLED'}

        self.move_obj = None
        self.tg_obj = None

        self.init_mouse(event)
        # deselect all
        bpy.ops.object.select_all(action='DESELECT')

        self.init_move_obj(context, event)
        # get first raycast object and normal
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


def register():
    bpy.utils.register_class(PH_OT_scatter_single)


def unregister():
    bpy.utils.unregister_class(PH_OT_scatter_single)
