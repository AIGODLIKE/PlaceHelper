import bpy
from bpy.types import AddonPreferences, PropertyGroup
from bpy.props import StringProperty, IntProperty, BoolProperty, FloatProperty, EnumProperty, FloatVectorProperty, \
    PointerProperty

from . import __ADDON_NAME__
from .place_tool.gzg import update_gzg_pref


def get_addon_pref():
    """Get the addon preferences"""
    return bpy.context.preferences.addons[__ADDON_NAME__].preferences


class PlaceToolBBoxProps(PropertyGroup):
    offset: FloatProperty(name='Geometry Offset', default=0.00001, min=0.0, max=0.001, step=1, precision=5)
    # display
    width: FloatProperty(name='Width', min=1, max=5, default=2)
    coll_alert: BoolProperty(name='Collision Alert', default=False)
    color: FloatVectorProperty(name='Color', subtype='COLOR', size=4, default=(0.8, 0.8, 0.1, 1.0), max=1, min=0)
    color_alert: FloatVectorProperty(name='Collision', subtype='COLOR', size=4,
                                     default=(1.0, 0.0, 0.0, 1.0), max=1, min=0)


class PlaceToolGizmoProps(PropertyGroup):
    scale_basis: FloatProperty(name='Scale', default=0.5, min=0.1, max=2, update=update_gzg_pref)
    color: FloatVectorProperty(name='Color', subtype='COLOR', size=3, default=(0.48, 0.4, 1), update=update_gzg_pref)
    color_highlight: FloatVectorProperty(name='Highlight', subtype='COLOR', size=3, default=(1, 1, 1),
                                         update=update_gzg_pref)


class PlaceToolProps(PropertyGroup):
    bbox: PointerProperty(type=PlaceToolBBoxProps)
    gz: PointerProperty(name='Gizmo', type=PlaceToolGizmoProps)


class DynamicPlaceToolProps(PropertyGroup):
    use_color: BoolProperty(name='Use Color When Moving', default=True)
    active_color: FloatVectorProperty(name='Active', subtype='COLOR', size=4, default=(1, 0.095, 0.033, 1.0), max=1,
                                      min=0)
    passive_color: FloatVectorProperty(name='Passive', subtype='COLOR', size=4, default=(0.023, 0.233, 0.776, 1.0),
                                       max=1,
                                       min=0)


class Preferences(AddonPreferences):
    bl_idname = __ADDON_NAME__

    tool_type: EnumProperty(name='Tool', items=[('PLACE_TOOL', 'Place', ''), ('TRANSFORM_TOOL', 'Transform', ''),
                                                ('DYNAMIC_PLACE_TOOL', 'Dynamic Place', '')], default='PLACE_TOOL')

    place_tool: PointerProperty(type=PlaceToolProps)
    dynamic_place_tool: PointerProperty(type=DynamicPlaceToolProps)
    #
    use_event_handle_all: BoolProperty(name='Gizmo Handle All Event', default=False)
    debug: BoolProperty(name='Debug', default=False)

    def draw(self, context):
        layout = self.layout

        row_all = layout.split(factor=0.2)

        col = row_all.column(align=True)
        col.prop(self, 'tool_type', expand=True)
        col.separator()
        # col.operator('ph.run_doc')

        col = row_all.column()

        if self.tool_type == 'PLACE_TOOL':
            self.draw_place_tool(context, col)
        elif self.tool_type == 'TRANSFORM_TOOL':
            pass
        elif self.tool_type == 'DYNAMIC_PLACE_TOOL':
            self.draw_dynamic_place_tool(context, col)

        col.prop(self, 'use_event_handle_all')
        # layout.prop(self, 'debug')

    def draw_dynamic_place_tool(self, context, layout):
        col = layout.box().column()
        col.use_property_split = True

        col.label(text='Display')
        tool = self.dynamic_place_tool
        col.active = tool.use_color
        col.prop(tool, 'use_color')
        col.prop(tool, 'active_color')
        col.prop(tool, 'passive_color')

    def draw_place_tool(self, context, layout):
        _layout = layout.column()

        col = _layout.box().column()
        col.use_property_split = True

        col.label(text='Bounding Box', icon='META_CUBE')
        col1 = col.column()
        bbox = self.place_tool.bbox
        col1.prop(bbox, 'offset')

        col2 = col.column(heading='Display')
        col2.prop(bbox, 'coll_alert')
        col2.prop(bbox, 'width')
        col2.prop(bbox, 'color')
        if bbox.coll_alert:
            col2.prop(bbox, 'color_alert')

        col = _layout.box().column()
        col.use_property_split = True

        col.label(text='Gizmos', icon='GIZMO')
        col.separator()

        box = col.box().column()
        box.prop(self.place_tool.gz, 'scale_basis', slider=True)
        box.prop(self.place_tool.gz, 'color')
        box.prop(self.place_tool.gz, 'color_highlight')


class PH_OT_run_doc(bpy.types.Operator):
    bl_idname = 'ph.run_doc'
    bl_label = 'Documentation'

    port: IntProperty(name='Port', default=1145)

    def execute(self, context):
        import os
        import sys
        import subprocess

        # close the server if it's already running
        cmd = f'netstat -ano | findstr {self.port}'
        res = subprocess.run(cmd, shell=True, capture_output=True)
        if res.returncode == 0:
            res = res.stdout.decode().split('\n')
            result = []
            for line in res:
                temp = [i for i in line.split(' ') if i != '']
                if len(temp) > 4:
                    result.append(temp[4])
            for pid in result:
                subprocess.run(f'taskkill /PID {pid} /F', shell=True)

        # create new server
        exec_py = sys.executable
        exec_dir = os.path.join(os.path.dirname(__file__),'docs')
        cmd = f'{exec_py} -m http.server --directory "{exec_dir}" {self.port}'
        subprocess.Popen(cmd, shell=True)
        bpy.ops.wm.url_open(url=f'http://localhost:{self.port}')
        return {'FINISHED'}


def register():
    bpy.utils.register_class(PlaceToolBBoxProps)
    bpy.utils.register_class(PlaceToolGizmoProps)
    bpy.utils.register_class(PlaceToolProps)
    bpy.utils.register_class(DynamicPlaceToolProps)
    bpy.utils.register_class(Preferences)
    bpy.utils.register_class(PH_OT_run_doc)


def unregister():
    bpy.utils.unregister_class(PlaceToolBBoxProps)
    bpy.utils.unregister_class(PlaceToolGizmoProps)
    bpy.utils.unregister_class(PlaceToolProps)
    bpy.utils.unregister_class(DynamicPlaceToolProps)
    bpy.utils.unregister_class(Preferences)
    bpy.utils.unregister_class(PH_OT_run_doc)
