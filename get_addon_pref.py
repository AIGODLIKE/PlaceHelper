import bpy


def get_addon_pref():
    """Get the addon preferences"""
    return bpy.context.preferences.addons[__package__].preferences
