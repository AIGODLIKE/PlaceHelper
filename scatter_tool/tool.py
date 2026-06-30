from pathlib import Path

import bpy
from bpy.props import BoolProperty, FloatProperty, EnumProperty, PointerProperty
from bpy.types import PropertyGroup

from ..utils import EXIT_TO_SELECT_BOX_KEYMAP
from ..icons import draw_random_toggle, draw_random_operator


class ScatterToolProps(PropertyGroup):
    # 笔刷
    radius: FloatProperty(name="Radius", description="Brush radius",
                          default=1.0, min=0.001, soft_max=20.0, subtype="DISTANCE")
    use_random_radius: BoolProperty(name="Random Radius",
                                    description="Randomize the brush radius per stamp between Radius and Max Radius",
                                    default=False)
    radius_max: FloatProperty(name="Max Radius",
                              description="Upper bound of the random brush radius",
                              default=2.0, min=0.001, soft_max=20.0, subtype="DISTANCE")
    use_pressure_radius: BoolProperty(name="Pressure Radius",
                                      description="Use tablet pen pressure to drive brush radius between "
                                                  "Min and Max Radius (shown live at the brush)",
                                      default=False)
    pressure_radius_min: FloatProperty(name="Pressure Min Radius",
                                         description="Brush radius at the lightest pressure",
                                         default=0.2, min=0.001, soft_max=20.0, subtype="DISTANCE")
    pressure_radius_max: FloatProperty(name="Pressure Max Radius",
                                       description="Brush radius at the firmest pressure",
                                       default=2.0, min=0.001, soft_max=20.0, subtype="DISTANCE")
    density: FloatProperty(name="Density",
                           description="Target number of instances per square unit of brush area. "
                                       "The tool keeps trying placements to reach this density, "
                                       "so a large Min Distance no longer starves the result",
                           default=5.0, min=0.01, soft_max=50.0)
    use_random_density: BoolProperty(name="Random Density",
                                     description="Randomize the density per stamp between Density and Max Density",
                                     default=False)
    density_max: FloatProperty(name="Max Density",
                               description="Upper bound of the random density",
                               default=10.0, min=0.01, soft_max=50.0)
    use_pressure_density: BoolProperty(name="Pressure Density",
                                       description="Use tablet pen pressure to drive density: "
                                                   "pressure is mapped between Min and Max Density "
                                                   "(the current pressure is shown at the brush)",
                                       default=False)
    pressure_density_min: FloatProperty(name="Pressure Min Density",
                                        description="Density at the lightest pressure",
                                        default=0.5, min=0.0, soft_max=50.0)
    pressure_density_max: FloatProperty(name="Pressure Max Density",
                                        description="Density at the firmest pressure",
                                        default=10.0, min=0.01, soft_max=50.0)
    min_dist: FloatProperty(name="Min Distance",
                            description="Minimum distance between scattered objects (0 = off)",
                            default=0.0, min=0.0, soft_max=10.0, subtype="DISTANCE")
    use_random_min_dist: BoolProperty(name="Random Spacing",
                                      description="Randomize the spacing between objects, picking a value "
                                                  "between Min Distance and Max Distance for each placement",
                                      default=False)
    min_dist_max: FloatProperty(name="Max Distance",
                                description="Upper bound of the random spacing",
                                default=0.5, min=0.0, soft_max=10.0, subtype="DISTANCE")
    use_stacking: BoolProperty(name="Stacking",
                               description="Allow scattering on top of already scattered objects, "
                                           "stacking them up like a tower",
                               default=False)

    # 防穿插
    avoid_overlap: BoolProperty(name="Avoid Overlap",
                                description="Keep instances apart based on their bounding size",
                                default=False)
    overlap_factor: FloatProperty(name="Overlap Spacing",
                                  description="Multiplier on the combined bounding radius",
                                  default=0.8, min=0.0, soft_max=2.0)

    # 变换随机
    scale_min: FloatProperty(name="Scale Min", default=0.8, min=0.001, soft_max=10.0)
    scale_max: FloatProperty(name="Scale Max", default=1.2, min=0.001, soft_max=10.0)
    use_random_scale: BoolProperty(name="Random Scale",
                                   description="Randomize scale between Scale Min and Scale Max. "
                                               "When off, every instance uses the fixed Scale (Min) value",
                                   default=True)
    use_pressure_scale: BoolProperty(name="Pressure Scale",
                                     description="Use tablet pen pressure to drive scale between "
                                                 "Scale Min and Scale Max (the current pressure is shown at the brush)",
                                     default=False)
    random_scale_axis: BoolProperty(name="Random Per-Axis Scale",
                                    description="Randomize each axis independently for non-uniform (stretched) scaling. "
                                                "When off, scaling is uniform across all axes",
                                    default=False)
    z_offset: FloatProperty(name="Height",
                            description="Distance from the surface along its normal",
                            default=0.0, subtype="DISTANCE")
    use_random_height: BoolProperty(name="Random Height",
                                    description="Randomize the normal height between Height and Max Height",
                                    default=False)
    z_offset_max: FloatProperty(name="Max Height",
                                description="Upper bound of the random normal height",
                                default=0.5, subtype="DISTANCE")
    align_normal: BoolProperty(name="Align to Normal",
                               description="Align scattered objects to the surface normal",
                               default=True)
    random_rotation: BoolProperty(name="Random Rotation",
                                  description="Randomize rotation around the surface normal",
                                  default=True)
    tilt_max: FloatProperty(name="Random Tilt",
                            description="Maximum random tilt away from the normal (degrees)",
                            default=0.0, min=0.0, max=90.0, subtype="ANGLE")

    # 过滤
    limit_to_surface: BoolProperty(name="Limit to Surface",
                                   description="Only place objects where the brush actually overlaps a surface. "
                                               "Samples that fall outside the surface are skipped, so a brush "
                                               "larger than the surface will not scatter objects beyond its edge",
                                   default=True)
    use_slope_limit: BoolProperty(name="Limit Slope",
                                  description="Only scatter on surfaces flatter than the limit",
                                  default=False)
    slope_limit: FloatProperty(name="Max Slope",
                               description="Maximum surface slope angle (degrees)",
                               default=30.0, min=0.0, max=90.0, subtype="ANGLE")
    use_height_limit: BoolProperty(name="Limit Height",
                                   description="Only scatter within a world Z range",
                                   default=False)
    height_min: FloatProperty(name="Height Min", default=0.0, subtype="DISTANCE")
    height_max: FloatProperty(name="Height Max", default=10.0, subtype="DISTANCE")

    # 遮罩
    use_mask: BoolProperty(name="Density Mask",
                           description="Use an image texture (via UV) to control density",
                           default=False)
    mask_image: PointerProperty(name="Mask", type=bpy.types.Image)
    mask_invert: BoolProperty(name="Invert Mask", default=False)

    # 复制方式
    duplicate: EnumProperty(name="Duplicate",
                            items=[("INSTANCE", "Instance", "Create linked instances (share mesh data)"),
                                   ("COPY", "Object", "Create full copies (independent mesh data)")],
                            default="INSTANCE")


