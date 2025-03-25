from . import tool, gizmo, ops, props

module_list = [
    ops,
    gizmo,
    tool,
    props,
]


def register():
    for mod in module_list:
        mod.register()


def unregister():
    for mod in reversed(module_list):
        mod.unregister()
