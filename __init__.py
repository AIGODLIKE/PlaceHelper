bl_info = {
    "name": "Place Helper",
    "author": "幻之境科技 (开发:Atticus)",
    "blender": (3, 2, 0),
    "version": (1, 0),
    "category": "幻之境",
    "support": "COMMUNITY",
    "doc_url": "",
    "tracker_url": "",
    "description": "",
    "location": "Tool Shelf",
}

__ADDON_NAME__ = __name__

from . import custom_gizmos, place_tool, transform_tool, dynamic_place_tool, preferences, localdb


def register():
    preferences.register()
    custom_gizmos.register()
    place_tool.register()
    transform_tool.register()
    dynamic_place_tool.register()
    localdb.register()


def unregister():
    localdb.unregister()
    dynamic_place_tool.unregister()
    transform_tool.unregister()
    place_tool.unregister()
    custom_gizmos.unregister()
    preferences.unregister()


if __name__ == "__main__":
    register()
