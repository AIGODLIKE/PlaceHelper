#
# 使用 bpy.types.Object.name 为key，返回以该物体构建的AlignObject
# str : AlignObject

# 运行时缓存
# 结构: bpy.types.Object.name : AlignObject
# ------------------------------------------------------------

# 存放预计算的场景物体
SCENE_OBJS = {}

# 存放实时更新的激活项物体
ALIGN_OBJ = {'active_name': None,
             'active_prv_name': None}

ALIGN_OBJS = {'bbox_pts': None,
              'center': None,
              'top': None,
              'bottom': None}

OVERLAP_OBJ = {'obj_name': None,
               'is_project': False}
