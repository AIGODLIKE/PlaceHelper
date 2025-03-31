import bmesh
import bpy

from ..hub import hub_matrix

COLLECTION_NAME = "Particle System Collection"

FRAME_START = 0
FRAME_END = 5000
DEFAULT_STRENGTH = 100


def get_collection():
    index = bpy.data.collections.find(COLLECTION_NAME)
    if index == -1:
        bpy.data.collections.new(COLLECTION_NAME)
    return bpy.data.collections[index]


def clear_collection():
    index = bpy.data.collections.find(COLLECTION_NAME)
    if index != -1:
        bpy.data.collections.remove(bpy.data.collections[index])


def clear_data():
    """"""
    ...


def set_props(prop, data):
    for key, value in data.items():
        if isinstance(value, dict):
            prop = getattr(prop, key, None)
            if prop:
                set_props(prop, value)
        else:
            setattr(prop, key, value)


def create_particle_panel(context, obj, collection) -> bpy.types.Object:
    """创建一个粒子平面,用于在拖动时通过粒子与力场进行动态碰撞"""
    print("create_particle_panel")
    matrix = obj.matrix_world.copy()

    bm = bmesh.new()
    bmesh.ops.create_grid(bm, size=.001)

    mesh = bpy.data.meshes.new(f"{obj.data.name}_particle_system_mesh")
    bm.to_mesh(mesh)
    particle_obj = bpy.data.objects.new(f"{obj.name}_particle_system_object", mesh)
    collection.objects.link(particle_obj)
    particle_obj.matrix_world = matrix

    context.view_layer.objects.active = particle_obj
    bpy.ops.object.particle_system_add("INVOKE_DEFAULT", False)  # 添加一个粒子系统
    particle = particle_obj.particle_systems.active.settings

    set_props(particle, {
        "count": 1,
        "emit_from": "FACE",
        "frame_start": FRAME_START,
        "frame_end": FRAME_END,
        "lifetime": FRAME_END,
        "render_type": "OBJECT",
        "grid_resolution": 1,
        "instance_object": obj,
        "use_rotation_instance": True,
        "use_scale_instance": True,
        "physics_type": "BOIDS",
        "distribution": "GRID",
        "particle_size": 1,
        "boids": {
            "use_flight": False,
            "use_land": True,
        }
    })
    particle_obj.select_set(False)
    return particle_obj


def create_force_field_object(context, matrix, name, collection) -> bpy.types.Object:
    empty = bpy.data.objects.new(name, None)
    collection.objects.link(empty)
    empty.matrix_world = matrix

    context.view_layer.objects.active = empty
    bpy.ops.object.forcefield_toggle("INVOKE_DEFAULT", False, )
    empty.field.flow = 10
    empty.field.strength = -DEFAULT_STRENGTH

    empty.select_set(True)
    empty.empty_display_size = .00001
    return empty


def create_empty_object(context, matrix, name, collection) -> bpy.types.Object:
    empty = bpy.data.objects.new(name, None)
    collection.objects.link(empty)
    empty.matrix_world = matrix
    return empty


def check_apply(event) -> bool:
    values = (event.value, event.value_prev)
    return event.type in ("MOUSEMOVE", "INBETWEEN_MOUSEMOVE") and event.type_prev == "LEFTMOUSE" and "RELEASE" in values


def check_cancel(event) -> bool:
    types = (event.type, event.type_prev)
    values = (event.value, event.value_prev)
    return event.type == "MOUSEMOVE" and event.type_prev in ("RIGHTMOUSE", "ESC") and "RELEASE" in values


def inverse_proportional(x, k):
    """计算反比例函数 y = k/x 的值"""
    if x == 0:
        raise ValueError("x 不能为0，分母不能为零！")
    return k / x

class SingleForceFieldMode:
    ...


class MultiForceFieldMode:
    ...