class PH_TL_ScatterTool(bpy.types.WorkSpaceTool):
    bl_idname = "ph.scatter_tool"
    bl_space_type = "VIEW_3D"
    bl_context_mode = "OBJECT"
    bl_label = "Scatter"
    bl_icon = Path(__file__).parent.parent.joinpath("icons", "scatter_tool").as_posix()
    bl_keymap = (
        ("object.ph_scatter_brush",
         {"type": "MOUSEMOVE", "value": "ANY"},
         {"properties": []}),
        ("object.ph_scatter_brush",
         {"type": "LEFTMOUSE", "value": "PRESS"},
         {"properties": []}),
    ) + EXIT_TO_SELECT_BOX_KEYMAP

    def draw_settings(context, layout, tool):
        from ..help_overlay import draw_help_toggle
        draw_help_toggle(layout)
        prop = context.scene.scatter_tool

        # 半径：压感 + 随机（范围在折叠弹窗）
        row = layout.row(align=True)
        row.prop(prop, "radius")
        row.prop(prop, "use_pressure_radius", text="", icon="STYLUS_PRESSURE", toggle=True)
        if prop.use_pressure_radius:
            row.popover(panel="PH_PT_ScatterPressureRadius", text="")
        draw_random_toggle(row, prop, "use_random_radius")
        if prop.use_random_radius:
            row.popover(panel="PH_PT_ScatterRandRadius", text="")

        # 密度：压感 + 随机
        row = layout.row(align=True)
        row.prop(prop, "density")
        row.prop(prop, "use_pressure_density", text="", icon="STYLUS_PRESSURE", toggle=True)
        if prop.use_pressure_density:
            row.popover(panel="PH_PT_ScatterPressure", text="")
        draw_random_toggle(row, prop, "use_random_density")
        if prop.use_random_density:
            row.popover(panel="PH_PT_ScatterRandDensity", text="")

        # 最小距离 + 随机
        row = layout.row(align=True)
        row.prop(prop, "min_dist")
        draw_random_toggle(row, prop, "use_random_min_dist")
        if prop.use_random_min_dist:
            row.popover(panel="PH_PT_ScatterRandDist", text="")

        # 缩放 + 压感 + 随机
        row = layout.row(align=True)
        row.prop(prop, "scale_min", text="Scale")
        row.prop(prop, "use_pressure_scale", text="", icon="STYLUS_PRESSURE", toggle=True)
        if prop.use_pressure_scale:
            row.popover(panel="PH_PT_ScatterScale", text="")
        draw_random_toggle(row, prop, "use_random_scale")
        if prop.use_random_scale:
            row.popover(panel="PH_PT_ScatterScale", text="")

        layout.prop(prop, "use_stacking", text="", icon="MOD_ARRAY", toggle=True)
        layout.popover(panel="PH_PT_ScatterSource", text="", icon="OBJECT_DATA")
        layout.popover(panel="PH_PT_ScatterTool", text="", icon="PREFERENCES")
        layout.operator("object.ph_scatter_apply", text="", icon="CHECKMARK")
        layout.operator("object.ph_scatter_clear", text="", icon="TRASH")


