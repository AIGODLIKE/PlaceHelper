import bpy
from bpy.props import BoolProperty, IntProperty, FloatProperty, EnumProperty
from bpy.types import PropertyGroup

from .gzg import update_gzg_pref


class DynamicPlaceProps(PropertyGroup):
    mode: EnumProperty(name='Mode',
                       items=[('FORCE', 'Scale', 'Scale'), ('DRAG', 'Drag', 'Drag')],
                       default='DRAG', update=update_gzg_pref)
    location: EnumProperty(name='Location', items=[
        ('CENTER', 'Center', ''),
        ('CURSOR', 'Cursor', ''),
    ], default='CENTER', update=update_gzg_pref)

    # use_gravity: BoolProperty(name='Use Gravity', default=True)
    gravity_strength: FloatProperty(name='Gravity', default=2, min=0, soft_max=10)
    strength: IntProperty(name='Strength', default=100, min=-500, max=500)

    # bake
    bake_animation: BoolProperty(name='Bake Animation', default=False)

    active: EnumProperty(
        name='Active',
        items=[
            ('CONVEX_HULL', 'Convex Hull', '', 'MESH_ICOSPHERE', 0),
            ('SPHERE', 'Sphere', '', 'MESH_UVSPHERE', 1),
            ('BOX', 'Box', '', 'MESH_CUBE', 2),
            ('CYLINDER', 'Cylinder', '', 'MESH_CYLINDER', 3),
            ('CAPSULE', 'Capsule', '', 'MESH_CAPSULE', 4),
            ('CONE', 'Cone', '', 'MESH_CONE', 5),
            ('MESH', 'Mesh', '', 'MESH_DATA', 6),
        ],
        default='CONVEX_HULL'
    )
    passive: EnumProperty(
        name='Passive',
        items=[
            ('CONVEX_HULL', 'Convex Hull', '', 'MESH_ICOSPHERE', 0),
            ('SPHERE', 'Sphere', '', 'MESH_UVSPHERE', 1),
            ('BOX', 'Box', '', 'MESH_CUBE', 2),
            ('CYLINDER', 'Cylinder', '', 'MESH_CYLINDER', 3),
            ('CAPSULE', 'Capsule', '', 'MESH_CAPSULE', 4),
            ('CONE', 'Cone', '', 'MESH_CONE', 5),
            ('MESH', 'Mesh', '', 'MESH_DATA', 6),
        ],
        default='MESH'
    )

    collision_margin: FloatProperty(name='Margin',
                                    min=0, max=1, default=0)

    trace_coll_level: IntProperty(name='Trace Collection Level', min=1, default=2)

    # draw
    draw_active: BoolProperty(name='Draw Active Collision',
                              description='Draw Active Object Collision lines, Performance will decrease',
                              default=False)


class PH_TL_DynamicPlaceTool(bpy.types.WorkSpaceTool):
    bl_idname = "ph.dynamic_place_tool"
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'OBJECT'
    bl_label = "Gravity Dynamic Place"
    bl_widget = "PH_GZG_dynamic_place"
    bl_icon = "ops.transform.transform"
    bl_keymap = "3D View Tool: Select Box"

    def draw_settings(context, layout, tool):
        prop = bpy.context.scene.dynamic_place_tool
        layout.prop(prop, "mode")
        layout.prop(prop, "location")
        if prop.mode == 'FORCE':
            layout.prop(prop, "strength")
        elif prop.mode == 'DRAG':
            layout.prop(prop, "gravity_strength")
        layout.prop(prop, "bake_animation")
        layout.popover(panel="PH_PT_DynamicPlaceToolPanel", text='', icon='PREFERENCES')


class PH_PT_DynamicPlaceTool(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_label = "Dynamic Place"
    bl_idname = "PH_PT_DynamicPlaceToolPanel"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        prop = context.scene.dynamic_place_tool
        layout.label(text='Collisions')
        row = layout.row(align=True)
        row.prop(prop, "active")
        row = layout.row(align=True)
        row.prop(prop, "passive")
        layout.separator()
        row = layout.row(align=True)
        row.prop(prop, "collision_margin")
        row = layout.row(align=True)
        row.prop(prop, "trace_coll_level")
        row = layout.row(align=True)
        row.label(text='Performance')
        row = layout.row(align=True)
        row.prop(prop, 'draw_active')


class PH_OT_set_dynamic_place_mode(bpy.types.Operator):
    bl_idname = 'ph.set_dynamic_place_mode'
    bl_label = 'Mode'

    axis: EnumProperty(name="Axis",
                       items=[("X", "X", ''),
                              ("Y", "Y", ''),
                              ("Z", "Z", '')],
                       default="Z")
    invert_axis: BoolProperty(name="Invert Axis", default=False)

    def invoke(self, context, event):
        def draw(self, context):
            layout = self.layout
            prop = bpy.context.scene.dynamic_place_tool
            layout.prop(prop, "mode")
            layout.prop(prop, "location")
            layout.prop(prop, "strength")
            layout.popover(panel="PH_PT_DynamicPlaceToolPanel", text='', icon='PREFERENCES')

        context.window_manager.popup_menu(draw, title='Dynamic Place', icon='PREFERENCES')
        return {'FINISHED'}


def register():
    bpy.utils.register_class(DynamicPlaceProps)
    bpy.utils.register_class(PH_OT_set_dynamic_place_mode)
    bpy.utils.register_class(PH_PT_DynamicPlaceTool)
    bpy.types.Scene.dynamic_place_tool = bpy.props.PointerProperty(type=DynamicPlaceProps)

    bpy.utils.register_tool(PH_TL_DynamicPlaceTool, separator=False)


def unregister():
    bpy.utils.unregister_tool(PH_TL_DynamicPlaceTool)
    bpy.utils.unregister_class(DynamicPlaceProps)
    bpy.utils.unregister_class(PH_PT_DynamicPlaceTool)
    bpy.utils.unregister_class(PH_OT_set_dynamic_place_mode)

    del bpy.types.Scene.dynamic_place_tool
