import time
from enum import Enum

import blf
import bpy
import gpu
from bpy.app.handlers import persistent
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

from ..utils import get_pref, is_contains_chinese

text_handler = None
view_3d_handler = None
area_handler = None
hmatrix_handler = None
text_data = {
    # "identifier": TextHub,
}
view_3d_data = {
    # "identifier": View3DHub,
}
area_data = {
    # "identifier": AreaHub,
}
matrix_data = {
    # "identifier": MatrixHub,
}

UNDO_CLEAR_HUB = [
    "MP7_TOOLS_OT_optimization_mesh",
]


class TextAlign(Enum):
    NONE = -1
    LEFT_UP = 0
    RIGHT_UP = 2
    LEFT_DOWN = 5
    RIGHT_DOWN = 7

    CENTER = 8

    CENTER_UP = 11
    CENTER_DOWN = 10
    CENTER_LEFT = 12
    CENTER_RIGHT = 9


class PublicHub:
    start_time: float  # 开始时间,用作记录,在初始化的时候设置
    timeout: "float|None|bool"  # 超时时间s 就是hub想显示多久 如果设置为None就是一直显示
    area_restrictions: [int]  # 绘制区域限制,如果为None则不限制,里面输入area的hash 是int
    is_alpha_animation: bool  # 是alpha动画
    shaders = {}

    def __init__(
            self,
            identity: str,
            timeout: float = 1,
            area_restrictions: "list|int|None" = None,
            is_alpha_animation: bool = True,
    ):
        self.identifier = identity
        self.timeout = timeout
        self.area_restrictions = area_restrictions
        self.is_alpha_animation = is_alpha_animation and isinstance(timeout, float)
        self.start_time = time.time()
        self.init_shader()
        self.register_timer()
        self.register_handler()

    @property
    def is_timeout(self) -> bool:
        if self.is_persistent:
            return False
        diff_time = time.time() - self.start_time
        return self.timeout < diff_time

    @property
    def is_persistent(self) -> bool:
        """反回此hub是否是持续的
        就是没有超时时间，会一直显示
        """
        return self.timeout is None

    @property
    def is_draw(self) -> bool:
        """在窗口最大化时也进行绘制"""
        screen = bpy.context.screen
        parent_area = None
        if screen.show_fullscreen:
            if screen.name.endswith("-nonnormal"):
                parent_screen = bpy.data.screens.get(screen.name.replace('-nonnormal', ""), None)
                if parent_screen is not None:
                    for area in parent_screen.areas:
                        if area.type == "EMPTY":
                            parent_area = hash(area)
                            break

        if self.area_restrictions is not None:
            area = bpy.context.area
            area_hash = hash(area)
            if isinstance(self.area_restrictions, int):
                if area_hash == self.area_restrictions:
                    return True
                if parent_area is not None and parent_area == self.area_restrictions:
                    return True
            elif isinstance(self.area_restrictions, list):
                if area_hash in self.area_restrictions:
                    return True
                if parent_area is not None and parent_area in self.area_restrictions:
                    return True
            return False

        if self.is_timeout:
            return False
        return True

    @property
    def alpha(self) -> float:
        dt = time.time() - self.start_time
        if not self.is_alpha_animation:
            return 1
        if not self.timeout:
            return 1
        if dt > self.timeout:
            alpha = 0
        else:
            alpha = 1 - dt / self.timeout
        return alpha

    @property
    def text_color(self):
        """偏好设置hub文字颜色"""
        return get_pref().hub_text_color

    @property
    def view_3d_color(self):
        """偏好设置view 3d颜色"""
        return get_pref().hub_3d_color

    @property
    def area_color(self):
        return get_pref().hub_area_color

    @property
    def line_width(self):
        """线宽"""
        return get_pref().hub_line_width

    def register_timer(self):
        if self.timeout is not None:  # 如果有超时时间就添加一个定时器
            if not bpy.app.timers.is_registered(try_update_timer):
                bpy.app.timers.register(try_update_timer, first_interval=0.1, persistent=True)

        if hub_undo_clear not in bpy.app.handlers.undo_post:
            bpy.app.handlers.undo_post.append(hub_undo_clear)

    def register_handler(self):
        pass

    def init_shader(self):
        pass

    def draw(self):
        pass


