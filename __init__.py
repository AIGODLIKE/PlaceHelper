from . import custom_gizmos, place_tool, transform_tool, dynamic_place_tool, preferences, localdb,dynamic_place

bl_info = {
    "name": "Place Helper 放置助手",
    "author": "AIGODLIKE社区,Atticus,小萌新",
    "blender": (4, 2, 0),
    "version": (1, 3, 5),
    "category": "辣椒出品",
    "support": "COMMUNITY",
    "doc_url": "",
    "tracker_url": "",
    "description": "",
    "location": "Tool Shelf",
}


def register():
    preferences.register()
    custom_gizmos.register()
    place_tool.register()
    transform_tool.register()
    dynamic_place_tool.register()
    dynamic_place.register()
    localdb.register()


def unregister():
    localdb.unregister()
    dynamic_place_tool.unregister()
    dynamic_place.unregister()
    transform_tool.unregister()
    place_tool.unregister()
    custom_gizmos.unregister()
    preferences.unregister()


if __name__ == "__main__":
    register()