class _ScatterPopover:
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"


class PH_PT_ScatterPressureRadius(_ScatterPopover, bpy.types.Panel):
    bl_label = "Pressure Radius"
    bl_idname = "PH_PT_ScatterPressureRadius"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        prop = context.scene.scatter_tool
        col = layout.column(align=True)
        col.prop(prop, "pressure_radius_min", text="Min")
        col.prop(prop, "pressure_radius_max", text="Max")
        layout.label(text="Live pressure is shown at the brush", icon="INFO")


class PH_PT_ScatterRandRadius(_ScatterPopover, bpy.types.Panel):
    bl_label = "Random Radius"
    bl_idname = "PH_PT_ScatterRandRadius"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        prop = context.scene.scatter_tool
        col = layout.column(align=True)
        col.prop(prop, "radius", text="Min")
        col.prop(prop, "radius_max", text="Max")


class PH_PT_ScatterPressure(_ScatterPopover, bpy.types.Panel):
    bl_label = "Pressure Density"
    bl_idname = "PH_PT_ScatterPressure"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        prop = context.scene.scatter_tool
        col = layout.column(align=True)
        col.prop(prop, "pressure_density_min", text="Min")
        col.prop(prop, "pressure_density_max", text="Max")
        layout.label(text="Live pressure is shown at the brush", icon="INFO")


class PH_PT_ScatterRandDensity(_ScatterPopover, bpy.types.Panel):
    bl_label = "Random Density"
    bl_idname = "PH_PT_ScatterRandDensity"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        prop = context.scene.scatter_tool
        col = layout.column(align=True)
        col.prop(prop, "density", text="Min")
        col.prop(prop, "density_max", text="Max")


class PH_PT_ScatterScale(_ScatterPopover, bpy.types.Panel):
    bl_label = "Scale"
    bl_idname = "PH_PT_ScatterScale"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        prop = context.scene.scatter_tool
        col = layout.column(align=True)
        col.prop(prop, "scale_min", text="Min")
        col.prop(prop, "scale_max", text="Max")
        layout.prop(prop, "random_scale_axis")


class PH_PT_ScatterRandDist(_ScatterPopover, bpy.types.Panel):
    bl_label = "Random Spacing"
    bl_idname = "PH_PT_ScatterRandDist"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        prop = context.scene.scatter_tool
        col = layout.column(align=True)
        col.prop(prop, "min_dist", text="Min")
        col.prop(prop, "min_dist_max", text="Max")


class PH_PT_ScatterRandHeight(_ScatterPopover, bpy.types.Panel):
    bl_label = "Random Height"
    bl_idname = "PH_PT_ScatterRandHeight"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        prop = context.scene.scatter_tool
        col = layout.column(align=True)
        col.prop(prop, "z_offset", text="Min")
        col.prop(prop, "z_offset_max", text="Max")


class PH_PT_ScatterSource(_ScatterPopover, bpy.types.Panel):
    bl_label = "Scatter Sources"
    bl_idname = "PH_PT_ScatterSource"

    def draw(self, context):
        layout = self.layout
        from .op import _SOURCE_TYPES
        srcs = [o for o in context.selected_objects if o.type in _SOURCE_TYPES]
        layout.label(text="Source Probability", icon="OBJECT_DATA")
        if srcs:
            col = layout.column(align=True)
            for o in srcs:
                row = col.row(align=True)
                row.label(text=o.name)
                row.prop(o, "ph_scatter_weight", text="")
            draw_random_operator(layout, "object.ph_scatter_random_weights")
        else:
            layout.label(text="Select source objects to set probability", icon="INFO")


