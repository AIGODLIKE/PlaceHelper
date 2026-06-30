import math
import random

import bpy
import gpu
from bpy.app.handlers import persistent
from bpy.app.translations import pgettext_iface as _iface
from gpu_extras.batch import batch_for_shader
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.interpolate import poly_3d_calc

from ..utils import get_pref
from ..utils.raycast import mouse_ray

SCATTER_COLL_NAME = "PH_Scatter"
# 用自定义属性标记散布集合，避免依赖集合名字（用户可能重命名）。
SCATTER_COLL_ID = "ph_is_scatter"

# 全局单例标记，避免工具 keymap 在 MOUSEMOVE 上重复启动多个模态
_INSTANCE_RUNNING = False


def find_scatter_collection():
    """按自定义属性标记查找散布集合；找不到时回退到旧版命名（不写入数据）。"""
    for coll in bpy.data.collections:
        if coll.get(SCATTER_COLL_ID):
            return coll
    return bpy.data.collections.get(SCATTER_COLL_NAME)

scatter_tool_props = lambda: bpy.context.scene.scatter_tool

# 可作为散布源的物体类型。
# 除网格类外，新增 EMPTY（集合实例/空物体）、LIGHT（灯光）等，
# 这些类型 .copy() 同样有效，INSTANCE 模式会共享其数据（集合实例仍指向同一集合）。
_SOURCE_TYPES = {
    "MESH", "CURVE", "SURFACE", "FONT", "META",
    "EMPTY", "LIGHT", "LIGHT_PROBE", "VOLUME",
    "GPENCIL", "GREASEPENCIL", "CURVES",
}


# 几何辅助
# ----------------------------------------------------------------------

def tangent_basis(normal: Vector):
    n = normal.normalized()
    up = Vector((0.0, 0.0, 1.0))
    if abs(n.dot(up)) > 0.999:
        up = Vector((1.0, 0.0, 0.0))
    t1 = n.cross(up).normalized()
    t2 = n.cross(t1).normalized()
    return t1, t2


def circle_points(center: Vector, normal: Vector, radius: float, segments: int = 48):
    t1, t2 = tangent_basis(normal)
    pts = []
    prev = None
    for i in range(segments + 1):
        a = 2.0 * math.pi * i / segments
        p = center + (math.cos(a) * t1 + math.sin(a) * t2) * radius
        if prev is not None:
            pts.append(prev)
            pts.append(p)
        prev = p
    return pts


def _deferred_undo_push():
    """在模态事件循环之外推送撤销点，避免释放运行中算子的内存。"""
    try:
        bpy.ops.ed.undo_push(message="Scatter Brush")
    except Exception:
        pass
    return None  # 只执行一次


def active_tool_is_scatter(context) -> bool:
    try:
        tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
        return bool(tool) and tool.idname == "ph.scatter_tool"
    except Exception:
        return True


# 模块级笔刷绘制状态与句柄。
# 绘制回调只读取该字典，绝不引用算子实例，避免算子被释放后产生
# "StructRNA has been removed" 的孤儿绘制崩溃。
_DRAW = {
    "active": False,
    "center": None,
    "normal": None,
    "radius": 1.0,
    "color": (0.2, 0.7, 1.0, 0.9),
    "width": 2.0,
    "pressure": 1.0,
    "show_pressure": False,
}
_draw_handle = None
_draw_handle_px = None


def _draw_brush_callback():
    try:
        if not _DRAW.get("active"):
            return
        center = _DRAW.get("center")
        normal = _DRAW.get("normal")
        if center is None or normal is None:
            return
        pts = circle_points(center, normal, _DRAW.get("radius", 1.0))
        if not pts:
            return
        gpu.state.line_width_set(_DRAW.get("width", 2.0))
        gpu.state.blend_set("ALPHA")
        shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        shader.bind()
        shader.uniform_float("color", _DRAW.get("color", (0.2, 0.7, 1.0, 0.9)))
        batch = batch_for_shader(shader, "LINES", {"pos": pts})
        batch.draw(shader)
        gpu.state.line_width_set(1.0)
        gpu.state.blend_set("NONE")
    except Exception:
        pass


def _draw_pressure_callback():
    """屏幕空间绘制：在笔刷处显示当前实时笔压百分比。"""
    try:
        if not _DRAW.get("active") or not _DRAW.get("show_pressure"):
            return
        center = _DRAW.get("center")
        if center is None:
            return
        from bpy_extras import view3d_utils
        import blf
        region = bpy.context.region
        rv3d = bpy.context.region_data
        if region is None or rv3d is None:
            return
        co = view3d_utils.location_3d_to_region_2d(region, rv3d, center)
        if co is None:
            return
        ui = max(bpy.context.preferences.system.ui_scale, 0.5)
        font_id = 0
        p = _DRAW.get("pressure", 1.0)
        text = "%s %d%%" % (_iface("Pressure"), int(round(p * 100)))
        blf.enable(font_id, blf.SHADOW)
        blf.shadow(font_id, 3, 0.0, 0.0, 0.0, 0.85)
        blf.shadow_offset(font_id, 1, -1)
        blf.size(font_id, round(13 * ui))
        blf.color(font_id, 1.0, 0.85, 0.2, 0.95)
        blf.position(font_id, co.x + round(14 * ui), co.y + round(14 * ui), 0.0)
        blf.draw(font_id, text)
        blf.disable(font_id, blf.SHADOW)
    except Exception:
        pass


