from contextlib import contextmanager

import bmesh
import bpy
import gpu
from bpy.props import BoolProperty, EnumProperty
from bpy_extras import view3d_utils
from bpy_extras.view3d_utils import location_3d_to_region_2d
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

from ..utils import get_pref
from ..utils.get_gz_matrix import get_matrix
from ..utils.get_position import get_objs_bbox_center


def get_shader(shader_type='3d'):
    shader_3d = shader_2d = gpu.shader.from_builtin('UNIFORM_COLOR')
    shader_debug = gpu.shader.from_builtin('UNIFORM_COLOR')
    shader_tex = gpu.shader.from_builtin('IMAGE')

    if shader_type == '3d':
        return shader_3d
    elif shader_type == '2d':
        return shader_2d
    elif shader_type == 'debug':
        return shader_debug
    elif shader_type == 'tex':
        return shader_tex


C_OBJECT_TYPE_RBD = {'MESH'}

G_DRAW_MESH = {
    'convex_hull': None,
    'pt_mesh': None,
    'tmp_mesh': None,
}


def get_parent_collection_names(collection, parent_names):
    all_coll = list(bpy.context.scene.collection.children_recursive)
    all_coll.append(bpy.context.scene.collection)

    for parent_collection in bpy.data.collections:
        if collection in parent_collection.children_recursive:
            parent_names.append(parent_collection.name)
            get_parent_collection_names(parent_collection, parent_names)
            return


def turn_collection_hierarchy_into_path(obj):
    parent_collection = obj.users_collection[0]
    parent_names = []
    parent_names.append(parent_collection.name)
    get_parent_collection_names(parent_collection, parent_names)
    if len(parent_names) == 1 and parent_names[0] != "Scene Collection":
        parent_names.insert(0, "Scene Collection")

    return parent_names


@contextmanager
def wrap_bgl_restore(width):
    try:
        gpu.state.line_width_set(width)
        gpu.state.point_size_set(8)
        yield  # do the work
    finally:
        gpu.state.line_width_set(1)
        gpu.state.point_size_set(5)


def get_draw_points(context, convex_hull: bool = False):
    obj = context.object
    eval_obj = obj.evaluated_get(context.evaluated_depsgraph_get())
    mesh = eval_obj.to_mesh()
    # get convex hull
    bm = bmesh.new()
    bm.from_mesh(mesh)
    me = bpy.data.meshes.new(f"{obj.name}_draw")

    if convex_hull:
        ch = bmesh.ops.convex_hull(bm, input=bm.verts)
        bmesh.ops.delete(
            bm,
            geom=ch["geom_unused"] + ch["geom_interior"],
            context='VERTS',
        )
    bm.to_mesh(me)

    # get edges points
    points = []
    for edge in me.edges:
        points.append(me.vertices[edge.vertices[0]].co)
        points.append(me.vertices[edge.vertices[1]].co)

    return points, me


def fix_draw_pts(context, pts):
    """修正点的位置"""
    obj = context.object
    matrix = obj.matrix_world
    # 修正点的位置
    fix_pts = []
    for pt in pts:
        fix_pt = matrix @ pt
        fix_pts.append(fix_pt)
    return fix_pts


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