class TextHub(PublicHub):
    """
    暂时只支持 从上向下绘制 column
    """

    offset_data = {
        # (w,h,scale,text_offset):offset
    }

    @property
    def offset(self) -> Vector:
        """calculate_offset
        通过文本对齐方式和输入的偏移值获取需要偏移的位置"""
        area = bpy.context.area
        aw, ah = area.width, area.height
        key = (aw, ah, self.scale, self.text_offset)

        def calculate_offset():
            # TODO(其它对齐方向还没写完)
            """
            {'FOOTER',
            'ASSET_SHELF_HEADER',
             'NAVIGATION_BAR',
              'UI',
               'TOOL_HEADER',
                'ASSET_SHELF',
                 'HEADER',
                  'CHANNELS', 'HUD', 'TOOLS', 'EXECUTE', 'WINDOW'}
            Returns:

            """
            top = 0
            bottom = 0
            left = 0
            right = 0
            for region in area.regions:
                if region.type in (
                        "TOOL_HEADER",
                        "HEADER"
                ):
                    top += region.height

            if self.text_align == TextAlign.CENTER_DOWN:
                return self.text_offset + Vector((aw / 2 - self.w / 2, self.h))
            elif self.text_align == TextAlign.CENTER_UP:
                return self.text_offset + Vector((aw / 2 - self.w / 2, ah - self.h - top))
            return self.text_offset

        if key in self.offset_data:
            return self.offset_data[key]
        else:
            self.offset_data = {}
            offset = calculate_offset()
            self.offset_data[key] = offset
            return offset

    w: float  # 测量的文本高度
    h: float

    @property
    def scale(self) -> float:
        return get_pref().hub_scale

    def dimensions_texts(self):
        """测量所有文本"""
        w, h = 0, 0

        for info in self.texts:
            text = info.get("text", "Not Find Text")
            size = info.get("font_size", info.get("size", 20))
            font_id = info.get("font_id", 0)

            blf.size(font_id, size * self.scale)

            (width, height) = blf.dimensions(font_id, text)
            info["width"] = width
            info["height"] = height
            h += height * 1.5
            if width > w:
                w = width
        self.w = w
        self.h = h

    def __init__(
            self,
            identifier: str,
            texts: list,

            timeout: "float|None",
            text_offset: Vector,
            text_align: TextAlign,
            area_restrictions: "list|int|None",
            is_alpha_animation: bool,
    ):
        global text_data

        self.offset_data = {}

        text_data[identifier] = self
        self.texts = texts
        self.text_offset = text_offset
        self.text_align = text_align

        self.dimensions_texts()

        super().__init__(identifier, timeout, area_restrictions, is_alpha_animation)

    def draw(self):
        if self.is_timeout:
            text_data.pop(self.identifier)
        elif self.is_draw:
            gpu.state.blend_set("ALPHA")
            with gpu.matrix.push_pop():
                gpu.matrix.translate(self.offset)
                for info in self.texts:
                    text = info.get("text", "Not Find Text")
                    color = (*info.get("color", self.text_color), self.alpha)
                    size = info.get("font_size", info.get("size", 20))
                    font_id = info.get("font_id", 0)

                    blf.position(font_id, 0, 0, 0)
                    blf.size(font_id, size * self.scale)
                    blf.color(font_id, *color)
                    blf.disable(font_id, blf.CLIPPING)

                    height = info.get("height", 0)
                    if is_contains_chinese(text):
                        gpu.matrix.translate(Vector([0, -height * .075]))

                    blf.draw(font_id, str(text))
                    gpu.matrix.translate(Vector((0, -height * 1.5)))

    def register_handler(self):
        global text_handler, text_data

        def draw_text():
            if text_data:
                for text in text_data.copy().values():
                    text.draw()

        if text_handler is None:  # 只管加,不管删 在注销插件时删除 clear_handlers
            text_handler = bpy.types.SpaceView3D.draw_handler_add(draw_text, (), "WINDOW", "POST_PIXEL")


