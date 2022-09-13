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
    active_bbox_calc_mode: EnumProperty(name='Active',
                                        items=[('ACCURATE', 'Final', 'Use visual obj bounding box, slower'),
                                               ('FAST', 'Base', 'Use basic mesh bounding box, faster'), ],
                                        default='ACCURATE')

    other_bbox_calc_mode: EnumProperty(name='Others',
                                       items=[('ACCURATE', 'Final', 'Use visual obj bounding box, slower'),
                                              ('FAST', 'Base', 'Use basic mesh bounding box, faster'), ],
                                       default='ACCURATE')

    offset: FloatProperty(name='Geometry Offset', default=0.00001, min=0.0, max=0.001, step=1, precision=5)
    # display
    width: FloatProperty(name='Width', min=1, max=5, default=2)
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


class Preferences(AddonPreferences):
    bl_idname = __ADDON_NAME__

    place_tool: PointerProperty(type=PlaceToolProps)
    debug: BoolProperty(name='Debug', default=False)

    def draw(self, context):
        layout = self.layout

        col = layout.box().column()
        col.use_property_split = True

        col.label(text='Bounding Box', icon='META_CUBE')
        col.separator()

        bbox = self.place_tool.bbox
        box = col.box().column()
        box.label(text='Performance')
        box.prop(bbox, 'active_bbox_calc_mode')
        box.prop(bbox, 'other_bbox_calc_mode')
        box.prop(bbox, 'offset')

        box = col.box().column()
        box.label(text='Display')
        box.prop(bbox, 'width')
        box.prop(bbox, 'color')
        box.prop(bbox, 'color_alert')

        col = layout.box().column()
        col.use_property_split = True

        col.label(text='Gizmos', icon='GIZMO')
        col.separator()

        box = col.box().column()
        box.prop(self.place_tool.gz, 'scale_basis', slider=True)
        box.prop(self.place_tool.gz, 'color')
        box.prop(self.place_tool.gz, 'color_highlight')

        layout.prop(self, 'debug')


def register():
    bpy.utils.register_class(PlaceToolBBoxProps)
    bpy.utils.register_class(PlaceToolGizmoProps)
    bpy.utils.register_class(PlaceToolProps)
    bpy.utils.register_class(Preferences)


def unregister():
    bpy.utils.unregister_class(PlaceToolBBoxProps)
    bpy.utils.unregister_class(PlaceToolGizmoProps)
    bpy.utils.unregister_class(PlaceToolProps)
    bpy.utils.unregister_class(Preferences)
