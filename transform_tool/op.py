from math import radians

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatVectorProperty
from mathutils import Quaternion

from ..utils import get_pref

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
    panel_constraint: BoolProperty(name="Not Moving this Axis", default=False)
    matrix_basis: FloatVectorProperty(size=(4, 4), subtype="MATRIX")
    move_event_count = None

    @property
    def constraint_axis(self):
        constraint_axis_dict = {
            "X": (True, False, False),
            "Y": (False, True, False),
            "Z": (False, False, True),
            "VIEW": (False, False, False),
        }
        axis_set = constraint_axis_dict[self.axis]
        if self.panel_constraint and axis_set != (True, True, True):
            axis_set = (not axis_set[0], not axis_set[1], not axis_set[2])
        return axis_set

    def get_translate_ops_args(self, context):
        transform_pivot_point = context.scene.tool_settings.transform_pivot_point
        orientation = context.window.scene.transform_orientation_slots[0].type

        trans_args = {
            "mode": "TRANSLATION",
            "release_confirm": True,
            "constraint_axis": self.constraint_axis,
        }

        if transform_pivot_point == "INDIVIDUAL_ORIGINS":
            ...
        else:
            if orientation == "NORMAL":
                if self.axis in ("X", "Y", "Z"):
                    trans_args["orient_axis"] = self.axis
                trans_args["orient_type"] = "NORMAL"
        return trans_args

    def get_orient_matrix(self, context):
        mat = self.matrix_basis.copy().to_3x3()

        if self.axis == "X":
            mat = mat @ Quaternion((0.0, 1.0, 0.0), radians(90)).to_matrix().to_3x3()
        elif self.axis == "Y":
            mat = mat @ Quaternion((1.0, 0.0, 0.0), radians(90)).to_matrix().to_3x3()
        return mat

    def translate(self, context, is_copy=False):
        trans_args = self.get_translate_ops_args(context)

        if is_copy:
            trans_args.pop("mode")
            bpy.ops.object.duplicate_move("INVOKE_DEFAULT",
                                          OBJECT_OT_duplicate={"linked": False if is_copy != "INSTANCE" else True,
                                                               "mode": "TRANSLATION"},
                                          TRANSFORM_OT_translate=trans_args)
        else:
            bpy.ops.transform.transform("INVOKE_DEFAULT", **trans_args)

    def translate_mesh_extrude(self, context):
        orientation = context.window.scene.transform_orientation_slots[0].type
        args = {"constraint_axis": self.constraint_axis, "release_confirm": True}
        if orientation == "NORMAL":
            args["orient_type"] = "NORMAL"
        bpy.ops.mesh.extrude_context_move(
            "INVOKE_DEFAULT",
            MESH_OT_extrude_context={"use_normal_flip": False, "mirror": False},
            TRANSFORM_OT_translate=args,
        )

    def scale(self, context, ):
        if self.axis in ("VIEW", "Z"):
            bpy.ops.mesh.inset("INVOKE_DEFAULT", release_confirm=True)
        else:
            bpy.ops.mesh.extrude_context("EXEC_DEFAULT")
            bpy.ops.transform.resize("INVOKE_DEFAULT", constraint_axis=self.constraint_axis, release_confirm=True)

    def move(self, context, event):
        if context.mode == "OBJECT":
            is_copy = False if not event.shift else context.scene.move_view_tool.duplicate
            self.translate(context, is_copy=is_copy)
        elif context.mode == "EDIT_MESH":
            if event.shift:
                self.translate_mesh_extrude(context)
            else:
                self.translate(context, is_copy=False)

    def invoke(self, context, event):
        self.move_event_count = 0
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        pref = get_pref()
        if event.value == "RELEASE" and event.type == "LEFTMOUSE":
            # PASS select operator 选择网格
            bpy.ops.view3d.select("INVOKE_DEFAULT", extend=event.shift, enumerate=event.alt)
            return {"FINISHED"}
        elif event.type == "MOUSEMOVE":
            self.move_event_count += 1
            if self.move_event_count > pref.transform_gizmo_move_event_count:
                if context.mode == "EDIT_MESH" and event.ctrl:
                    self.scale(context)
                else:
                    self.move(context, event)
                return {"FINISHED"}
        return {"RUNNING_MODAL"}


classes = (
    PH_OT_translate,
)

register, unregister = bpy.utils.register_classes_factory(classes)
