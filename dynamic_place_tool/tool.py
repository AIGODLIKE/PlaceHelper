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
    strength: IntProperty(name='Strength', default=100, min=0, max=500)


class TestTool3(bpy.types.WorkSpaceTool):
    bl_idname = "TEST.test_tool3"
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'OBJECT'
    bl_label = "Test"
    bl_widget = "TEST_GGT_test_group3"
    bl_icon = "ops.transform.transform"
    bl_keymap = "3D View Tool: Select Box"

    def draw_settings(context, layout, tool):
        prop = bpy.context.scene.dynamic_place_tool
        layout.prop(prop, "mode")
        layout.prop(prop, "strength")
        prop = tool.operator_properties('test.dynamic_place')
        layout.prop(prop, "invert")


def register():
    bpy.utils.register_class(DynamicPlaceProps)
    bpy.types.Scene.dynamic_place_tool = bpy.props.PointerProperty(type=DynamicPlaceProps)

    bpy.utils.register_tool(TestTool3, separator=False)


def unregister():
    bpy.utils.unregister_tool(TestTool3)

    bpy.utils.unregister_class(DynamicPlaceProps)
