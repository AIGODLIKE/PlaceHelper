from . import op, gzg, tool, _runtime,test


def register():
    op.register()
    gzg.register()
    tool.register()
    test.register()


def unregister():
    tool.unregister()
    gzg.unregister()
    op.unregister()
    test.unregister()