class DynamicBase:
    bl_label = 'Dynamic Place'
    bl_options = {'REGISTER', 'UNDO', 'GRAB_CURSOR', 'BLOCKING'}

    # draw
    draw_pts = None
    draw_handle = None
    tmp_mesh = None

    # rbd setting
    objs = []
    coll_obj = {}
    coll_index = 0

    # shading
    obj_colors = {}
    shading_type = None
    color_type = None

    # cache
    frame_range = 1000
    ori_frame_start = None
    ori_frame_end = None
    ori_frame_current = None

    # pass in
    axis: EnumProperty(name='Axis', items=[('X', 'X', 'X'), ('Y', 'Y', 'Y'), ('Z', 'Z', 'Z'), ('VIEW', 'View', 'View')])
    invert_axis: BoolProperty(name='Invert', default=False)

    def draw_obj_coll_callback_px(self, context):
        if not context.scene.dynamic_place_tool.draw_active: return

        if self.draw_pts is None:
            convex_hull = context.scene.dynamic_place_tool.active == 'CONVEX_HULL'
            self.draw_pts, self.tmp_mesh = get_draw_points(context, convex_hull=convex_hull)

        draw_pts = fix_draw_pts(context, self.draw_pts)

        pref_bbox = get_pref().place_tool.bbox
        width = pref_bbox.width
        color = pref_bbox.color

        with wrap_bgl_restore(width):
            shader_3d = get_shader('3d')
            shader_3d.bind()
            shader_3d.uniform_float("color", color)
            batch = batch_for_shader(shader_3d, 'LINES', {"pos": draw_pts})
            batch.draw(shader_3d)

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

        context.scene.frame_start = self.ori_frame_current
        context.scene.frame_end = self.ori_frame_current + self.frame_range
        context.scene.frame_step = 1

        self.fit_frame_range()
        self.frame = context.scene.frame_start

    def init_rbd_world(self, context):
        self.ori_gravity = context.scene.gravity.copy()
        context.scene.gravity = (0, 0, 0)

        self.ori_point_cache_frame_start = context.scene.rigidbody_world.point_cache.frame_start
        self.ori_point_cache_frame_end = context.scene.rigidbody_world.point_cache.frame_end

        context.scene.rigidbody_world.point_cache.frame_start = self.ori_frame_current
        context.scene.rigidbody_world.point_cache.frame_end = self.ori_frame_current + self.frame_range

    def init_collection_coll(self, context):
        self.coll_obj.clear()
        active_obj = context.active_object
        selected_objects = list(context.selected_objects)

        trace_collection_level = context.scene.dynamic_place_tool.trace_coll_level
        # get all selected object collection
        coll_list = []
        for obj in selected_objects:
            if obj.type not in C_OBJECT_TYPE_RBD: continue
            colls = turn_collection_hierarchy_into_path(obj)
            coll_list.extend(colls[:min(trace_collection_level, len(colls))])

        coll_list = set(coll_list)

        # collision_shape
        passive = context.scene.dynamic_place_tool.passive
        margin = context.scene.dynamic_place_tool.collision_margin
        passive_color = get_pref().dynamic_place_tool.passive_color
        passive_color = tuple(passive_color)
        use_color = get_pref().dynamic_place_tool.use_color

        def set_coll_obj(collection):
            for obj in collection.objects:
                if obj.name not in context.view_layer.objects:
                    continue

                if obj.name in self.obj_colors or obj in self.coll_obj:
                    continue

                if obj.hide_viewport is False:
                    if obj.name in context.view_layer.objects:
                        obj.select_set(True)

                if obj not in selected_objects and obj.type in C_OBJECT_TYPE_RBD and obj.hide_viewport is False:
                    context.view_layer.objects.active = obj

                    if hasattr(obj, 'rigid_body') and obj.rigid_body is not None:
                        self.coll_obj[obj] = obj.rigid_body.type
                    else:
                        self.coll_obj[obj] = 'NONE'
                        bpy.ops.rigidbody.object_add()

                    obj.rigid_body.type = 'PASSIVE'
                    obj.rigid_body.mesh_source = 'FINAL'
                    obj.rigid_body.collision_shape = passive
                    obj.rigid_body.use_margin = True
                    obj.rigid_body.collision_margin = margin

                    # obj color
                    self.obj_colors[obj] = tuple(obj.color)
                    # print('store color: ', obj.name,tuple(obj.color))
                    if use_color:
                        obj.color = passive_color

                obj.select_set(False)

        all_ready_set = []

        for coll in coll_list:
            if coll not in context.view_layer.layer_collection.children:
                continue
            if context.view_layer.layer_collection.children[coll].exclude is True:
                continue
            if coll in all_ready_set:
                continue

            collection = bpy.context.scene.collection if coll == 'Scene Collection' else bpy.data.collections[coll]
            set_coll_obj(collection)
            all_ready_set.append(coll)

            for child_coll in collection.children_recursive:
                if child_coll not in context.view_layer.layer_collection.children:
                    continue
                if context.view_layer.layer_collection.children[child_coll].exclude is True:
                    continue
                if child_coll.name in all_ready_set:
                    continue

                set_coll_obj(child_coll)
                all_ready_set.append(child_coll.name)

        context.view_layer.objects.active = active_obj

    def restore_collection_coll(self, context):
        for obj, rigid_body_type in self.coll_obj.items():
            if rigid_body_type == 'NONE' and obj.hide_viewport is False:
                context.view_layer.objects.active = obj
                bpy.ops.rigidbody.object_remove()
            else:
                obj.rigid_body.type = rigid_body_type

    def init_space_view(self, objs, context):
        self.obj_colors.clear()
        active_color = get_pref().dynamic_place_tool.active_color
        active_color = tuple(active_color)
        use_color = get_pref().dynamic_place_tool.use_color

        # tmp color
        for obj in objs:
            if not getattr(obj, 'color'): continue
            self.obj_colors[obj] = tuple(obj.color)
            if use_color:
                obj.color = active_color
        # tmp shading
        self.shading_type = context.area.spaces[0].shading.type
        self.color_type = context.area.spaces[0].shading.color_type
        # print(self.shading_type, self.color_type)
        # print(context.area.spaces[0].shading.type, context.area.spaces[0].shading.color_type)
        context.area.spaces[0].shading.type = 'SOLID'
        context.area.spaces[0].shading.color_type = 'OBJECT'

    def restore_space_view(self, context):
        # restore color
        for obj, color in self.obj_colors.items():
            # print('restore color', obj.name, obj.color, color)
            obj.color = color
        # restore shading
        context.area.spaces[0].shading.type = self.shading_type
        context.area.spaces[0].shading.color_type = self.color_type
        self.obj_colors.clear()

    def init_obj(self, context):

        # collision_shape
        active = context.scene.dynamic_place_tool.active
        margin = context.scene.dynamic_place_tool.collision_margin

        bpy.ops.rigidbody.object_add()
        context.object.rigid_body.collision_collections[0] = False
        context.object.rigid_body.collision_collections[self.coll_index] = True
        context.object.rigid_body.mesh_source = 'FINAL'
        context.object.rigid_body.collision_shape = active
        context.object.rigid_body.use_margin = True
        context.object.rigid_body.collision_margin = margin

        for obj in self.objs:
            obj.select_set(True)

        bpy.ops.rigidbody.object_settings_copy('INVOKE_DEFAULT')

    def apply_current(self, context):
        if context.scene.dynamic_place_tool.bake_animation:
            bpy.ops.rigidbody.bake_to_keyframes(frame_start=1,
                                                frame_end=self.frame, step=1)
        else:
            bpy.ops.object.visual_transform_apply()

    def show_menu(self, context):
        if context.active_object is None or context.active_object.hide_viewport or not context.active_object.select_get():
            def draw(cls, _context):
                cls.layout.label(text="Please select the active object")

            context.window_manager.popup_menu(draw, title=f'Warning', icon='ERROR')
            return True


