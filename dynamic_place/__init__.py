from . import tool, gizmo, ops

module_list = [
    ops,
    gizmo,
    tool,
]


def register():
    for mod in module_list:
        mod.register()


def unregister():
    for mod in reversed(module_list):
        mod.unregister()