class ToolOptions:
    use_transform_data_origin = None
    use_transform_pivot_point_align = None
    use_transform_skip_children = None

    show_object_origins = None
    show_object_origins_all = None

    def remember_tool(self, context):
        tool = context.scene.tool_settings
        space_data = context.space_data

        self.use_transform_data_origin = tool.use_transform_data_origin
        self.use_transform_pivot_point_align = tool.use_transform_pivot_point_align
        self.use_transform_skip_children = tool.use_transform_skip_children
        tool.use_transform_data_origin = False
        tool.use_transform_pivot_point_align = False
        tool.use_transform_skip_children = False

        if hasattr(space_data, "overlay"):
            overlay = space_data.overlay
            self.show_object_origins = overlay.show_object_origins
            self.show_object_origins_all = overlay.show_object_origins_all

            overlay.show_object_origins = False
            overlay.show_object_origins_all = False

    def restore_tool(self, context):
        tool = context.scene.tool_settings
        space_data = context.space_data

        tool.use_transform_data_origin = self.use_transform_data_origin
        tool.use_transform_pivot_point_align = self.use_transform_pivot_point_align
        tool.use_transform_skip_children = self.use_transform_skip_children

        if hasattr(space_data, "overlay"):
            overlay = space_data.overlay

            overlay.show_object_origins = self.show_object_origins
            overlay.show_object_origins_all = self.show_object_origins_all


class FrameOptions:
    frame_current = None
    frame_start = None
    frame_end = None

    def remember_frame(self, context):
        self.frame_current = context.scene.frame_current
        self.frame_start = context.scene.frame_start
        self.frame_end = context.scene.frame_end

        context.scene.frame_current = FRAME_START
        context.scene.frame_start = FRAME_START
        context.scene.frame_end = FRAME_END

    def restore_frame(self, context):
        context.scene.frame_current = self.frame_current
        context.scene.frame_start = self.frame_start
        context.scene.frame_end = self.frame_end


def update_matrix_draw(context, timeout=None):
    matrixs = [obj.matrix_world.copy() for obj in context.selected_objects]
    hub_matrix("Dynamic Place", matrixs,
               timeout=timeout,
               area_restrictions=hash(context.area),
               is_alpha_animation=True,
               )