class PH_OT_gravity_place(DynamicBase, bpy.types.Operator):
    bl_idname = 'ph.gravity_place'
    bl_label = 'Dynamic Place'

    def set_gravity_vec(self, context):
        location_type = context.scene.dynamic_place_tool.location

        if location_type == 'CURSOR':
            pt_end = context.scene.cursor.location
            pt_start = get_objs_bbox_center(self.objs)
            vec = pt_end - pt_start
        else:
            x, y, z, xD, yD, zD = get_matrix(context)

            axis = self.axis
            invert = self.invert_axis

            if axis == 'X':
                q = x if not invert else xD
            elif axis == 'Y':
                q = y if not invert else yD
            elif axis == 'Z':
                q = z if not invert else zD

            vec = Vector((0, 0, 9.8))
            vec.rotate(q)

        context.scene.gravity = vec

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            self.mouseDX = self.mouseDX - event.mouse_x
            self.mouseDY = self.mouseDY - event.mouse_y

            multiplier = 1 if event.shift else 2

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
        if self.show_menu(context): return {"INTERFACE"}

        self.init_space_view(context.selected_objects, context)

        self.active_obj = context.active_object
        self.mode = context.scene.dynamic_place_tool.mode

        self.active_obj = context.active_object
        self.mode = context.scene.dynamic_place_tool.mode

        self.mouseDX = event.mouse_x
        self.mouseDY = event.mouse_y
        self.startX = event.mouse_x
        self.startY = event.mouse_y

        self.objs.clear()

        for obj in context.selected_objects:
            if obj.type != 'MESH':
                obj.select_set(False)
            elif obj.hide_viewport is True:
                obj.select_set(False)
            else:
                self.objs.append(obj)

        self.init_collection_coll(context)
        self.init_obj(context)
        self.init_frame(context)
        self.init_rbd_world(context)

        self.set_gravity_vec(context)

        context.window_manager.modal_handler_add(self)
        PH_OT_gravity_place.draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_obj_coll_callback_px,
            (context,),
            'WINDOW',
            'POST_VIEW')
        return {'RUNNING_MODAL'}

    def free(self, context):
        # remove draw handler
        if PH_OT_gravity_place.draw_handle:
            bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle, 'WINDOW')
        if self.tmp_mesh:
            bpy.data.meshes.remove(self.tmp_mesh)

        for obj in self.objs:
            obj.select_set(True)

        self.apply_current(context)
        if not context.scene.dynamic_place_tool.bake_animation:
            bpy.ops.rigidbody.objects_remove()
        # restore
        self.restore_frame(context)
        self.restore_rbd_world(context)
        self.restore_collection_coll(context)

        context.view_layer.objects.active = self.active_obj
        self.restore_space_view(context)


