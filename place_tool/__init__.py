from . import op, gzg, tool, _runtime, test, scatter_single


def register():
    op.register()
    gzg.register()
    tool.register()
    test.register()
    scatter_single.register()


def unregister():
    tool.unregister()
    gzg.unregister()
    op.unregister()
    test.unregister()
    scatter_single.unregister()
