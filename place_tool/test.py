import bpy
from .op import ray_cast, exclude_ray_cast, mouse_offset
from mathutils import Vector, Matrix


class TEST_OT_test_place(bpy.types.Operator):
    bl_idname = 'test.test_place'
    bl_label = 'Test Place'
    bl_description = 'Test Place'

    move_obj = None
    tg_matrix = None
    tg_obj = None
    tmp_parent = None

    rotate_mode = False

    def modal(self, context, event):
        if event.type == 'LEFTMOUSE':
            if event.value == 'RELEASE':
                self.apply_tmp_parent()
                return {'FINISHED'}

        if event.type == 'MOUSEMOVE':
            if not self.move_obj or not self.tmp_parent:
                return {'PASS_THROUGH'}

            if not event.alt:
                with exclude_ray_cast([self.move_obj]):
                    tg_obj, normal, location, matrix, world_loc = self.get_raycast_res(context, event)
                    if not tg_obj:
                        self.tmp_parent.location = world_loc
                        return {'PASS_THROUGH'}

                    self.tg_obj = tg_obj
                    self.tmp_parent.location = location
                    self.tmp_parent.rotation_mode = 'QUATERNION'
                    self.tmp_parent.rotation_quaternion = normal.to_track_quat('-Z', 'Y')

            else:
                with mouse_offset(self, event) as (offset_x, offset_y):
                    # rotate tmp_parent local z axis
                    pivot = self.tmp_parent.location
                    # obj local z axis
                    z = self.tmp_parent.matrix_world.to_quaternion() @ Vector((0, 0, 1))

                    rot_matrix = (
                            Matrix.Translation(pivot) @
                            Matrix.Diagonal(Vector((1,) * 3)).to_4x4() @
                            Matrix.Rotation(-offset_x, 4, z) @
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

    def create_tmp_parent(self, location, normal):
        self.remove_tmp_parent()

        empty = bpy.data.objects.new('Empty', None)
        empty.name = 'TMP_PARENT'
        empty.empty_display_type = 'PLAIN_AXES'
        empty.empty_display_size = 0

        empty.location = location
        empty.rotation_mode = 'QUATERNION'
        empty.rotation_quaternion = normal.to_track_quat('Z', 'Y')
        bpy.context.scene.collection.objects.link(empty)

        def create_tmp_parent(obj):
            con = obj.constraints.new('CHILD_OF')
            con.name = 'TMP_PARENT'
            con.use_rotation_x = True
            con.use_rotation_y = True
            con.use_rotation_z = True
            con.target = empty
            obj.select_set(False)

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

    def init_move_obj(self, context,event):
        # init move obj
        move_obj, normal, location, matrix, world_loc = self.get_raycast_res(context, event)
        if not move_obj:
            return {'CANCELLED'}
        self.move_obj = move_obj
        # set active object
        context.view_layer.objects.active = self.move_obj
        self.create_tmp_parent(location, normal)

    def invoke(self, context, event):
        self.move_obj = None
        self.tg_obj = None

        self.init_mouse(event)
        # deselect all
        bpy.ops.object.select_all(action='DESELECT')

        self.init_move_obj(context,event)
        # get first raycast object and normal
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


def register():
    bpy.utils.register_class(TEST_OT_test_place)


def unregister():
    bpy.utils.unregister_class(TEST_OT_test_place)
