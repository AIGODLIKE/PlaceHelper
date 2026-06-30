"""UI preview icons for PlaceHelper."""

from pathlib import Path

import bpy
import bpy.utils.previews

_preview_collection = None
ICON_RANDOM_DICE = "random_dice"


def _icons_dir() -> Path:
    return Path(__file__).resolve().parent


def random_dice_icon() -> int:
    if _preview_collection and ICON_RANDOM_DICE in _preview_collection:
        return _preview_collection[ICON_RANDOM_DICE].icon_id
    return 0


def draw_random_toggle(layout, data, prop_name, **kwargs):
    icon_id = random_dice_icon()
    if icon_id:
        layout.prop(data, prop_name, text="", icon="NONE", icon_value=icon_id, toggle=True, **kwargs)
    else:
        layout.prop(data, prop_name, text="", icon="MOD_NOISE", toggle=True, **kwargs)


def draw_random_operator(layout, op_idname, **kwargs):
    icon_id = random_dice_icon()
    if icon_id:
        layout.operator(op_idname, icon="NONE", icon_value=icon_id, **kwargs)
    else:
        layout.operator(op_idname, icon="MOD_NOISE", **kwargs)


def register():
    global _preview_collection
    _preview_collection = bpy.utils.previews.new()
    png = _icons_dir() / "random_dice.png"
    if png.is_file():
        _preview_collection.load(ICON_RANDOM_DICE, str(png), "IMAGE")


def unregister():
    global _preview_collection
    if _preview_collection is not None:
        bpy.utils.previews.remove(_preview_collection)
        _preview_collection = None