class Dynamic(ToolOptions, FrameOptions):
    axis: bpy.props.StringProperty()

    move_objects = {}
    collection = None

    active_object = None

    timer = None

    def add_empty(self, context):
        self.move_objects = {}

        collection = self.collection = get_collection()
        context.scene.collection.children.link(collection)

        for obj in context.selected_objects:
            if obj.type == "MESH":
                empty = create_empty_object(context, obj.matrix_world.copy(),
                                            f"{obj.name}_empty",
                                            collection)

                self.move_objects[obj.name] = {
                    "empty": empty.name,
                    "matrix": obj.matrix_world.copy(),
                }

                obj.select_set(False)
                empty.select_set(True)

    def restore_selected(self, context):
        if self.active_object:
            active_index = context.scene.objects.find(self.active_object)
            if active_index != -1:
                context.view_layer.objects.active = context.scene.objects[active_index]
        for obj, value in self.move_objects.items():
            place_index = context.scene.objects.find(obj)
            if place_index != -1:
                obj = context.scene.objects[place_index]
                obj.select_set(True)

    is_run = None

    def invoke(self, context, event):
        self.is_run = False
        context.scene.objects.update()
        context.view_layer.objects.update()

        clear_collection()
        bpy.ops.ed.undo_push(message="Push Undo")

        # 1.初始化,记录当前场景的时间帧
        # 2.使用粒子和刚体来进行移动。通过空物体力场来对物体进行移动
        active = context.view_layer.objects.active
        self.active_object = active.name if active else None

        self.remember_frame(context)
        self.remember_tool(context)
        self.add_empty(context)

        wm = context.window_manager

        self.timer = wm.event_timer_add(1 / 30, window=context.window)

        context.view_layer.objects.active = None
        context.scene.update_tag()
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL", "PASS_THROUGH"}

    def modal(self, context, event):
        print("context,", context, event.type)
        update_matrix_draw(context)
        self.update_matrix(context)

        if check_apply(event):
            print("event check_apply", event.type, event.type_prev, event.value, event.value_prev, flush=True)
            self.apply(context)
            self.exit(context)
            return {"FINISHED"}
        elif check_cancel(event):
            print("event check_cancel", event.type, event.type_prev, event.value, event.value_prev, flush=True)
            self.exit(context)
            return {"FINISHED"}

        return {"RUNNING_MODAL", "PASS_THROUGH"}

    def execute(self, context):
        print(self.bl_idname, self.axis)
        return {"FINISHED"}

    def exit(self, context):
        context.scene.objects.update()
        context.view_layer.objects.update()

        clear_collection()

        self.restore_frame(context)
        self.restore_selected(context)
        self.restore_tool(context)
        update_matrix_draw(context, timeout=1)

        wm = context.window_manager
        wm.event_timer_remove(self.timer)

        print()

    def apply(self, context):
        """将粒子物体应用后的物体矩阵copy到原物体"""
        self.update_matrix(context)

    def update_matrix(self, context):
        deps = context.evaluated_depsgraph_get()
        for place_obj, value in self.move_objects.items():
            empty_obj = value["empty"]

            place_index = context.scene.objects.find(place_obj)
            empty_index = context.scene.objects.find(empty_obj)
            if place_index != -1 and empty_index != -1:
                place = context.scene.objects[place_index]
                empty = context.scene.objects[empty_index]

                res, location, normal, index, obj, mat = context.scene.ray_cast(
                    deps, place.location,
                    direction=place.location - empty.location,
                    distance=99999999)

                if res is False:
                    place.matrix_world.translation = empty.matrix_world.translation
                elif obj == place:
                    off_location = Matrix.Translation(location)

                    res, location, normal, index, obj, mat = context.scene.ray_cast(
                        deps, location,
                        direction=location - empty.location,
                        distance=99999999)
                else:
                    ...

    @property
    def args(self) -> dict:
        args = {}
        if self.axis != "VIEW":
            args["constraint_axis"] = {
                "X": (True, False, False),
                "Y": (False, True, False),
                "Z": (False, False, True),
            }[self.axis]
        return args

    def remove_empty(self, restore_matrix=False):
        for place_obj, value in self.move_objects.items():
            empty_obj = value["empty"]
            matrix = value["matrix"]

            place_index = bpy.data.objects.find(place_obj)
            if place_index != -1 and restore_matrix:
                place = bpy.data.objects[place_index]
                place.matrix_world = matrix

            empty_index = bpy.data.objects.find(empty_obj)
            if empty_index != -1:
                bpy.data.objects.remove(bpy.data.objects[empty_index])


class DynamicMove(bpy.types.Operator, Dynamic):
    bl_idname = 'ph.dynamic_move'
    bl_label = 'Dynamic Move'

    def invoke(self, context, event):
        res = super().invoke(context, event)
        bpy.ops.transform.translate("INVOKE_DEFAULT", False, **self.args)
        return res


class DynamicRotate(bpy.types.Operator, Dynamic):
    bl_idname = 'ph.dynamic_rotate'
    bl_label = 'Dynamic Rotate'

    def invoke(self, context, event):
        res = super().invoke(context, event)
        bpy.ops.transform.rotate("INVOKE_DEFAULT", False, **self.args)
        return res


class DynamicScale(bpy.types.Operator, Dynamic):
    bl_idname = 'ph.dynamic_scale'
    bl_label = 'Dynamic Scale'

    def invoke(self, context, event):
        res = super().invoke(context, event)
        bpy.ops.transform.resize("INVOKE_DEFAULT", False, **self.args)
        return res


classes = (
    DynamicMove,
    DynamicRotate,
    DynamicScale,
)

register, unregister = bpy.utils.register_classes_factory(classes)
