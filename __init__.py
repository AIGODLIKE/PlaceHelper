bl_info = {
    "name": "Place Helper 放置助手",
    "author": "AIGODLIKE社区,Atticus",
    "blender": (4, 1, 1),
    "version": (1, 2, 7),
    "category": "辣椒出品",
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