def _add_brush_draw():
    """按需注册笔刷绘制与文件加载复位处理器（仅在工具激活进入模态时）。"""
    global _draw_handle, _draw_handle_px
    if _draw_handle is None:
        _draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw_brush_callback, (), "WINDOW", "POST_VIEW")
    if _draw_handle_px is None:
        _draw_handle_px = bpy.types.SpaceView3D.draw_handler_add(
            _draw_pressure_callback, (), "WINDOW", "POST_PIXEL")
    if _reset_scatter_state not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_reset_scatter_state)


def _remove_brush_draw():
    """退出模态/卸载时移除绘制与文件加载处理器，不让其常驻。"""
    global _draw_handle, _draw_handle_px
    if _draw_handle is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, "WINDOW")
        except Exception:
            pass
        _draw_handle = None
    if _draw_handle_px is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_draw_handle_px, "WINDOW")
        except Exception:
            pass
        _draw_handle_px = None
    if _reset_scatter_state in bpy.app.handlers.load_post:
        try:
            bpy.app.handlers.load_post.remove(_reset_scatter_state)
        except Exception:
            pass


class PH_OT_scatter_brush(bpy.types.Operator):
    """Scatter Brush\nDrag on a surface to scatter, Ctrl+Drag to erase\nDrag on empty space to box-select source objects\nAlt+Wheel (hover), Wheel (while painting) or [ ]: Adjust Radius"""
    bl_idname = "object.ph_scatter_brush"
    bl_label = "Scatter Brush"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT" and context.area and context.area.type == "VIEW_3D"

    # 运行时状态
    painting = False
    erasing = False
    ctrl = False
    cur_pressure = 1.0

    sources = None
    weights = None
    target = None
    bvh = None
    eval_target = None
    eval_mesh = None
    target_matrix = None
    target_matrix_inv = None

    created_session = None  # 整个模态会话创建的物体
    created_stroke = 0  # 当前笔触创建数
    erased_stroke = 0
    collection = None

    grid = None
    grid_cell = 0.1
    last_stamp = None

    cur_center = None
    cur_normal = None

    start_area = None

    # 遮罩
    mask_pixels = None
    mask_w = 0
    mask_h = 0

    # INVOKE / MODAL
    # ------------------------------------------------------------------

    def invoke(self, context, event):
        global _INSTANCE_RUNNING
        if _INSTANCE_RUNNING:
            return {"CANCELLED"}

        self.props = scatter_tool_props()
        self.painting = False
        self.erasing = False
        self.ctrl = event.ctrl
        self.cur_pressure = 1.0
        self.created_session = []
        self.grid = {}
        self.last_stamp = None
        self.cur_center = None
        self.cur_normal = None
        self._reset_target()

        self.collection = self.get_scatter_collection(context)
        self.start_area = context.area

        # 仅在工具实际激活、进入模态时才注册绘制/加载处理器
        _add_brush_draw()

        _INSTANCE_RUNNING = True
        context.window_manager.modal_handler_add(self)
        self.update_hover(context, event)
        self._tag(context)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        # 任何异常都安全退出并复位单例标记，避免工具卡死再也无法绘制
        try:
            return self._process_event(context, event)
        except Exception:
            import traceback
            traceback.print_exc()
            self.finish(context)
            return {"FINISHED"}

    def _process_event(self, context, event):
        # 重新获取属性指针：全局撤销(Ctrl+Z)会重建数据块，invoke 时缓存的
        # scene.scatter_tool RNA 指针会失效，再访问 self.props 会直接导致
        # 访问越界崩溃（Python try/except 也拦不住）。每个事件都重新取一次。
        try:
            self.props = context.scene.scatter_tool
        except (AttributeError, ReferenceError):
            self.finish(context)
            return {"FINISHED"}

        # 工具被切走则退出
        if not active_tool_is_scatter(context):
            self.finish(context)
            return {"FINISHED"}

        self.ctrl = event.ctrl

        # 实时记录数位板笔压，供密度/缩放映射与屏幕读数显示
        if (self.props.use_pressure_density or self.props.use_pressure_scale
                or self.props.use_pressure_radius) \
                and getattr(event, "is_tablet", False):
            self.cur_pressure = max(0.0, min(1.0, event.pressure))

        # 调整半径：[ ] 始终可用
        if event.type in {"LEFT_BRACKET", "RIGHT_BRACKET"} and event.value == "PRESS":
            factor = 0.85 if event.type == "LEFT_BRACKET" else 1.18
            self.props.radius = max(0.001, self.props.radius * factor)
            self._tag(context)
            return {"RUNNING_MODAL"}

        # 滚轮：绘制中、或悬停时按住 Alt 调整笔刷大小；否则让出给视图缩放
        if event.type in {"WHEELUPMOUSE", "WHEELDOWNMOUSE"}:
            if self.painting or event.alt:
                factor = 1.12 if event.type == "WHEELUPMOUSE" else 0.88
                self.props.radius = max(0.001, self.props.radius * factor)
                self._tag(context)
                return {"RUNNING_MODAL"}
            return {"PASS_THROUGH"}

        # 让出视图导航
        if event.type in {"MIDDLEMOUSE",
                          "NUMPAD_1", "NUMPAD_2", "NUMPAD_3", "NUMPAD_4", "NUMPAD_5",
                          "NUMPAD_6", "NUMPAD_7", "NUMPAD_8", "NUMPAD_9"}:
            return {"PASS_THROUGH"}

        if event.type in {"ESC"} and event.value == "PRESS":
            self.finish(context)
            # 退出散布并切换到内置框选工具
            try:
                bpy.ops.wm.tool_set_by_id(name="builtin.select_box")
            except Exception:
                pass
            return {"FINISHED"}

        inside = self.in_view_region(context, event)

        # 指针不在 3D 视图绘制区内（工具栏/顶栏/侧栏等）：放行事件，保证可以点击切换工具、使用顶栏
        if not self.painting and not inside:
            if self.cur_center is not None:
                self.cur_center = None
                self._tag(context)
            return {"PASS_THROUGH"}

        if event.type == "LEFTMOUSE":
            if event.value == "PRESS":
                if not inside:
                    return {"PASS_THROUGH"}
                # 空白处（光标下无表面）起拖：交给原生框选，用选中结果更新散布源物体
                if not event.ctrl and self.cur_center is None:
                    self.finish(context)
                    try:
                        bpy.ops.view3d.select_box("INVOKE_DEFAULT")
                    except Exception:
                        pass
                    return {"FINISHED"}
                self.begin_stroke(context, event)
                self._tag(context)
                return {"RUNNING_MODAL"}
            elif event.value == "RELEASE":
                self.end_stroke(context)
                self._tag(context)
                return {"RUNNING_MODAL"}

        if event.type == "MOUSEMOVE":
            self.update_hover(context, event)
            if self.painting:
                if self.erasing:
                    self.erase_at(context)
                else:
                    self.paint_at(context, event)
            self._tag(context)
            return {"RUNNING_MODAL"}

        return {"PASS_THROUGH"}

    # 叠加在 WINDOW 之上的界面子区域（工具栏/顶栏/侧栏/资产架等）
    _UI_REGION_TYPES = {
        "HEADER", "TOOL_HEADER", "UI", "TOOLS", "HUD", "NAV_BAR",
        "EXECUTE", "FOOTER", "ASSET_SHELF", "ASSET_SHELF_HEADER",
    }

    def in_view_region(self, context, event) -> bool:
        """指针是否位于 3D 视图真正的绘制区内。

        注意：VIEW_3D 的 WINDOW 区域铺满整个编辑器，工具栏(TOOLS)、
        顶部工具设置栏(TOOL_HEADER)、N 侧栏(UI) 等是叠加在其上的子区域。
        因此必须先判断指针是否落在这些叠加 UI 子区域内——是则视为视口外，
        放行事件，保证可以点击切换工具、使用顶栏。
        """
        area = context.area
        if area is None or area.type != "VIEW_3D":
            return False

        mx, my = event.mouse_x, event.mouse_y
        win_region = None
        for region in area.regions:
            if region.type == "WINDOW":
                win_region = region
                continue
            if region.type not in self._UI_REGION_TYPES:
                continue
            if region.width <= 1 or region.height <= 1:
                continue
            if (region.x <= mx < region.x + region.width and
                    region.y <= my < region.y + region.height):
                return False

        if win_region is None:
            return False
        return (win_region.x <= mx < win_region.x + win_region.width and
                win_region.y <= my < win_region.y + win_region.height)

    def _tag(self, context):
        self._sync_draw()
        area = self.start_area or context.area
        try:
            if area:
                area.tag_redraw()
        except (ReferenceError, AttributeError):
            pass

    # STROKE LIFECYCLE
    # ------------------------------------------------------------------

    def begin_stroke(self, context, event):
        self.created_stroke = 0
        self.erased_stroke = 0
        self.last_stamp = None

        if event.ctrl:
            self.erasing = True
            self.painting = True
            self.erase_at(context)
            return

        self.erasing = False
        self.sources = [o for o in context.selected_objects if o.type in _SOURCE_TYPES]
        if not self.sources:
            self.report({"WARNING"}, _iface("Please select at least one object to scatter"))
            self.painting = False
            return

        self.weights = [max(0.0, getattr(o, "ph_scatter_weight", 1.0)) for o in self.sources]
        if sum(self.weights) <= 0:
            self.weights = [1.0] * len(self.sources)
        # 叠加模式场景投射时需要跳过散布源本身
        self._stroke_skip = {o.name for o in self.sources}

        target = self.pick_target(context, event)
        if target is None:
            self.report({"INFO"}, _iface("No surface under cursor"))
            self.painting = False
            return

        self.target = target
        self.setup_target(context, target)
        self.compute_grid_cell()
        # 撤销/重做后缓存的集合引用可能失效，每次落笔前重新获取，避免 ReferenceError
        self.collection = self.get_scatter_collection(context)

        self.painting = True
        self.paint_at(context, event)

    def end_stroke(self, context):
        was_painting = self.painting
        self.painting = False
        self.erasing = False
        self._clear_target_data()
        # 延迟到模态事件之外推送撤销点：在模态事件内直接调用 bpy.ops.ed.undo_push
        # 可能释放正在运行算子的内存，导致工具卡死，因此用定时器延后执行。
        if was_painting and (self.created_stroke > 0 or self.erased_stroke > 0):
            try:
                bpy.app.timers.register(_deferred_undo_push, first_interval=0.0)
            except Exception:
                pass

    def setup_target(self, context, target):
        depsgraph = context.evaluated_depsgraph_get()
        self._reset_target()

        use_mask = self.props.use_mask and self.props.mask_image is not None
        if use_mask:
            self.eval_target = target.evaluated_get(depsgraph)
            self.eval_mesh = self.eval_target.to_mesh()
            self.target_matrix = self.eval_target.matrix_world.copy()
            try:
                self.target_matrix_inv = self.target_matrix.inverted()
            except ValueError:
                self.target_matrix_inv = Matrix.Identity(4)
            self._build_mask()
        else:
            eval_obj = target.evaluated_get(depsgraph)
            mesh = eval_obj.to_mesh()
            mat = eval_obj.matrix_world
            verts = [mat @ v.co for v in mesh.vertices]
            polys = [tuple(p.vertices) for p in mesh.polygons]
            try:
                self.bvh = BVHTree.FromPolygons(verts, polys)
            except Exception:
                self.bvh = None
            eval_obj.to_mesh_clear()

    def _reset_target(self):
        self.target = None
        self.bvh = None
        self.eval_target = None
        self.eval_mesh = None
        self.target_matrix = None
        self.target_matrix_inv = None
        self.mask_pixels = None
        self.mask_w = 0
        self.mask_h = 0

    def _clear_target_data(self):
        if self.eval_target is not None and self.eval_mesh is not None:
            try:
                self.eval_target.to_mesh_clear()
            except Exception:
                pass
        self._reset_target()

    # RAYCAST
    # ------------------------------------------------------------------

    def _cast(self, origin_w: Vector, dir_w: Vector):
        """返回 (世界坐标, 世界法线, 局部坐标 or None, 面索引 or None)"""
        if self.eval_mesh is not None and self.eval_target is not None:
            mi = self.target_matrix_inv
            lo = mi @ origin_w
            ld = (mi.to_3x3() @ dir_w).normalized()
            ok, loc, nor, idx = self.eval_target.ray_cast(lo, ld)
            if not ok:
                return None
            wl = self.target_matrix @ loc
            wn = (self.target_matrix.to_3x3().inverted_safe().transposed() @ nor).normalized()
            return wl, wn, loc, idx
        if self.bvh is not None:
            loc, nor, idx, _dist = self.bvh.ray_cast(origin_w, dir_w)
            if loc is None:
                return None
            return loc, nor.normalized(), None, idx
        return None

    def _cast_scene(self, context, origin_w: Vector, dir_w: Vector):
        """叠加模式用：对整个场景投射（含已散布物体），跳过散布源本身。"""
        depsgraph = context.evaluated_depsgraph_get()
        skip = getattr(self, "_stroke_skip", None) or set()
        direction = dir_w.normalized()
        start = origin_w.copy()
        for _ in range(8):
            result, location, normal, _i, obj, _m = context.scene.ray_cast(depsgraph, start, direction)
            if not result:
                return None
            if obj is None or obj.name not in skip:
                return location, normal.normalized(), None, None
            start = location + direction * 0.0001
        return None

    def pick_target(self, context, event):
        depsgraph = context.evaluated_depsgraph_get()
        origin, direction = mouse_ray(context, event)
        skip = self.skip_names(context)
        start = origin.copy()
        for _ in range(8):
            result, location, _n, _i, obj, _m = context.scene.ray_cast(depsgraph, start, direction)
            if not result:
                return None
            if obj is not None and obj.name not in skip:
                return obj
            start = location + direction * 0.0001
        return None

    def skip_names(self, context):
        names = set()
        for o in context.selected_objects:
            if o.type in _SOURCE_TYPES:
                names.add(o.name)
        # 叠加模式下，已散布物体应作为可投射的表面，因此不加入跳过集合
        if not self.props.use_stacking:
            coll = find_scatter_collection()
            if coll:
                for o in coll.objects:
                    names.add(o.name)
        return names

    def update_hover(self, context, event):
        """悬停时用场景投射定位笔刷圆环（贴在地表）"""
        depsgraph = context.evaluated_depsgraph_get()
        origin, direction = mouse_ray(context, event)
        skip = self.skip_names(context)
        start = origin.copy()
        for _ in range(8):
            result, location, normal, _i, obj, _m = context.scene.ray_cast(depsgraph, start, direction)
            if not result:
                self.cur_center = None
                return
            if obj is not None and obj.name not in skip:
                self.cur_center = location
                self.cur_normal = normal.normalized()
                return
            start = location + direction * 0.0001
        self.cur_center = None

    # PAINT
    # ------------------------------------------------------------------

    def paint_at(self, context, event):
        origin, direction = mouse_ray(context, event)
        # 叠加模式：用场景投射（含已散布物体）定位落点，可在其表面继续堆叠
        if self.props.use_stacking:
            res = self._cast_scene(context, origin, direction)
        else:
            res = self._cast(origin, direction)
        if res is None:
            return
        center, normal = res[0], res[1]
        self.cur_center, self.cur_normal = center, normal

        pressure = 1.0
        if (self.props.use_pressure_density or self.props.use_pressure_scale
                or self.props.use_pressure_radius):
            pressure = self.cur_pressure if getattr(event, "is_tablet", False) else 1.0

        step = max(self._effective_radius(pressure) * 0.4, 1e-4)
        if self.last_stamp is not None and (center - self.last_stamp).length < step:
            return
        self.last_stamp = center

        self.do_stamp(context, center, normal, pressure)

    # 单次笔触放置上限与尝试系数，避免大半径/高密度时卡死
    _MAX_PER_STAMP = 300
    _ATTEMPT_FACTOR = 6
    _MAX_ATTEMPTS = 2000

    def _effective_radius(self, pressure: float = 1.0) -> float:
        """笔刷有效半径（优先级：压感 > 随机 > 固定）。"""
        p = self.props
        if p.use_pressure_radius:
            lo, hi = p.pressure_radius_min, p.pressure_radius_max
            if hi < lo:
                lo, hi = hi, lo
            return max(0.001, lo + (hi - lo) * max(0.0, min(1.0, pressure)))
        if p.use_random_radius:
            lo, hi = p.radius, p.radius_max
            if hi < lo:
                lo, hi = hi, lo
            return max(0.001, random.uniform(lo, hi))
        return p.radius

    def do_stamp(self, context, center: Vector, normal: Vector, pressure: float = 1.0):
        radius = self._effective_radius(pressure)
        t1, t2 = tangent_basis(normal)

        # 密度来源（优先级）：压感映射 > 随机 > 固定
        if self.props.use_pressure_density:
            lo, hi = self.props.pressure_density_min, self.props.pressure_density_max
            if hi < lo:
                lo, hi = hi, lo
            density = lo + (hi - lo) * max(0.0, min(1.0, pressure))
        elif self.props.use_random_density:
            lo, hi = self.props.density, self.props.density_max
            if hi < lo:
                lo, hi = hi, lo
            density = random.uniform(lo, hi)
        else:
            density = self.props.density

        # 目标数量 = 密度 × 笔刷面积；越界则做安全裁剪
        area = math.pi * radius * radius
        target = int(round(density * area))
        if self.props.use_pressure_density:
            # 启用压感时允许“轻触少放、几乎不放”，因此下限为 0
            target = max(0, min(target, self._MAX_PER_STAMP))
            if target == 0:
                return
        else:
            target = max(1, min(target, self._MAX_PER_STAMP))

        # 有间距/防穿插约束时，超采样尝试以填满可行点位，
        # 这样大“最小距离”不会因尝试次数不足而导致散布过少。
        md_active = self.props.min_dist > 0.0 or (
            self.props.use_random_min_dist and self.props.min_dist_max > 0.0)
        spacing_active = md_active or self.props.avoid_overlap
        if spacing_active:
            attempts = min(target * self._ATTEMPT_FACTOR, self._MAX_ATTEMPTS)
        else:
            attempts = target

        placed = 0
        for _ in range(attempts):
            if placed >= target:
                break

            a = random.uniform(0.0, 2.0 * math.pi)
            r = radius * math.sqrt(random.random())
            candidate = center + (math.cos(a) * t1 + math.sin(a) * t2) * r

            cast_origin = candidate + normal * (radius + 0.001)
            if self.props.use_stacking:
                res = self._cast_scene(context, cast_origin, -normal)
            else:
                res = self._cast(cast_origin, -normal)
            if res is None:
                # 采样点正下方没有表面：笔刷大于散布面时会出现这种情况。
                # 默认跳过，避免把物体散布到表面之外。
                if self.props.limit_to_surface:
                    continue
                loc, nor, local_loc, face_idx = candidate, normal, None, None
            else:
                loc, nor, local_loc, face_idx = res

            if not self.passes_filters(loc, nor):
                continue

            if self.mask_pixels is not None and face_idx is not None and local_loc is not None:
                if random.random() > self.sample_mask(face_idx, local_loc):
                    continue

            src = random.choices(self.sources, weights=self.weights, k=1)[0]
            scale_vec = self._random_scale(pressure)
            dims = src.dimensions
            rep = max(scale_vec.x, scale_vec.y, scale_vec.z)
            inst_radius = Vector((dims[0], dims[1], dims[2])).length * 0.5 * rep

            if not self.accept_point(loc, inst_radius):
                continue

            self.create_instance(src, scale_vec, loc, nor)
            placed += 1

    def _random_scale(self, pressure: float = 1.0) -> Vector:
        """返回本次实例的缩放系数。
        优先级：压感映射 > 随机 > 固定。
        - 压感：在 [min,max] 间按笔压取值。
        - 随机：在 [min,max] 取随机，若再开“各轴随机”则三轴独立（非等比）。
        - 固定：取 scale_min。
        """
        p = self.props
        lo, hi = p.scale_min, p.scale_max
        if hi < lo:
            lo, hi = hi, lo
        if p.use_pressure_scale:
            f = lo + (hi - lo) * max(0.0, min(1.0, pressure))
            return Vector((f, f, f))
        if not p.use_random_scale:
            s = p.scale_min
            return Vector((s, s, s))
        if p.random_scale_axis:
            return Vector((random.uniform(lo, hi),
                           random.uniform(lo, hi),
                           random.uniform(lo, hi)))
        f = random.uniform(lo, hi)
        return Vector((f, f, f))

    def passes_filters(self, loc: Vector, normal: Vector) -> bool:
        p = self.props
        if p.use_slope_limit:
            slope = math.degrees(Vector((0.0, 0.0, 1.0)).angle(normal, 0.0))
            if slope > p.slope_limit:
                return False
        if p.use_height_limit:
            if loc.z < p.height_min or loc.z > p.height_max:
                return False
        return True

    def accept_point(self, loc: Vector, radius: float) -> bool:
        if self.props.use_random_min_dist:
            lo, hi = self.props.min_dist, self.props.min_dist_max
            if hi < lo:
                lo, hi = hi, lo
            md = random.uniform(lo, hi)
        else:
            md = self.props.min_dist
        ao = self.props.avoid_overlap
        if md <= 0 and not ao:
            return True
        cell = self.grid_cell
        cx, cy, cz = int(loc.x // cell), int(loc.y // cell), int(loc.z // cell)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for (p, pr) in self.grid.get((cx + dx, cy + dy, cz + dz), ()):
                        sep = md
                        if ao:
                            sep = max(sep, (radius + pr) * self.props.overlap_factor)
                        if (p - loc).length < sep:
                            return False
        self.grid.setdefault((cx, cy, cz), []).append((loc, radius))
        return True

    def compute_grid_cell(self):
        max_r = 0.0
        for s in self.sources:
            d = s.dimensions
            max_r = max(max_r, Vector((d[0], d[1], d[2])).length * 0.5 * self.props.scale_max)
        factor = max(self.props.overlap_factor, 1.0)
        # 随机间距时，网格必须按最大可能间距取格，保证邻域搜索覆盖
        eff_min_dist = self.props.min_dist
        if self.props.use_random_min_dist:
            eff_min_dist = max(self.props.min_dist, self.props.min_dist_max)
        self.grid_cell = max(eff_min_dist, max_r * 2.0 * factor, 1e-4)

    def create_instance(self, src, scale: Vector, loc: Vector, normal: Vector):
        new_obj = src.copy()
        if self.props.duplicate == "COPY" and src.data:
            new_obj.data = src.data.copy()
        # 防御性：若缓存的集合引用因撤销/重做而失效，重新获取一个有效集合
        try:
            coll = self.collection
            coll.objects.link(new_obj)
        except ReferenceError:
            coll = self.get_scatter_collection(bpy.context)
            self.collection = coll
            coll.objects.link(new_obj)

        if self.props.align_normal:
            align_q = Vector((0.0, 0.0, 1.0)).rotation_difference(normal)
        else:
            align_q = Quaternion()

        angle = random.uniform(0.0, 2.0 * math.pi) if self.props.random_rotation else 0.0
        z_q = Quaternion((0.0, 0.0, 1.0), angle)

        rot_q = align_q @ z_q

        if self.props.tilt_max > 0.0:
            tilt = math.radians(random.uniform(0.0, self.props.tilt_max))
            ta = random.uniform(0.0, 2.0 * math.pi)
            t1, t2 = tangent_basis(normal)
            tilt_axis = math.cos(ta) * t1 + math.sin(ta) * t2
            rot_q = Quaternion(tilt_axis, tilt) @ rot_q

        rot_mat = rot_q.to_matrix().to_4x4()
        src_scale = src.matrix_world.to_scale()
        final_scale = Vector((src_scale.x * scale.x,
                              src_scale.y * scale.y,
                              src_scale.z * scale.z))
        scale_mat = Matrix.Diagonal(final_scale.to_4d())

        if self.props.use_random_height:
            lo, hi = self.props.z_offset, self.props.z_offset_max
            if hi < lo:
                lo, hi = hi, lo
            height = random.uniform(lo, hi)
        else:
            height = self.props.z_offset
        offset = normal * height
        new_obj.matrix_world = Matrix.Translation(loc + offset) @ rot_mat @ scale_mat
        new_obj.select_set(False)

        self.created_session.append(new_obj)
        self.created_stroke += 1

    # ERASE
    # ------------------------------------------------------------------

    def erase_at(self, context):
        if self.cur_center is None:
            return
        coll = find_scatter_collection()
        if coll is None:
            return
        radius = self.props.radius
        center = self.cur_center
        for obj in list(coll.objects):
            if (obj.matrix_world.translation - center).length <= radius:
                try:
                    bpy.data.objects.remove(obj, do_unlink=True)
                    self.erased_stroke += 1
                except (ReferenceError, RuntimeError):
                    pass

    # MASK
    # ------------------------------------------------------------------

    def _build_mask(self):
        self.mask_pixels = None
        img = self.props.mask_image
        if img is None:
            return
        try:
            w, h = img.size[0], img.size[1]
            if w <= 0 or h <= 0:
                return
            buf = [0.0] * (w * h * 4)
            img.pixels.foreach_get(buf)
            self.mask_pixels = buf
            self.mask_w = w
            self.mask_h = h
        except Exception:
            self.mask_pixels = None

    def sample_mask(self, face_idx: int, local_loc: Vector) -> float:
        try:
            mesh = self.eval_mesh
            uv_layer = mesh.uv_layers.active
            if uv_layer is None:
                return 1.0
            poly = mesh.polygons[face_idx]
            coords = [mesh.vertices[mesh.loops[li].vertex_index].co for li in poly.loop_indices]
            uvs = [uv_layer.data[li].uv for li in poly.loop_indices]
            weights = poly_3d_calc(coords, local_loc)
            u = sum(w * uv.x for w, uv in zip(weights, uvs))
            v = sum(w * uv.y for w, uv in zip(weights, uvs))

            x = int((u % 1.0) * self.mask_w) % self.mask_w
            y = int((v % 1.0) * self.mask_h) % self.mask_h
            idx = (y * self.mask_w + x) * 4
            r, g, b, _a = self.mask_pixels[idx:idx + 4]
            val = 0.2126 * r + 0.7152 * g + 0.0722 * b
            if self.props.mask_invert:
                val = 1.0 - val
            return max(0.0, min(1.0, val))
        except Exception:
            return 1.0

    # COLLECTION
    # ------------------------------------------------------------------

    @staticmethod
    def get_scatter_collection(context):
        coll = find_scatter_collection()
        if coll is None:
            coll = bpy.data.collections.new(SCATTER_COLL_NAME)
        # 确保标记存在（含旧版按名字创建的集合，首次使用时补标记）
        if not coll.get(SCATTER_COLL_ID):
            coll[SCATTER_COLL_ID] = True
        if coll not in context.scene.collection.children_recursive:
            try:
                context.scene.collection.children.link(coll)
            except RuntimeError:
                pass
        return coll

    # END
    # ------------------------------------------------------------------

    def finish(self, context):
        global _INSTANCE_RUNNING
        try:
            self._clear_target_data()
        except Exception:
            pass
        self.painting = False
        self.erasing = False
        _INSTANCE_RUNNING = False
        _DRAW["active"] = False
        _DRAW["center"] = None
        area = self.start_area or context.area
        try:
            if area:
                area.tag_redraw()
        except (ReferenceError, AttributeError):
            pass
        # 退出模态即移除绘制/加载处理器，不让其常驻
        _remove_brush_draw()

    # DRAW
    # ------------------------------------------------------------------

    def _sync_draw(self):
        """把当前实例状态同步到模块级绘制字典，供 _draw_brush_callback 读取。"""
        try:
            pref = get_pref().scatter_tool
            _DRAW["color"] = tuple(pref.ring_color_erase if self.ctrl else pref.ring_color)
            _DRAW["width"] = pref.ring_width
        except Exception:
            _DRAW["color"] = (1.0, 0.25, 0.2, 0.9) if self.ctrl else (0.2, 0.7, 1.0, 0.9)
            _DRAW["width"] = 2.0
        try:
            prop = bpy.context.scene.scatter_tool
            if self.painting and prop.use_pressure_radius:
                _DRAW["radius"] = self._effective_radius(self.cur_pressure)
            else:
                _DRAW["radius"] = prop.radius
        except Exception:
            pass
        _DRAW["center"] = self.cur_center
        _DRAW["normal"] = self.cur_normal
        _DRAW["active"] = True
        try:
            _DRAW["pressure"] = self.cur_pressure
            _DRAW["show_pressure"] = bool(
                (self.props.use_pressure_density or self.props.use_pressure_scale
                 or self.props.use_pressure_radius) and self.painting)
        except Exception:
            _DRAW["show_pressure"] = False


class PH_OT_scatter_clear(bpy.types.Operator):
    """Remove all objects scattered into the Scatter collection"""
    bl_idname = "object.ph_scatter_clear"
    bl_label = "Clear Scattered"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        coll = find_scatter_collection()
        return coll is not None and len(coll.objects) > 0

    def execute(self, context):
        coll = find_scatter_collection()
        if coll is None:
            return {"CANCELLED"}
        count = 0
        for obj in list(coll.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
            count += 1
        self.report({"INFO"}, _iface("Removed %d scattered objects") % count)
        return {"FINISHED"}


class PH_OT_scatter_apply(bpy.types.Operator):
    """Apply scattered objects: move them out of the Scatter collection so they
    become permanent and are no longer removed by Clear Scattered"""
    bl_idname = "object.ph_scatter_apply"
    bl_label = "Apply Scatter"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        coll = find_scatter_collection()
        return coll is not None and len(coll.objects) > 0

    def execute(self, context):
        coll = find_scatter_collection()
        if coll is None:
            return {"CANCELLED"}
        # 优先放入散布集合所在的父级；退回场景根集合
        target = context.scene.collection
        count = 0
        for obj in list(coll.objects):
            try:
                if obj.name not in target.objects:
                    target.objects.link(obj)
            except RuntimeError:
                pass
            try:
                coll.objects.unlink(obj)
            except RuntimeError:
                pass
            count += 1
        self.report({"INFO"}, _iface("Applied %d scattered objects") % count)
        return {"FINISHED"}


class PH_OT_scatter_random_weights(bpy.types.Operator):
    """Randomize the scatter probability (weight) of the selected source objects"""
    bl_idname = "object.ph_scatter_random_weights"
    bl_label = "Randomize Weights"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return any(o.type in _SOURCE_TYPES for o in context.selected_objects)

    def execute(self, context):
        count = 0
        for o in context.selected_objects:
            if o.type in _SOURCE_TYPES:
                o.ph_scatter_weight = round(random.uniform(0.1, 2.0), 2)
                count += 1
        self.report({"INFO"}, _iface("Randomized %d source weights") % count)
        return {"FINISHED"}


@persistent
def _reset_scatter_state(_dummy):
    """文件加载时复位运行状态并清理处理器。

    打开 / 新建文件会终止正在运行的模态算子，但不会调用 finish()，
    导致 _INSTANCE_RUNNING 残留为 True、绘制句柄泄漏。该处理器只在
    模态运行期间挂载（invoke 时），加载后复位状态并移除自身与绘制句柄。
    """
    global _INSTANCE_RUNNING, _draw_handle, _draw_handle_px
    _INSTANCE_RUNNING = False
    _DRAW["active"] = False
    _DRAW["center"] = None
    if _draw_handle is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, "WINDOW")
        except Exception:
            pass
        _draw_handle = None
    if _draw_handle_px is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_draw_handle_px, "WINDOW")
        except Exception:
            pass
        _draw_handle_px = None
    if _reset_scatter_state in bpy.app.handlers.load_post:
        try:
            bpy.app.handlers.load_post.remove(_reset_scatter_state)
        except Exception:
            pass


classes = (
    PH_OT_scatter_brush,
    PH_OT_scatter_clear,
    PH_OT_scatter_apply,
    PH_OT_scatter_random_weights,
)

_register_cls, _unregister_cls = bpy.utils.register_classes_factory(classes)


def register():
    global _INSTANCE_RUNNING
    _register_cls()
    # 处理器不随扩展注册而常驻，改为工具激活进入模态时按需注册
    _INSTANCE_RUNNING = False
    _DRAW["active"] = False


def unregister():
    global _draw_handle, _draw_handle_px
    # 卸载时兜底清理可能仍挂载的处理器（正常情况 finish 已移除）
    if _reset_scatter_state in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_reset_scatter_state)
    _DRAW["active"] = False
    if _draw_handle is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, "WINDOW")
        except Exception:
            pass
        _draw_handle = None
    if _draw_handle_px is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_draw_handle_px, "WINDOW")
        except Exception:
            pass
        _draw_handle_px = None
    _unregister_cls()
