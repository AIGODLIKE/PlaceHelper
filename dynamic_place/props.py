import bpy


class DynamicPlaceProperty(bpy.types.PropertyGroup):
    mode: bpy.props.EnumProperty(name='Force Field Mode',
                                 items=[('SINGLE', 'Single', 'Single'), ('MULTI', 'Multi', 'Multi')],
                                 default='MULTI')
    force_field_coefficient_factor: bpy.props.FloatProperty(
        name="Force move coefficient",
        description="Attenuation coefficient of force field movement",
        default=.5,
    )
    min_force_field: bpy.props.FloatProperty(name="Min Force", default=-10)
    max_force_field: bpy.props.FloatProperty(name="Max Force", default=1000)


def register():
    bpy.utils.register_class(DynamicPlaceProperty)
    bpy.types.Scene.dynamic_place = bpy.props.PointerProperty(type=DynamicPlaceProperty)


def unregister():
    del bpy.types.Scene.dynamic_place
    bpy.utils.unregister_class(DynamicPlaceProperty)
