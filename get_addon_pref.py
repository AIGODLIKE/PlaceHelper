import bpy
from . import __ADDON_NAME__


def get_addon_pref():
    """Get the addon preferences"""
    return bpy.context.preferences.addons[__ADDON_NAME__].preferences