class PH_PT_ScatterTool(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_label = "Scatter"
    bl_idname = "PH_PT_ScatterTool"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        prop = context.scene.scatter_tool

        layout.label(text="Brush", icon="BRUSH_DATA")
        layout.prop(prop, "radius")
        layout.prop(prop, "use_pressure_radius")
        if prop.use_pressure_radius:
            col = layout.column(align=True)
            col.prop(prop, "pressure_radius_min", text="Pressure Min")
            col.prop(prop, "pressure_radius_max", text="Max")
        layout.prop(prop, "use_random_radius")
        if prop.use_random_radius:
            layout.prop(prop, "radius_max")
        layout.prop(prop, "density")
        layout.prop(prop, "use_pressure_density")
        if prop.use_pressure_density:
            col = layout.column(align=True)
            col.prop(prop, "pressure_density_min", text="Pressure Min")
            col.prop(prop, "pressure_density_max", text="Max")
        layout.prop(prop, "use_random_density")
        if prop.use_random_density:
            layout.prop(prop, "density_max")
        layout.prop(prop, "min_dist")
        layout.prop(prop, "use_random_min_dist")
        if prop.use_random_min_dist:
            layout.prop(prop, "min_dist_max")
        layout.prop(prop, "avoid_overlap")
        if prop.avoid_overlap:
            layout.prop(prop, "overlap_factor")
        layout.prop(prop, "use_stacking")

        layout.separator()
        layout.label(text="Transform", icon="ORIENTATION_GLOBAL")
        layout.prop(prop, "use_pressure_scale")
        layout.prop(prop, "use_random_scale")
        col = layout.column(align=True)
        if prop.use_random_scale or prop.use_pressure_scale:
            col.prop(prop, "scale_min", text="Scale Min")
            col.prop(prop, "scale_max", text="Scale Max")
            if prop.use_random_scale:
                layout.prop(prop, "random_scale_axis")
        else:
            col.prop(prop, "scale_min", text="Scale")
        layout.prop(prop, "z_offset")
        layout.prop(prop, "use_random_height")
        if prop.use_random_height:
            layout.prop(prop, "z_offset_max")
        layout.prop(prop, "align_normal")
        layout.prop(prop, "random_rotation")
        layout.prop(prop, "tilt_max")

        layout.separator()
        layout.label(text="Filter", icon="FILTER")
        layout.prop(prop, "limit_to_surface")
        layout.prop(prop, "use_slope_limit")
        if prop.use_slope_limit:
            layout.prop(prop, "slope_limit")
        layout.prop(prop, "use_height_limit")
        if prop.use_height_limit:
            col = layout.column(align=True)
            col.prop(prop, "height_min")
            col.prop(prop, "height_max")

        layout.separator()
        layout.label(text="Density Mask", icon="TEXTURE")
        layout.prop(prop, "use_mask")
        if prop.use_mask:
            layout.template_ID(prop, "mask_image", open="image.open")
            layout.prop(prop, "mask_invert")

        layout.separator()
        layout.label(text="Source Probability", icon="OBJECT_DATA")
        from .op import _SOURCE_TYPES
        srcs = [o for o in context.selected_objects if o.type in _SOURCE_TYPES]
        if srcs:
            col = layout.column(align=True)
            col.use_property_split = False
            for o in srcs:
                row = col.row(align=True)
                row.label(text=o.name)
                row.prop(o, "ph_scatter_weight", text="")
            draw_random_operator(layout, "object.ph_scatter_random_weights")
        else:
            layout.label(text="Select source objects to set probability", icon="INFO")

        layout.separator()
        layout.prop(prop, "duplicate")


_POPOVERS = (
    PH_PT_ScatterPressureRadius,
    PH_PT_ScatterRandRadius,
    PH_PT_ScatterPressure,
    PH_PT_ScatterRandDensity,
    PH_PT_ScatterScale,
    PH_PT_ScatterRandDist,
    PH_PT_ScatterRandHeight,
    PH_PT_ScatterSource,
)


def register():
    bpy.utils.register_class(ScatterToolProps)
    for cls in _POPOVERS:
        bpy.utils.register_class(cls)
    bpy.utils.register_class(PH_PT_ScatterTool)
    bpy.types.Scene.scatter_tool = bpy.props.PointerProperty(type=ScatterToolProps)
    bpy.types.Object.ph_scatter_weight = bpy.props.FloatProperty(
        name="Scatter Weight",
        description="Relative probability of this object when scattering multiple sources",
        default=1.0, min=0.0, soft_max=10.0)

    bpy.utils.register_tool(PH_TL_ScatterTool, separator=True)


def unregister():
    bpy.utils.unregister_tool(PH_TL_ScatterTool)
    bpy.utils.unregister_class(PH_PT_ScatterTool)
    for cls in reversed(_POPOVERS):
        bpy.utils.unregister_class(cls)
    bpy.utils.unregister_class(ScatterToolProps)

    del bpy.types.Scene.scatter_tool
    del bpy.types.Object.ph_scatter_weight
