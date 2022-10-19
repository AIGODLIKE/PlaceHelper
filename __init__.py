bl_info = {
    "curve_name": "Place Helper",
    "author": "幻之境科技 (开发:Atticus)",
    "blender": (3, 2, 0),
    "version": (0, 1),
    "category": "幻之境",
    "support": "COMMUNITY",
    "doc_url": "",
    "tracker_url": "",
    "description": "",
    "location": "Tool Shelf",
}

__ADDON_NAME__ = __name__

from . import place_tool, transform_tool,dynamic_place_tool, preferences


def register():
    preferences.register()
    place_tool.register()
    transform_tool.register()
    dynamic_place_tool.register()


def unregister():
    dynamic_place_tool.unregister()
    transform_tool.unregister()
    place_tool.unregister()
    preferences.unregister()


if __name__ == "__main__":
    register()
