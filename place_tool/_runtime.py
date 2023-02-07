#
# 使用 bpy.types.Object 为key，返回以该物体构建的AlignObject
# bpy.types.Object : AlignObject

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
