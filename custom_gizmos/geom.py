import bpy


def from_mesh_get_triangle_face_co(mesh: 'bpy.types.Mesh') -> list:
    """
    :param mesh: input mesh read vertex
    :type mesh: bpy.data.meshes
    :return list: vertex coordinate list[[cox,coy,coz],[cox,coy,coz]...]
    """
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    bmesh.ops.triangulate(bm, faces=bm.faces)
    co_list = [list(float(format(j, ".3f")) for j in vert.co) for face in
               bm.faces for vert in face.verts]
    bm.free()
    return co_list


def from_selected_obj_generate_json():
    """Export selected object vertex data as gizmo custom paint data
    The output file should be in the blender folder
    gizmo.json
    """
    import json
    data = {}
    for obj in bpy.context.selected_objects:
        data[obj.name] = from_mesh_get_triangle_face_co(obj.data)
    with open('1gizmo.json', 'w+') as f:
        f.write(json.dumps(data))


if __name__ == "__main__":
    from_selected_obj_generate_json()
