import bpy

from .. import __package__ as base_package


def get_pref():
    return bpy.context.preferences.addons[base_package].preferences
