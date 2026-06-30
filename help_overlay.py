"""各工具的左下角操作帮助提示，以及顶部工具栏的开关。

提示文本通过 bpy.app.translations 翻译，支持多语言。
"""

import math
import time

import blf
import bpy

# 可作为散布源的物体类型（与 scatter_tool/op.py 的 _SOURCE_TYPES 保持一致）
_SCATTER_SOURCE_TYPES = {
    "MESH", "CURVE", "SURFACE", "FONT", "META",
    "EMPTY", "LIGHT", "LIGHT_PROBE", "VOLUME",
    "GPENCIL", "GREASEPENCIL", "CURVES",
}

# 工具 idname -> (标题, [提示行, ...])
# 这里的源字符串均为英文，运行时经 pgettext_iface 翻译为当前界面语言。
_TOOL_HELP = {
    "ph.place_tool": (
        "Place Tool",
        [
            "Click: Select object",
            "Drag: Place on surface",
            "Alt + Drag: Box select",
            "Shift + Drag: Duplicate and place",
            "Alt + Click: Set placement axis",
            "Drag + Wheel: Spin around axis",
            "Drag + Ctrl + Alt + Wheel: Spin in 90 steps",
            "Esc: Exit to Select Box tool",
        ],
    ),
    "ph.transform_pro": (
        "Transform Pro",
        [
            "Drag object: Move",
            "Shift / Alt + Drag: Duplicate while moving",
            "Double click object: Enter Edit Mode",
            "Drag empty space: Box select",
            "Toggle Show Gizmo in the top bar",
            "Esc: Exit to Select Box tool",
        ],
    ),
    "ph.transform_pro_edit": (
        "Transform Pro",
        [
            "Drag gizmo: Move / rotate / scale",
            "Double click empty: Exit Edit Mode",
            "Drag empty space: Box select",
            "Esc: Exit to Select Box tool",
        ],
    ),
    "ph.dynamic_place_tool": (
        "Gravity Dynamic Place",
        [
            "Drag object: Drop with gravity",
            "Set Mode / Gravity in the top bar",
            "Esc: Exit to Select Box tool",
        ],
    ),
    "ph.scatter_tool": (
        "Scatter",
        [
            "Drag empty space: Box select sources",
            "Drag: Paint objects",
            "Ctrl + Drag: Erase",
            "Alt + Wheel: Adjust brush radius",
            "[ / ]: Adjust brush radius",
            "Esc: Exit to Select Box tool",
        ],
    ),
}

# 当散布工具未选择任何源物体时，在顶部高亮闪烁的提示
_SCATTER_NO_SOURCE_HINT = "Select objects first, then drag empty space to pick sources"

_HELP_HANDLE = None

# 无源物体高亮闪烁所需的重绘定时器
_PULSE_TIMER_ON = False
_LAST_PULSE_REQUEST = 0.0


def _has_scatter_source(context):
    try:
        objs = context.selected_objects
    except Exception:
        objs = None
    if not objs:
        return False
    return any(o.type in _SCATTER_SOURCE_TYPES for o in objs)


def _tag_view3d_redraw():
    wm = bpy.context.window_manager
    if wm is None:
        return
    for win in wm.windows:
        screen = win.screen
        if screen is None:
            continue
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def _pulse_timer():
    """持续重绘视口以驱动闪烁；提示停止请求后自动结束。"""
    global _PULSE_TIMER_ON
    if time.time() - _LAST_PULSE_REQUEST < 0.3:
        _tag_view3d_redraw()
        return 1.0 / 30.0
    _PULSE_TIMER_ON = False
    return None


def _request_pulse():
    """由绘制回调在需要闪烁时调用：刷新请求时间，并在必要时启动定时器。"""
    global _PULSE_TIMER_ON, _LAST_PULSE_REQUEST
    _LAST_PULSE_REQUEST = time.time()
    if not _PULSE_TIMER_ON:
        _PULSE_TIMER_ON = True
        try:
            bpy.app.timers.register(_pulse_timer)
        except Exception:
            _PULSE_TIMER_ON = False