class PH_OT_scale_force(DynamicBase, bpy.types.Operator):
    bl_idname = 'ph.scale_force'
    bl_label = 'Dynamic Place'

    force = None

    def invoke(self, context, event):
        if self.show_menu(context): return {"INTERFACE"}

        self.init_space_view(context.selected_objects, context)

        self.active_obj = context.active_object
        self.mode = context.scene.dynamic_place_tool.mode

        self.mouseDX = event.mouse_x
        self.mouseDY = event.mouse_y
        self.startX = event.mouse_x
        self.startY = event.mouse_y

        self.objs.clear()

        for obj in context.selected_objects:
            if obj.type != 'MESH':
                obj.select_set(False)
            elif obj.hide_viewport is True:
                obj.select_set(False)
            else:
                self.objs.append(obj)

        self.init_collection_coll(context)
        self.init_obj(context)
        self.init_force(context)
        self.init_frame(context)
        self.init_rbd_world(context)

        bpy.context.window_manager.modal_handler_add(self)
        PH_OT_scale_force.draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_obj_coll_callback_px,
            (context,),
            'WINDOW',
            'POST_VIEW')
        return {'RUNNING_MODAL'}

    def init_force(self, context):
        self.force = None

        active = context.object
        bpy.ops.object.effector_add(type='FORCE')
        self.force = context.active_object
        self.force.select_set(False)

        self.force.field.shape = 'PLANE'

        location_type = context.scene.dynamic_place_tool.location
        if location_type == 'CURSOR':
            pt_end = get_objs_bbox_center(self.objs)
            pt_start = context.scene.cursor.location
            vec = pt_end - pt_start
            q = Vector((0, 0, 1)).rotation_difference(vec)
            self.force.rotation_quaternion = q
            self.force.location = pt_end
        else:
            mXW, mYW, mZW, mX_d, mY_d, mZ_d = get_matrix(reverse_zD=True)
            if self.axis == 'X':
                self.force.matrix_world = mXW if not self.invert_axis else mX_d
            elif self.axis == 'Y':
                self.force.matrix_world = mYW if not self.invert_axis else mY_d
            elif self.axis == 'Z':
                self.force.matrix_world = mZW if not self.invert_axis else mZ_d
            else:  # all
                self.force.field.shape = 'POINT'

        self.force.matrix_world.translation = get_objs_bbox_center(self.objs)
        self.force.field.strength = context.scene.dynamic_place_tool.strength * -1

        self.force.field.falloff_power = 1
        context.view_layer.objects.active = active

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
            elif self.axis == 'Z':
                self.force.field.strength = - value if self.startY - y > event.mouse_y - y else value

                if invert_z:
                    self.force.field.strength *= -1
            elif self.axis == 'VIEW':
                self.force.field.strength = - value if self.startX - x > event.mouse_x - x else value

    def free(self, context):
        # remove draw handler
        if PH_OT_scale_force.draw_handle:
            bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle, 'WINDOW')
        if self.tmp_mesh:
            bpy.data.meshes.remove(self.tmp_mesh)

        for obj in self.objs:
            obj.select_set(True)

        self.apply_current(context)
        if not context.scene.dynamic_place_tool.bake_animation:
            bpy.ops.rigidbody.objects_remove()
        # restore
        self.restore_frame(context)
        self.restore_rbd_world(context)
        self.restore_collection_coll(context)
        # remove force field
        if self.force:
            bpy.data.objects.remove(self.force)

        context.view_layer.objects.active = self.active_obj
        self.restore_space_view(context)

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            self.mouseDX = self.mouseDX - event.mouse_x
            self.mouseDY = self.mouseDY - event.mouse_y

            multiplier = 1 if event.shift else 2

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


classes = (
    PH_OT_gravity_place,
    PH_OT_scale_force,
)

register, unregister = bpy.utils.register_classes_factory(classes)
