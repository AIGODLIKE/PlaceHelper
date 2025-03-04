from math import radians

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatVectorProperty
from mathutils import Quaternion

C_OBJECT_TYPE_HAS_BBOX = {"MESH", "CURVE", "FONT", "LATTICE"}

move_view_tool_props = lambda: bpy.context.scene.move_view_tool


class PH_OT_translate(bpy.types.Operator):
    bl_idname = "ph.translate"
    bl_label = "Translate"
    bl_description = "Translate"
    # bl_options = {"REGISTER", "UNDO"}

    axis: EnumProperty(
        name="Axis",
        description="Axis",
        items=[
            ("X", "X", "", "", 0),
            ("Y", "Y", "", "", 1),
            ("Z", "Z", "", "", 2),
            ("VIEW", "View", "", "", 3),
        ],
        default="VIEW",
    )
    invert_constraint: BoolProperty(name="Not Moving this Axis", default=False)
    matrix_basis: FloatVectorProperty(size=(4, 4), subtype="MATRIX")
    pp = None

    def get_orient_matrix(self, context):
        mat = self.matrix_basis.copy().to_3x3()

        if self.axis == "X":
            mat = mat @ Quaternion((0.0, 1.0, 0.0), radians(90)).to_matrix().to_3x3()
        elif self.axis == "Y":
            mat = mat @ Quaternion((1.0, 0.0, 0.0), radians(90)).to_matrix().to_3x3()
        return mat

    @staticmethod
    def translate(self, context, axis_set, matrix_orient, copy=None):
        tpp = context.scene.tool_settings.transform_pivot_point
        os = context.window.scene.transform_orientation_slots[0].type

        print("translate", tpp, os, flush=True)
        trans_args = {
            "mode": "TRANSLATION",
            "release_confirm": True,
            "constraint_axis": axis_set,
        }

        if tpp == "INDIVIDUAL_ORIGINS":
            ...
        else:
            if os == "NORMAL":
                if self.axis in ("X", "Y", "Z"):
                    trans_args["orient_axis"] = self.axis
                trans_args["orient_type"] = "NORMAL"
                # trans_args["orient_matrix"] = matrix_orient
                # trans_args["center_override"] = self.pp
                # trans_args["orient_matrix_type"] = "NORMAL"

        if copy is None:
            bpy.ops.transform.transform('INVOKE_DEFAULT', **trans_args)
        else:
            trans_args.pop("mode")
            bpy.ops.object.duplicate_move("INVOKE_DEFAULT",
                                          OBJECT_OT_duplicate={"linked": False if copy != "INSTANCE" else True,
                                                               "mode": "TRANSLATION"},
                                          TRANSFORM_OT_translate=trans_args)

    def modal(self, context, event):
        if event.value == "RELEASE" or event.type in {"RET"}:
            return {"FINISHED"}
        elif event.type in {"ESC", "RIGHTMOUSE"}:
            return {"CANCELLED"}
        return {"RUNNING_MODAL"}

    def invoke(self, context, event):
        os = context.window.scene.transform_orientation_slots[0].type

        if self.pp is None:
            self.pp = self.matrix_basis.translation

        constraint_axis_dict = {
            "X": (True, False, False),
            "Y": (False, True, False),
            "Z": (False, False, True),
            "VIEW": (False, False, False),
        }
        axis_set = constraint_axis_dict[self.axis]
        if self.invert_constraint and axis_set != (True, True, True):
            axis_set = (not axis_set[0], not axis_set[1], not axis_set[2])

        if context.mode == "OBJECT":
            self.translate(self, context, axis_set, self.get_orient_matrix(context),
                           copy=None if not event.shift else context.scene.move_view_tool.duplicate)

        elif context.mode == "EDIT_MESH":
            if event.shift:
                args = {"constraint_axis": axis_set, "release_confirm": True}
                if os == "NORMAL":
                    args["orient_type"] = "NORMAL"

                bpy.ops.mesh.extrude_context_move(
                    "INVOKE_DEFAULT",
                    MESH_OT_extrude_context={"use_normal_flip": False, "mirror": False},
                    TRANSFORM_OT_translate=args,
                )
            else:
                self.translate(self, context, axis_set, self.get_orient_matrix(context), copy=None)
        return {"RUNNING_MODAL"}


classes = (
    PH_OT_translate,
)

register, unregister = bpy.utils.register_classes_factory(classes)