def draw_help_toggle(layout):
    """在工具顶部设置栏添加帮助提示开关。"""
    wm = bpy.context.window_manager
    if hasattr(wm, "ph_show_tool_help"):
        layout.prop(wm, "ph_show_tool_help", text="", icon="QUESTION", toggle=True)


def _active_tool_idname(context):
    try:
        tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
    except Exception:
        return None
    return tool.idname if tool is not None else None


def _draw_help_callback():
    context = bpy.context
    try:
        wm = context.window_manager
        if not getattr(wm, "ph_show_tool_help", False):
            return
        if context.area is None or context.area.type != "VIEW_3D":
            return

        idname = _active_tool_idname(context)
        entry = _TOOL_HELP.get(idname)
        if entry is None:
            return

        region = context.region
        if region is None or region.type != "WINDOW":
            return

        title_src, hint_srcs = entry
        translate = bpy.app.translations.pgettext_iface
        title = translate(title_src)
        hints = [translate(h) for h in hint_srcs]

        ui = max(context.preferences.system.ui_scale, 0.5)
        try:
            from .utils import get_pref
            pref = get_pref()
            off_x, off_y = pref.help_offset_x, pref.help_offset_y
        except Exception:
            off_x, off_y = 18, 18
        font_id = 0
        size = round(11 * ui)
        title_size = round(12 * ui)
        line_h = round((size + 7) * ui)
        x = round(off_x * ui)
        y0 = round(off_y * ui)

        lines = [(title, title_size, (1.0, 1.0, 1.0, 0.95))]

        # 散布工具：未选择任何源物体时，在标题下方加一条闪烁高亮提示
        if idname == "ph.scatter_tool" and not _has_scatter_source(context):
            _request_pulse()
            pulse = 0.5 + 0.5 * math.sin(time.time() * 5.0)
            warn_color = (1.0, 0.55 + 0.25 * pulse, 0.12, 0.55 + 0.45 * pulse)
            warn = translate(_SCATTER_NO_SOURCE_HINT)
            lines.append(("\u25b6 " + warn, size, warn_color))

        for h in hints:
            lines.append((h, size, (0.85, 0.88, 0.95, 0.9)))

        total = len(lines)
        blf.enable(font_id, blf.SHADOW)
        blf.shadow(font_id, 3, 0.0, 0.0, 0.0, 0.85)
        blf.shadow_offset(font_id, 1, -1)

        for i, (text, fsize, color) in enumerate(lines):
            yy = y0 + (total - 1 - i) * line_h
            blf.size(font_id, fsize)
            blf.color(font_id, *color)
            blf.position(font_id, x, yy, 0.0)
            blf.draw(font_id, text)

        blf.disable(font_id, blf.SHADOW)
    except Exception:
        # 绘制回调里绝不能抛异常，否则会污染视口渲染
        pass


def register():
    global _HELP_HANDLE
    bpy.types.WindowManager.ph_show_tool_help = bpy.props.BoolProperty(
        name="Show Tool Help",
        description="Show operation hints for the active tool in the lower-left corner of the viewport",
        default=True,
    )
    if _HELP_HANDLE is None:
        _HELP_HANDLE = bpy.types.SpaceView3D.draw_handler_add(
            _draw_help_callback, (), "WINDOW", "POST_PIXEL")


def unregister():
    global _HELP_HANDLE, _PULSE_TIMER_ON
    if _HELP_HANDLE is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_HELP_HANDLE, "WINDOW")
        except (ValueError, ReferenceError):
            pass
        _HELP_HANDLE = None
    try:
        if bpy.app.timers.is_registered(_pulse_timer):
            bpy.app.timers.unregister(_pulse_timer)
    except Exception:
        pass
    _PULSE_TIMER_ON = False
    if hasattr(bpy.types.WindowManager, "ph_show_tool_help"):
        del bpy.types.WindowManager.ph_show_tool_help
