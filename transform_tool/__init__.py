from . import op, gzg, tool


def register():
    op.register()
    gzg.register()
    tool.register()


def unregister():
    tool.unregister()
    gzg.unregister()
    op.unregister()
