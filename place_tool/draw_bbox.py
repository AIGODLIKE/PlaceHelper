# this file is used to draw bbox on blender‘s 3d View
from contextlib import contextmanager
from math import sin, cos, pi

import blf
import gpu
from bpy_extras.view3d_utils import location_3d_to_region_2d as loc3d_2_r2d
from gpu_extras.batch import batch_for_shader
from gpu_extras.presets import draw_circle_2d
from mathutils import Vector, Matrix

from ._runtime import ALIGN_OBJ, OVERLAP_OBJ, ALIGN_OBJS
from ..utils import get_pref
from ..utils.obj_bbox import AlignObject

C_OBJECT_TYPE = {'MESH', 'CURVE', 'FONT', 'LATTICE'}


def get_shader(type="3d"):
    shader_3d = gpu.shader.from_builtin('UNIFORM_COLOR')
    shader_2d = gpu.shader.from_builtin('UNIFORM_COLOR')
    shader_debug = gpu.shader.from_builtin('UNIFORM_COLOR')
    shader_tex = gpu.shader.from_builtin('IMAGE')

    if type == '3d':
        return shader_3d
    elif type == '2d':
        return shader_2d
    elif type == 'debug':
        return shader_debug
    elif type == 'tex':
        return shader_tex


def draw_bbox_callback(self, context):
    """draw bbox on 3d view"""
    if not context.object:
        return

    overlap_obj_a = OVERLAP_OBJ.get('obj')

    pref_bbox = get_pref().place_tool.bbox
    width = pref_bbox.width
    color = pref_bbox.color_alert if overlap_obj_a and pref_bbox.coll_alert else pref_bbox.color

    region = context.region
    r3d = context.space_data.region_3d

    with wrap_bgl_restore(width):
        if context.object and len(context.selected_objects) == 1:
            obj_A = ALIGN_OBJ.get('active', None)
            if context.object.type in C_OBJECT_TYPE and obj_A:  # mesh object

                shader_2d = get_shader('2d')
                shader_2d.bind()
                shader_2d.uniform_float("color", color)
                # 碰撞盒
                bbox_pts = get_obj_bbox_draw_pts(obj_A)
                if overlap_obj_a:
                    bbox_pts.extend(get_obj_bbox_draw_pts(overlap_obj_a))
                self.bbox_pts_2d = [loc3d_2_r2d(region, r3d, pt) for pt in bbox_pts]
                # 圆环和朝向
                bottom_pt = obj_A.get_axis_center(self.axis, self.invert_axis, is_local=True)
                circle_pts = get_circle_lines(obj_A.size, obj_A.mx, bottom_pt, self.axis)
                line_pts = get_normal_pts(obj_A.size, obj_A.mx, bottom_pt, self.axis, self.invert_axis)
                circle_pts.extend(line_pts)
                self.circle_pts_2d = [loc3d_2_r2d(region, r3d, pt) for pt in circle_pts]

                try:
                    batch = batch_for_shader(shader_2d, 'LINES', {"pos": self.circle_pts_2d})
                    batch.draw(shader_2d)
                except TypeError:
                    pass

                try:
                    batch = batch_for_shader(shader_2d, 'LINES', {"pos": self.bbox_pts_2d})
                    batch.draw(shader_2d)
                except TypeError:  # scale too big
                    pass

                draw_debug(obj_A, context)

            else:  # non mesh object
                pt = context.object.matrix_world.translation
                draw_circle_2d(loc3d_2_r2d(region, r3d, pt), color, radius=20)

        # objects
        elif context.object and len(context.selected_objects) > 1:
            objs_A = ALIGN_OBJS

            shader_2d = get_shader('2d')

            shader_2d.bind()
            shader_2d.uniform_float("color", color)

            if ALIGN_OBJS['bbox_pts']:
                # src
                pts = [pt for pt in objs_A['bbox_pts']]
                # element
                # bbox_pts = get_objs_bbox_draw_pts(objs_A['size'], pts, objs_A['center'])
                # circle_pts = get_circle_lines(objs_A['size'], Matrix.Translation(Vector((0, 0, 0))),
                #                               objs_A['bottom'])
                # line_pts = get_normal_pts(objs_A['size'], Matrix.Translation(Vector((0, 0, 0))),
                #                           objs_A['bottom'])
                # 2d
                draw_pts = pts
                draw_pts = [loc3d_2_r2d(region, r3d, pt) for pt in draw_pts]

                batch = batch_for_shader(shader_2d, 'POINTS', {"pos": draw_pts})
                batch.draw(shader_2d)


@contextmanager
def wrap_bgl_restore(width):
    ori_blend = gpu.state.blend_get()
    try:
        gpu.state.blend_set('ALPHA')
        gpu.state.line_width_set(width)
        gpu.state.point_size_set(8)

        yield  # do the work
    finally:
        gpu.state.blend_set(ori_blend)
        gpu.state.line_width_set(1)
        gpu.state.point_size_set(5)


