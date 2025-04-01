import bpy


class DynamicPlaceProperty(bpy.types.PropertyGroup):
    mode: bpy.props.EnumProperty(name="Force Field Mode",
                                 items=[("CENTER", "By Center", "All Objects Center"),
                                        ("INDIVIDUAL", "By Individual Center", "Objects Individual")],
                                 default="INDIVIDUAL")

    force_field_coefficient_factor: bpy.props.FloatProperty(
        name="Attenuation factor",
        description="Attenuation coefficient of force field movement",
        default=1.4,
        min=0.1,
        max=2,

    )
    min_force_field: bpy.props.FloatProperty(name="Min Force Field", default=10)
    max_force_field: bpy.props.FloatProperty(name="Max Force Field", default=1000)
    transform_tool_show_inset_gizmo: bpy.props.BoolProperty(default=False, options={"SKIP_SAVE"})

    @property
    def is_individual(self):
        return self.mode == "INDIVIDUAL"

    def draw(self, layout):
        layout.label(text="Force Field Mode")
        layout.row(align=True).prop(self, "mode", expand=True)
        row = layout.row(align=True)
        row.prop(self, "force_field_coefficient_factor")
        row.prop(self, "min_force_field")
        row.prop(self, "max_force_field")


def register():
    bpy.utils.register_class(DynamicPlaceProperty)
    bpy.types.Scene.dynamic_place = bpy.props.PointerProperty(type=DynamicPlaceProperty)


def unregister():
    del bpy.types.Scene.dynamic_place
    bpy.utils.unregister_class(DynamicPlaceProperty)
