from contextlib import contextmanager

import bpy
import gpu
from bpy.types import Gizmo

from .shapes import SHAPES


@contextmanager
def wrap_gpu_state():
    try:
        gpu.state.blend_set('ALPHA')
        yield
    finally:
        gpu.state.blend_set('NONE')


class PH_GT_custom_scale_3d(Gizmo):
    bl_idname = "PH_GT_custom_scale_3d"

    def ensure_gizmo(self):
        if not hasattr(self, "custom_shape"):
            self.custom_shape = self.new_custom_shape('TRIS', SHAPES['gz_shape_SCALE'])

    def draw(self, context):
        with wrap_gpu_state():
            self.ensure_gizmo()
            self.draw_custom_shape(self.custom_shape)

    def draw_select(self, context, select_id):
        self.ensure_gizmo()
        self.draw_custom_shape(self.custom_shape, select_id=select_id)

    def setup(self):
        self.ensure_gizmo()


class PH_GT_custom_rotate_z_3d(Gizmo):
    bl_idname = "PH_GT_custom_rotate_z_3d"

    def ensure_gizmo(self):
        if not hasattr(self, "custom_shape"):
            self.custom_shape = self.new_custom_shape('TRIS', SHAPES['gz_shape_ROTATE'])

    def draw(self, context):
        with wrap_gpu_state():
            self.ensure_gizmo()
            self.draw_custom_shape(self.custom_shape)

    def draw_select(self, context, select_id):
        self.ensure_gizmo()
        self.draw_custom_shape(self.custom_shape, select_id=select_id)

    def setup(self):
        self.ensure_gizmo()


class PH_GT_custom_move_plane_3d(Gizmo):
    def ensure_gizmo(self):
        if not hasattr(self, "custom_shape"):
            self.custom_shape = self.new_custom_shape('TRIS', SHAPES['gz_shape_PLANE'])

    def draw(self, context):
        with wrap_gpu_state():
            self.ensure_gizmo()
            self.draw_custom_shape(self.custom_shape)

    def draw_select(self, context, select_id):
        self.ensure_gizmo()
        self.draw_custom_shape(self.custom_shape, select_id=select_id)

    def setup(self):
        self.use_draw_offset_scale = True
        self.ensure_gizmo()


classes = (
    PH_GT_custom_scale_3d,
    PH_GT_custom_rotate_z_3d,
    PH_GT_custom_move_plane_3d
)

register, unregister = bpy.utils.register_classes_factory(classes)