def draw_debug(obj_A, context):
    # debug points
    if not get_pref().debug: return

    region = context.region
    r3d = context.space_data.region_3d

    shader_debug = get_shader('debug')

    shader_debug.bind()
    shader_debug.uniform_float("color", (0, 1, 0, 1))

    pt_3d = obj_A.get_neg_z_center(is_local=False)
    pt1_3d = obj_A.get_bbox_center(is_local=False)

    pt = loc3d_2_r2d(region, r3d, pt_3d)
    pt1 = loc3d_2_r2d(region, r3d, pt1_3d)

    batch = batch_for_shader(shader_debug, 'POINTS', {"pos": [pt, pt1]})
    batch.draw(shader_debug)

    font_id = 0
    blf.size(font_id, 20, 72)
    blf.color(font_id, 1, 1, 1, 1)
    blf.position(font_id, pt.x + 20, pt.y, 0)
    blf.draw(font_id, f'bottom:{pt_3d.x:.2f}, {pt_3d.y:.2f}, {pt_3d.z:.2f}')
    blf.position(font_id, pt1.x + 20, pt1.y, 0)
    blf.draw(font_id, f'center:{pt1_3d.x:.2f}, {pt1_3d.y:.2f}, {pt1_3d.z:.2f}')

    shader_debug.bind()
    shader_debug.uniform_float("color", (0, 1, 0, 1))

    if ALIGN_OBJS['bbox_pts']:
        pts = [loc3d_2_r2d(region, r3d, pt) for pt in ALIGN_OBJS['bbox_pts']]

        batch = batch_for_shader(shader_debug, 'POINTS', {"pos": pts})
        batch.draw(shader_debug)


def gen_pt_axis_co(pt: Vector, pt_center, offset: float = 0.1, threshold=0.1):
    """
    :param pt: 来源点
    :param offset: 偏移量
    :param threshold 用于避免快速移动出现的问题

    :return: 返回此点向三个轴向延申的一个角落的四个点
    """
    x, y, z = pt
    x_c, y_c, z_c = pt_center

    # 如果x小于x_c，则往x正方向设置点,反之往x负方向设置点
    def inv_axis(x, x_c):

        if x < x_c:
            return x + offset
        elif x > x_c:
            return x - offset
        else:
            return x

    pt1 = Vector((inv_axis(x, x_c), y, z))
    pt2 = Vector((x, inv_axis(y, y_c), z))
    pt3 = Vector((x, y, inv_axis(z, z_c)))

    return pt, pt1, pt2, pt3


def get_pt_co_lines(*args):
    """create line order of points"""
    pt, pt1, pt2, pt3 = gen_pt_axis_co(*args)
    return pt, pt1, pt, pt2, pt, pt3


def get_obj_bbox_draw_pts(obj: AlignObject, factor=0.15):
    """get bbox draw points,this bbox is a little bigger than the real bbox so that we can see the bbox"""
    draw_points = list()

    pts = obj.get_bbox_pts(is_local=True)
    pt_center = obj.get_bbox_center(is_local=True)

    scale_co = sum(obj.size) / 3 * factor

    for pt in pts:
        draw_points.extend(get_pt_co_lines(pt, pt_center, scale_co))
    # scale the bbox to make it look bigger
    scale_factor = 1.01
    scale_cage = Matrix.Diagonal(Vector((scale_factor,) * 3)).to_4x4()

    # get matrix result
    draw_points = [obj.mx @ scale_cage @ pt for pt in draw_points]

    return draw_points


def get_objs_bbox_draw_pts(size, pts, center: Vector, factor=0.1):
    """get bbox draw points,this bbox is a little bigger than the real bbox so that we can see the bbox"""
    draw_points = list()

    scale_co = sum(size) / 3 * factor

    for pt in pts:
        draw_points.extend(get_pt_co_lines(pt, center, scale_co))
    # scale the bbox to make it look bigger
    scale_factor = 1.01
    scale_cage = Matrix.Diagonal(Vector((scale_factor,) * 3)).to_4x4()

    # get matrix result
    draw_points = [scale_cage @ pt for pt in draw_points]

    return draw_points


def get_normal_pts(size, obj_mx: Matrix, local_center: Vector, axis='Z', invert_axis=False, factor=0.3):
    """get normal points from the bottom center of the bbox"""
    v = 1 if not invert_axis else -1

    if axis == 'Z':
        z = Vector((0, 0, v))
    elif axis == 'X':
        z = Vector((v, 0, 0))
    else:
        z = Vector((0, v, 0))

    length = size[-1] * factor

    pt1 = obj_mx @ local_center
    pt2 = obj_mx @ (local_center + z * length)
    return [pt1, pt2]


def get_circle_pts(size, obj_mx: Matrix, local_center: Vector, axis='Z', segments=32, factor=0.3):
    """get circle points from bottom center of bbox"""
    radius = sum(size[-1:]) / 2 * factor
    mul = (1.0 / (segments - 1)) * (pi * 2)

    if axis == 'Z':
        points = [(sin(i * mul) * radius, cos(i * mul) * radius, 0)
                  for i in range(segments)]
    elif axis == 'X':
        points = [(0, sin(i * mul) * radius, cos(i * mul) * radius)
                  for i in range(segments)]
    else:
        points = [(cos(i * mul) * radius, 0, sin(i * mul) * radius)
                  for i in range(segments)]

    return [obj_mx @ (local_center + Vector(pt)) for pt in points]


def get_circle_lines(*args):
    """create line order of circles points"""
    pts = get_circle_pts(*args)
    res = []

    res.append(pts[0])
    res.append(pts[-1])

    for i in range(len(pts) - 1):
        res.append(pts[i])
        res.append(pts[i + 1])

    return res
