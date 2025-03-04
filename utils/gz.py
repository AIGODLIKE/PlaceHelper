import bpy
from mathutils import Vector, Color, Euler, Matrix
from dataclasses import dataclass, field
from .obj_bbox import C_OBJECT_TYPE_HAS_BBOX
from ..utils import get_pref


@dataclass
class GizmoInfo:
    # color
    alpha: float = 0.9
    color: Color = (0.48, 0.4, 1)
    alpha_highlight: float = 1
    color_highlight: Color = (1.0, 1.0, 1.0)

    # settings
    use_draw_modal: bool = True
    use_event_handle_all: bool = False
    scale_basis: float = 1
    use_tooltip: bool = True

    def set_up(self, gzg, type):
        self.gz = gzg.gizmos.new(type)
        for key in self.__annotations__.keys():
            self.gz.__setattr__(key, self.__getattribute__(key))

        self.gz.use_event_handle_all = get_pref().use_event_handle_all

        return self.gz