class View3DHub(PublicHub):
    draw_items = None

    def init_shader(self):
        for item in self.draw_items:
            item.bind(self)

    def __init__(
            self,
            identifier: str,
            draw_items,
            timeout: float = 1,
            area_restrictions: "list|int|None" = None,
            is_alpha_animation: bool = True,
    ):
        global view_3d_data

        view_3d_data[identifier] = self

        self.draw_items = draw_items

        super().__init__(identifier, timeout, area_restrictions, is_alpha_animation)

    def draw(self):
        if self.is_timeout:
            view_3d_data.pop(self.identifier)
        elif self.is_draw:
            gpu.state.blend_set("ALPHA")
            if self.is_alpha_animation:
                self.init_shader()

            if self.draw_items:
                for item in self.draw_items:
                    item.draw()

    def register_handler(self):
        global view_3d_handler, view_3d_data

        def draw_3d():
            if view_3d_data:
                for view in view_3d_data.copy().values():
                    view.draw()

        if view_3d_handler is None:  # 只管加,不管删 在注销插件时删除 clear_handlers
            view_3d_handler = bpy.types.SpaceView3D.draw_handler_add(draw_3d, (), "WINDOW", "POST_VIEW")


class AreaHub(PublicHub):
    draw_cache = {}

    def __init__(
            self,
            identifier: str,
            color: tuple,
            offset: int,
            rounded_corner_size: int,
            timeout: float = 1,
            area_restrictions: "list|int|None" = None,
            is_alpha_animation: bool = True,
    ):
        global area_data

        area_data[identifier] = self

        if color:
            self.color = color
        self.offset = offset
        self.rounded_corner_size = rounded_corner_size

        super().__init__(identifier, timeout, area_restrictions, is_alpha_animation)

    def init_shader(self):
        from ..utils.bmesh import from_bmesh_get_draw_info
        area = bpy.context.area
        key = (area.height, area.width)

        color = getattr(self, "color", None)
        if color is not None:
            if len(color) == 3:
                color = (*color, self.alpha)
            elif len(color) == 4:
                ...
            else:
                color = self.area_color
        else:
            color = self.area_color

        self.shaders = {}
        import bmesh
        bm = bmesh.new()
        bm.verts.new((0, 0, 0))
        bm.verts.new((area.width, 0, 0))
        bm.verts.new((area.width, area.height, 0))
        bm.verts.new((0, area.height, 0))
        bm.verts.ensure_lookup_table()

        bm.faces.new(bm.verts)
        bmesh.ops.bevel(bm, geom=bm.verts, offset=self.rounded_corner_size, segments=8, affect="VERTICES",
                        profile=0.5,
                        offset_type="OFFSET")
        bmesh.ops.inset_region(bm, faces=bm.faces, thickness=self.offset, use_boundary=True)
        bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[bm.faces[1]], context="FACES")
        bmesh.ops.triangulate(bm, faces=bm.faces)

        info = from_bmesh_get_draw_info(bm)

        bm.free()

        verts, sequences = info["faces"]["verts"], info["faces"]["sequences"]

        shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        shader.uniform_float("color", color)
        shader.bind()
        batch = batch_for_shader(shader, "TRIS", {"pos": verts}, indices=sequences)
        self.shaders[batch] = shader
        self.draw_cache[key] = key

    def draw(self):
        if self.is_timeout:
            area_data.pop(self.identifier)
        elif self.is_draw:
            gpu.state.blend_set("ALPHA")
            self.init_shader()

            if self.shaders:
                for batch, shader in self.shaders.items():
                    batch.draw(shader)

    def register_handler(self):
        global area_handler, area_data

        def draw_area():
            if area_data:
                for area in area_data.copy().values():
                    area.draw()

        if area_handler is None:  # 只管加,不管删 在注销插件时删除 clear_handlers
            area_handler = bpy.types.SpaceView3D.draw_handler_add(draw_area, (), "WINDOW", "POST_PIXEL")


