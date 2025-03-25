import bpy
from mathutils import Vector

from .draw import clear_handlers, TextHub, View3DHub, try_update_timer, TextAlign, AreaHub, MatrixHub
from .view_3d import Hub3DItem


def get_nonnormal_area_hash(area_restrictions: "list|int|None" = None):
    """获取区域最大化area之前内容的hash"""
    # bpy.context.screen.show_fullscreen
    if area_restrictions is None:
        return None

    def get_normal_area_hash(hash_int: int):
        screen = bpy.context.screen
        if screen.show_fullscreen:
            if screen.name.endswith("-nonnormal"):  # 当前屏幕为最大化时，获取最大化之前的屏幕
                name = screen.name.replace("-nonnormal", "")
                screen = bpy.data.screens.get(name, None)
                if screen:
                    for area in screen.areas:
                        if area.type == "EMPTY":
                            return hash(area)
        return hash_int

    if isinstance(area_restrictions, int):
        return get_normal_area_hash(area_restrictions)
    elif isinstance(area_restrictions, list):
        return [get_normal_area_hash(i) for i in area_restrictions]


def hub_matrix(
        identifier: str,
        matrices,
        timeout: float | None = 1,
        area_restrictions: "list|int|None" = None,
        is_alpha_animation: bool = True,
):
    MatrixHub(identifier, matrices, timeout, area_restrictions, is_alpha_animation)


def hub_3d(
        identifier: str,
        draw_items: list[Hub3DItem,] | Hub3DItem,
        *,
        timeout: float | None = 1,
        area_restrictions: "list|int|None" = None,
        is_alpha_animation: bool = True,
):
    """
    {
        "verts": [],
        "edges": {"verts": [], "sequences": []},
        "faces": {"verts": [], "sequences": []}
    }
    """
    # draw_data = four_to_three(draw_info)
    if isinstance(draw_items, Hub3DItem):
        draw_items.preprocessed_data()
        draw_items = [draw_items, ]
    else:
        for item in draw_items:
            item.preprocessed_data()

    View3DHub(
        identifier,
        draw_items,
        timeout,
        get_nonnormal_area_hash(area_restrictions),
        is_alpha_animation,
    )


def hub_text(
        identifier: str,
        texts: list,
        *,
        timeout: float | None = 1,
        text_offset: Vector = Vector((0, 0)).freeze(),
        text_align: TextAlign = TextAlign.CENTER_DOWN,
        area_restrictions: "list|int|None" = None,
        is_alpha_animation: bool = True,
):
    """
    [
        {"text": text, "color": red},
    ]
    """
    TextHub(
        identifier,
        texts,
        timeout,
        text_offset,
        text_align,
        get_nonnormal_area_hash(area_restrictions),
        is_alpha_animation,
    )


def hub_area(
        identifier: str,
        *,
        color: tuple = None,
        offset: int = 10,
        rounded_corner_size=10,
        timeout: float | None = 1,
        area_restrictions: "list|int|None" = None,
        is_alpha_animation: bool = True,
):
    AreaHub(
        identifier,
        color,
        offset,
        rounded_corner_size,
        timeout,
        get_nonnormal_area_hash(area_restrictions),
        is_alpha_animation,
    )


def clear_hub(identifier: str):
    """清理删除指定 的Hub"""
    from .draw import text_data, view_3d_data, area_data, try_update_timer

    if identifier in text_data:
        text_data.pop(identifier)
    if identifier in view_3d_data:
        view_3d_data.pop(identifier)
    if identifier in area_data:
        area_data.pop(identifier)
    try_update_timer()


def check_hub(identifier: str) -> bool:
    """检查输入的hub是否已经有显示的了"""
    from .draw import text_data, view_3d_data, area_data, try_update_timer

    if identifier in text_data:
        return True
    if identifier in view_3d_data:
        return True
    if identifier in area_data:
        return True
    return False


def register():
    ...


def unregister():
    clear_handlers()
    try_update_timer(True)
