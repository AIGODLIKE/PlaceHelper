import bpy
import os
from pathlib import Path

from bpy.types import PropertyGroup
from bpy.props import StringProperty, BoolProperty, IntProperty, FloatProperty, EnumProperty
from bpy.app.translations import pgettext_iface as tips_

from .gzg import update_gzg_pref


class DynamicPlaceProps(PropertyGroup):
    mode: EnumProperty(name='Mode',
                       items=[('GRAVITY', 'Gravity', 'Gravity'), ('FORCE', 'Scale', 'Scale'), ('DRAG', 'Drag', 'Drag')],
                       default='DRAG', update=update_gzg_pref)
    location: EnumProperty(name='Location', items=[
        ('CENTER', 'Center', ''),
        ('CURSOR', 'Cursor', ''),
    ], default='CENTER')
    strength: IntProperty(name='Strength', default=100, min=-500, max=500)

    active: EnumProperty(name='Active', items=[
        ('CONVEX_HULL', 'Convex Hull', ''),
        ('MESH', 'Mesh', ''),
    ], default='CONVEX_HULL')
    passive: EnumProperty(name='Passive', items=[
        ('CONVEX_HULL', 'Convex Hull', ''),
        ('MESH', 'Mesh', ''),
    ], default='MESH')

    collision_margin: FloatProperty(name='Margin',
                                    min=0, max=1, default=0)

    trace_coll_level: IntProperty(name='Trace Collection Level', min=1, default=2)

    # draw
    draw_active: BoolProperty(name='Draw Collision',description='Draw Active Object Collision lines, Performance will decrease' ,default=False)


class PH_TL_DynamicPlaceTool(bpy.types.WorkSpaceTool):
    bl_idname = "ph.dynamic_place_tool"
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'OBJECT'
    bl_label = "Dynamic Place"
    bl_widget = "TEST_GGT_test_group3"
    bl_icon = "ops.transform.transform"
    bl_keymap = "3D View Tool: Select Box"

    def draw_settings(context, layout, tool):
        prop = bpy.context.scene.dynamic_place_tool
        layout.prop(prop, "mode")
        layout.prop(prop, "location")
        layout.prop(prop, "strength")
        layout.popover(panel="PH_PT_DynamicPlaceToolPanel", text = '',icon = 'PREFERENCES')

        # prop = tool.operator_properties('test.dynamic_place')
        # layout.prop(prop, "invert")

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
        layout.label(text = 'Collisions')
        row = layout.row(align = True)
        row.prop(prop, "active", expand = True)
        row = layout.row(align = True)
        row.prop(prop, "passive",expand = True)
        layout.separator()
        row = layout.row(align = True)
        row.prop(prop,"collision_margin")
        row = layout.row(align = True)
        row.prop(prop,"trace_coll_level")
        row = layout.row(align = True)
        row.label(text = 'Performance')
        row = layout.row(align = True)
        row.prop(prop,'draw_active')

def register():
    bpy.utils.register_class(DynamicPlaceProps)
    bpy.utils.register_class(PH_PT_DynamicPlaceTool)
    bpy.types.Scene.dynamic_place_tool = bpy.props.PointerProperty(type=DynamicPlaceProps)

    bpy.utils.register_tool(PH_TL_DynamicPlaceTool, separator=False)


def unregister():
    bpy.utils.unregister_tool(PH_TL_DynamicPlaceTool)
    bpy.utils.unregister_class(DynamicPlaceProps)
    bpy.utils.unregister_class(PH_PT_DynamicPlaceTool)