#
# 使用 bpy.types.Object 为key，返回以该物体构建的AlignObject
# bpy.types.Object : AlignObject

import bpy
from bpy.app.handlers import persistent

from ..util.obj_bbox import AlignObject,C_OBJECT_TYPE_HAS_BBOX
from ..get_addon_pref import get_addon_pref

# 运行时缓存
# 结构:bpy.types.Object : AlignObject
# ------------------------------------------------------------

# 存放预计算的场景物体
SCENE_OBJS = {}

# 存放实时更新的激活项物体
ALIGN_OBJ = {'active': None,
             'active_prv': None}

ALIGN_OBJS = {'bbox_pts': None,
              'center': None,
              'top': None,
              'bottom': None}

OVERLAP_OBJ = {'obj': None,
               'is_project': False}


# ------------------------------------------------------------

# 检测更新的持久性handle
# ------------------------------

def has_active_obj():
    if not bpy.context:
        return
    elif not bpy.context.object:
        return
    elif bpy.context.object.type not in C_OBJECT_TYPE_HAS_BBOX:
        return
    else:
        return True


def update_active_obj(type: str = 'active_prv'):
    obj = bpy.context.object
    if obj not in SCENE_OBJS:
        pref = get_addon_pref()
        active_mode = bpy.context.scene.place_tool.active_bbox_calc_mode
        obj_A = AlignObject(obj, active_mode)
        SCENE_OBJS[obj] = obj_A
    else:
        obj_A = SCENE_OBJS[obj]

    ALIGN_OBJ[type] = obj_A


@persistent
def get_active_obj(scene):
    if not has_active_obj(): return
    update_active_obj('active_prv')


@persistent
def set_active_obj(scene):
    if not has_active_obj(): return
    update_active_obj('active')


# ------------------------------

def register():
    bpy.app.handlers.depsgraph_update_pre.append(update_active_obj)
    bpy.app.handlers.depsgraph_update_post.append(set_active_obj)


def unregister():
    bpy.app.handlers.depsgraph_update_pre.append(update_active_obj)
    bpy.app.handlers.depsgraph_update_post.remove(set_active_obj)
