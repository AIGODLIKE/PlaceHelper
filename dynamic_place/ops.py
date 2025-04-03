import bmesh
import bpy
from mathutils import Vector, Matrix

from ..hub import hub_matrix
from ..utils import get_selected_objects_center_translation

COLLECTION_NAME = "Particle System Collection"

FRAME_START = 0
FRAME_END = 5000
DEFAULT_STRENGTH = 100


def get_collection():
    index = bpy.data.collections.find(COLLECTION_NAME)
    if index == -1:
        return bpy.data.collections.new(COLLECTION_NAME)
    return bpy.data.collections[index]


def clear_collection():
    index = bpy.data.collections.find(COLLECTION_NAME)
    if index != -1:
        bpy.data.collections.remove(bpy.data.collections[index])


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


def check_apply(event) -> bool:
    values = (event.value, event.value_prev)
    return event.type in ("MOUSEMOVE", "INBETWEEN_MOUSEMOVE") and event.type_prev == "LEFTMOUSE" and "RELEASE" in values


def check_cancel(event) -> bool:
    values = (event.value, event.value_prev)
    return event.type == "MOUSEMOVE" and event.type_prev in ("RIGHTMOUSE", "ESC") and "RELEASE" in values


def inverse_proportional(x, k):
    """计算反比例函数 y = k/x 的值"""
    if x == 0:
        raise ValueError("x 不能为0，分母不能为零！")
    return k / x


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

    selected_objects = []
    collision_objects = []
    dynamic_place_system = {}
    particle_system_collection = None

    active_object = None
    last_mouse = None

    mouse_distance = None

    def particle_force_field(self, context):
        """添加对应的粒子系统和力场"""
        prop = context.scene.dynamic_place

        self.selected_objects = []
        self.dynamic_place_system = {}

        particle_system_collection = self.particle_system_collection = get_collection()

        print("particle_system_collection", particle_system_collection)
        context.scene.collection.children.link(particle_system_collection)
        if not prop.is_individual:
            loc = get_selected_objects_center_translation(context)
            matrix = Matrix.Translation(loc)
            force_field_obj = create_force_field_object(context, matrix,
                                                        f"Center_empty_force_field", particle_system_collection)

            collection = bpy.data.collections.new(f"{force_field_obj.name}_effector_collection")
            collection.objects.link(force_field_obj)

        for obj in context.selected_objects:
            if obj.type == "MESH":
                self.selected_objects.append(obj)

                particle_obj = create_particle_panel(context, obj, particle_system_collection)

                if prop.is_individual:
                    force_field_obj = create_force_field_object(context, obj.matrix_world.copy(),
                                                                f"{obj.name}_empty_force_field",
                                                                particle_system_collection)

                    collection = bpy.data.collections.new(
                        f"{particle_obj.name}_{force_field_obj.name}_effector_collection")
                    collection.objects.link(force_field_obj)

                particle_obj.particle_systems.active.settings.effector_weights.collection = collection
                args = {}
                if obj.collision and obj.collision.use:
                    args["collision_use"] = True
                    obj.collision.use = False

                self.dynamic_place_system[obj.name] = {
                    "particle_obj": particle_obj.name,
                    "force_field_obj": force_field_obj.name,
                    "collection": collection.name,
                    **args
                }

                # print("particle_obj", obj.name, self.dynamic_place_system[obj.name])
                obj.hide_set(True)

    def add_collision(self, context):
        """添加碰撞"""
        context.scene.objects.update()
        context.view_layer.objects.update()

        self.collision_objects = []
        for obj in context.scene.objects:
            select = obj not in context.selected_objects
            hide = obj.hide_viewport is False and obj.hide_get() is False
            if select and hide and obj.type == "MESH":
                modifiers_type = [mod.type for mod in obj.modifiers]
                if "COLLISION" not in modifiers_type:
                    context.view_layer.objects.active = obj
                    obj.modifiers.new("COLLISION", "COLLISION")
                    if obj.collision:
                        obj.collision.absorption = 0.1
                        obj.collision.damping_factor = 0.1
                        self.collision_objects.append(obj.name)

    def restore_selected(self, context):
        active_index = context.scene.objects.find(self.active_object)
        if active_index != -1:
            context.view_layer.objects.active = context.scene.objects[active_index]
        for place, value in self.dynamic_place_system.items():
            place_index = context.scene.objects.find(place)
            if place_index != -1:
                place = context.scene.objects[place_index]
                if "collision_use" in value:
                    place.collision.use = True
                place.select_set(True)

    def invoke(self, context, event):
        context.scene.objects.update()
        context.view_layer.objects.update()

        clear_collection()
        bpy.ops.ed.undo_push(message="Push Undo")

        # 1.初始化,记录当前场景的时间帧
        # 2.使用粒子和刚体来进行移动。通过空物体力场来对物体进行移动
        active = context.view_layer.objects.active
        self.active_object = active.name if active else None
        self.mouse_distance = DEFAULT_STRENGTH

        self.remember_frame(context)
        self.remember_tool(context)
        self.add_collision(context)
        self.particle_force_field(context)
        self.last_mouse = Vector((event.mouse_x, event.mouse_y))

        context.view_layer.objects.active = None
        context.scene.update_tag()
        if not context.screen.is_animation_playing:
            bpy.ops.screen.animation_play("INVOKE_DEFAULT", False)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        update_matrix_draw(context)
        self.update_force_field(context, event)

        if check_apply(event):
            self.apply(context)
            self.exit(context)
            return {"FINISHED"}
        elif check_cancel(event):
            self.exit(context)
            return {"FINISHED"}

        return {"RUNNING_MODAL", "PASS_THROUGH"}

    def execute(self, context):
        return {"FINISHED"}

    def exit(self, context):
        context.scene.objects.update()
        context.view_layer.objects.update()
        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_play("INVOKE_DEFAULT", False)

        self.clear_collision(context)
        self.remove_particle()
        clear_collection()

        self.restore_frame(context)
        self.restore_selected(context)
        self.restore_tool(context)
        update_matrix_draw(context, timeout=1)

    def apply(self, context):
        """将粒子物体应用后的物体矩阵copy到原物体"""
        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_play("INVOKE_DEFAULT", False, )

        context.scene.objects.update()
        context.view_layer.objects.update()

        for place_obj, value in self.dynamic_place_system.items():
            particle_obj = value["particle_obj"]

            particle_index = context.view_layer.objects.find(particle_obj)
            place_index = context.view_layer.objects.find(place_obj)
            if particle_index != -1 and place_index != -1:
                particle = context.view_layer.objects[particle_index]
                place = context.view_layer.objects[place_index]
                place.hide_set(False)
                place.update_tag()
                context.view_layer.update()

                for obj in context.selected_objects:
                    obj.select_set(False)
                context.view_layer.objects.active = particle
                particle.select_set(True)
                try:
                    bpy.ops.object.duplicates_make_real("INVOKE_DEFAULT", False)
                    active = context.selected_objects[0]
                    # print("selected_objects", active, res)

                    matrix = active.matrix_world.copy()
                    place.matrix_world = matrix
                    place.update_tag()
                    bpy.data.objects.remove(active)
                except Exception as e:
                    print(e.args)

    def remove_particle(self):
        for place_obj, value in self.dynamic_place_system.items():
            particle_obj = value["particle_obj"]
            force_obj = value["force_field_obj"]
            collection = value["collection"]

            particle_index = bpy.data.objects.find(particle_obj)
            if particle_index != -1:
                particle = bpy.data.objects[particle_index]
                for system in particle.particle_systems:
                    bpy.data.particles.remove(system.settings)

            obj_index = bpy.data.objects.find(force_obj)
            if obj_index != -1:
                bpy.data.objects.remove(bpy.data.objects[obj_index])

            collection_index = bpy.data.collections.find(collection)
            if collection_index != -1:
                bpy.data.collections.remove(bpy.data.collections[collection_index])

    def clear_collision(self, context):
        for name in self.collision_objects:
            index = context.scene.objects.find(name)
            if index != -1:
                obj = context.scene.objects[index]
                context.view_layer.objects.active = obj
                for mod in obj.modifiers:
                    if mod.type == "COLLISION":
                        obj.modifiers.remove(mod)
                obj.update_tag()
            else:
                print("not find collision", name)

        context.scene.objects.update()
        context.view_layer.objects.update()

    def update_force_field(self, context, event):
        """更新力场
        根据每次对比上一次移动鼠标的位置
        """
        prop = context.scene.dynamic_place

        now_mouse = Vector((event.mouse_x, event.mouse_y))
        distance = (now_mouse - self.last_mouse).length

        self.mouse_distance += distance
        strength = min(prop.min_force_field, -self.mouse_distance)
        for place_obj, value in self.dynamic_place_system.items():
            force_obj = value["force_field_obj"]
            force_index = context.scene.objects.find(force_obj)

            if force_index != -1:
                force = context.scene.objects[force_index]
                force.field.strength = strength
            else:
                print("Tips: Not Find this force object ", force_obj)

        if self.mouse_distance > prop.min_force_field:
            value = 10 * prop.force_field_coefficient_factor
            self.mouse_distance -= value
        self.mouse_distance = max(min(self.mouse_distance, prop.max_force_field), prop.min_force_field)
        self.last_mouse = now_mouse

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