class MatrixHub(PublicHub):

    def __init__(
            self,
            identifier: str,
            matrices,
            timeout: float,
            area_restrictions: "list|int|None",
            is_alpha_animation: bool,
    ):
        global matrix_data
        matrix_data[identifier] = self

        self.matrices = matrices

        super().__init__(identifier, timeout, area_restrictions, is_alpha_animation)

    def init_shader(self):
        """ math_vis_console\draw.py L:189
            https://extensions.blender.org/add-ons/math-vis-console/
        """
        self.shaders = {}  # {"batch":shader}
        smooth_color_shader = gpu.shader.from_builtin("SMOOTH_COLOR")
        scale = get_pref().hub_scale
        x_p = Vector((scale, 0.0, 0.0))
        y_p = Vector((0.0, scale, 0.0))
        z_p = Vector((0.0, 0.0, scale))
        y_n = x_n = z_n = Vector()

        alpha = self.alpha
        red_dark = (0.5, 0.0, 0.0, alpha)
        red_light = (1.0, 0.0, 0.0, alpha)
        green_dark = (0.0, 0.5, 0.0, alpha)
        green_light = (0.0, 1.0, 0.0, alpha)
        blue_dark = (0.0, 0.0, 0.5, alpha)
        blue_light = (0.0, 0.0, 1.0, alpha)

        coords = []
        colors = []
        for matrix in self.matrices:
            coords.append(matrix @ x_n)
            coords.append(matrix @ x_p)
            colors.extend((red_dark, red_light))
            coords.append(matrix @ y_n)
            coords.append(matrix @ y_p)
            colors.extend((green_dark, green_light))
            coords.append(matrix @ z_n)
            coords.append(matrix @ z_p)
            colors.extend((blue_dark, blue_light))

        batch = batch_for_shader(smooth_color_shader, "LINES", {
            "pos": coords,
            "color": colors
        })
        self.shaders[batch] = smooth_color_shader

    def draw(self):
        if self.is_timeout:
            matrix_data.pop(self.identifier)
        elif self.is_draw:
            gpu.state.blend_set("ALPHA")
            if self.is_alpha_animation:
                self.init_shader()

            if self.matrices:
                for batch, shader in self.shaders.items():
                    batch.draw(shader)

    def register_handler(self):
        global hmatrix_handler, matrix_data

        def draw_matrix():
            if matrix_data:
                for view in matrix_data.copy().values():
                    view.draw()

        if hmatrix_handler is None:  # 只管加,不管删 在注销插件时删除 clear_handlers
            hmatrix_handler = bpy.types.SpaceView3D.draw_handler_add(draw_matrix, (), "WINDOW", "POST_VIEW")


count = 0


def try_update_timer(is_enforce=False):
    global count
    if bpy.app.background:
        return

    if bpy.context.screen:
        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()

    # 部分hub会一直显示,需要做出判断,如果不需要更新了就删除定时器
    is_text = len([text for text in text_data.values() if not text.is_persistent]) == 0
    is_3d = len([view for view in view_3d_data.values() if not view.is_persistent]) == 0
    is_area = len([area for area in area_data.values() if not area.is_persistent]) == 0
    is_matrix = len([matrix for matrix in matrix_data.values() if not matrix.is_persistent]) == 0
    is_not_draw = is_text and is_3d and is_area and is_matrix

    if is_not_draw or is_enforce:
        if bpy.app.timers.is_registered(try_update_timer):
            bpy.app.timers.unregister(try_update_timer)
            return None

    fps = 1 / get_pref().hub_fps
    count += 1
    return fps


@persistent
def hub_undo_clear(context, event):
    """在撤销时清理部分hub
    部分hub在撤销的时候不会删除,所以这里手动删除
    """
    for identifier in UNDO_CLEAR_HUB:
        if identifier in text_data:
            text_data.pop(identifier)
        if identifier in view_3d_data:
            view_3d_data.pop(identifier)
        if identifier in area_data:
            area_data.pop(identifier)
    try_update_timer()


def clear_handlers():
    """
    只有当插件注销时才删除handle
    """
    global text_handler, view_3d_handler, area_handler
    if text_handler:
        bpy.types.SpaceView3D.draw_handler_remove(text_handler, "WINDOW")
        text_handler = None

    if view_3d_handler:
        bpy.types.SpaceView3D.draw_handler_remove(view_3d_handler, "WINDOW")
        view_3d_handler = None

    if area_handler:
        bpy.types.SpaceView3D.draw_handler_remove(area_handler, "WINDOW")
        area_handler = None

    if hub_undo_clear in bpy.app.handlers.undo_post:
        bpy.app.handlers.undo_post.remove(hub_undo_clear)
