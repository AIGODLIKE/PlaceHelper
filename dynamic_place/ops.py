import bmesh
import bpy

COLLECTION_NAME = "Particle System Collection"

FRAME_START = 0
FRAME_END = 5000


def get_collection():
    index = bpy.data.collections.find(COLLECTION_NAME)
    if index == -1:
        bpy.data.collections.new(COLLECTION_NAME)
    return bpy.data.collections[index]


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
    bmesh.ops.create_grid(bm, size=1)

    mesh = bpy.data.meshes.new(f"{obj.data.name}_particle_system_mesh")
    bm.to_mesh(mesh)
    particle_obj = bpy.data.objects.new(f"{obj.name}_particle_system_object", mesh)
    collection.objects.link(particle_obj)
    particle_obj.matrix_world = matrix

    context.view_layer.objects.active = particle_obj
    bpy.ops.object.particle_system_add()  # 添加一个粒子系统
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


def create_force_field_object(context, obj, collection) -> bpy.types.Object:
    matrix = obj.matrix_world.copy()

    empty = bpy.data.objects.new(f"{obj.name}_empty_force_field", None)
    collection.objects.link(empty)
    empty.matrix_world = matrix

    context.view_layer.objects.active = empty
    bpy.ops.object.forcefield_toggle()
    empty.field.flow = 10
    empty.field.strength = -100

    empty.select_set(True)
    return empty


def set_frame(context):
    context.scene.frame_current = FRAME_START
    context.scene.frame_start = FRAME_START
    context.scene.frame_end = FRAME_END


class Dynamic:
    axis: bpy.props.StringProperty()

    selected_objects = []
    collision_objects = []
    dynamic_place_system = {}
    particle_system_collection = None

    frame_current = None
    frame_start = None
    frame_end = None

    active_object = None

    def particle_force_field(self, context):
        """添加对应的粒子系统和力场"""
        self.selected_objects = []
        self.dynamic_place_system = {}

        particle_system_collection = self.particle_system_collection = get_collection()

        context.scene.collection.children.link(particle_system_collection)

        for obj in context.selected_objects:
            self.selected_objects.append(obj)

            particle_obj = create_particle_panel(context, obj, particle_system_collection)

            force_field_obj = create_force_field_object(context, obj, particle_system_collection)

            self.dynamic_place_system[obj.name] = {
                "particle_obj": particle_obj.name,
                "force_field_obj": force_field_obj.name,
            }

            obj.hide_set(True)

    def collision(self, context):
        self.collision_objects = []
        for obj in context.scene.objects:
            select = obj not in context.selected_objects
            hide = obj.hide_viewport is False and obj.hide_get() is False
            if select and hide and obj.type == "MESH":
                modifiers_type = [mod.type for mod in obj.modifiers]
                if "COLLISION" not in modifiers_type:
                    context.view_layer.objects.active = obj
                    bpy.ops.object.modifier_add(type='COLLISION')
                    obj.collision.absorption = 0.1
                    obj.collision.damping_factor = 0.1

                    self.collision_objects.append(obj.name)

    def remember_frame(self, context):
        self.frame_current = context.scene.frame_current
        self.frame_start = context.scene.frame_start
        self.frame_end = context.scene.frame_end

    def invoke(self, context, event):
        active = context.view_layer.objects.active
        self.active_object = active.name if active else None
        self.remember_frame(context)
        set_frame(context)
        # self.collision(context)
        self.particle_force_field(context)

        context.view_layer.objects.active = None
        context.scene.update_tag()
        if not context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.value == "RELEASE" and event.type == "LEFTMOUSE":
            return {"FINISHED"}

        return {"RUNNING_MODAL", "PASS_THROUGH"}

    def execute(self, context):
        # TODO()
        # 1.初始化,记录当前场景的时间帧
        # 2.使用粒子和刚体来进行移动。通过空物体力场来对物体进行移动

        print(self.bl_idname, self.axis)
        return {"FINISHED"}

class DynamicMove(bpy.types.Operator, Dynamic):
    bl_idname = 'ph.dynamic_move'
    bl_label = 'Dynamic Move'

    def invoke(self, context, event):
        res = super().invoke(context, event)
        bpy.ops.transform.translate("INVOKE_DEFAULT")
        return res

    def modal(self, context, event):
        if event.value == "RELEASE" and event.type == "LEFTMOUSE":
            return {"FINISHED"}

        return {"RUNNING_MODAL", "PASS_THROUGH"}

class DynamicRotate(bpy.types.Operator, Dynamic):
    bl_idname = 'ph.dynamic_rotate'
    bl_label = 'Dynamic Rotate'

    def execute(self, context):
        return {"FINISHED"}


class DynamicScale(bpy.types.Operator, Dynamic):
    bl_idname = 'ph.dynamic_scale'
    bl_label = 'Dynamic Scale'

    def execute(self, context):
        return {"FINISHED"}


classes = (
    DynamicMove,
    DynamicRotate,
    DynamicScale,
)

register, unregister = bpy.utils.register_classes_factory(classes)
