import bpy


class Dynamic:
    axis: bpy.props.StringProperty()


class DynamicMove(bpy.types.Operator, Dynamic):
    bl_idname = 'ph.dynamic_move'
    bl_label = 'Dynamic Move'

    def execute(self, context):
        print(self.bl_idname, self.axis)
        return {"FINISHED"}


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
