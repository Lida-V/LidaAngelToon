# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Lida
"""LidaAngelToon: a model-independent Blender EEVEE material add-on."""

bl_info = {
    "name": "LidaAngelToon", "author": "Lida", "version": (0, 1, 0),
    "blender": (5, 2, 0), "location": "3D View > Sidebar > LidaAngelToon",
    "description": "Soft two-step toon shading with optional MatCap and outlines",
    "category": "Material", "doc_url": "https://github.com/Lida-V/LidaAngelToon",
}

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, PointerProperty, StringProperty
from . import shader


def sun_only(_self, obj):
    return obj.type == "LIGHT" and obj.data.type == "SUN"


class LATSettings(bpy.types.PropertyGroup):
    preset: EnumProperty(name="Material", items=[
        (k, label, "Apply this preset to the active material") for k, label in
        (("cloth", "Cloth"), ("skin", "Skin"), ("face", "Face"), ("hair", "Hair"),
         ("metal", "Metal"), ("gem", "Gem"), ("eye", "Eye"), ("nail", "Nail"),
         ("feather", "Feather"), ("mouth", "Mouth"))], default="cloth")
    sun: PointerProperty(name="Main sun", type=bpy.types.Object, poll=sun_only)
    make_single_user: BoolProperty(name="Copy shared material", default=True)
    receive_shadows: BoolProperty(name="Receive cast shadows (single sun)", default=False)
    ao_attribute: StringProperty(name="AO attribute", default="",
        description="Optional float mesh attribute: 1=open, 0=occluded. Empty means no baked AO")
    hair_streak: BoolProperty(name="Hair streak mask (requires UV)", default=False)
    outline: BoolProperty(name="Add outline", default=False)
    outline_mm: FloatProperty(name="Outline width (mm)", min=0.0, max=10.0, default=0.5)


class LAT_OT_apply(bpy.types.Operator):
    bl_idname = "lida_angel_toon.apply"
    bl_label = "Apply to selected meshes"
    bl_description = "Apply to each selected mesh's active material; keep the original nodes for Restore"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT" and any(o.type == "MESH" for o in context.selected_objects)

    def execute(self, context):
        cfg = context.scene.lida_angel_toon
        if context.scene.render.engine != "BLENDER_EEVEE":
            self.report({"ERROR"}, "Choose EEVEE in Render Properties first")
            return {"CANCELLED"}
        sun = shader.ensure_sun(context.scene, cfg.sun)
        cfg.sun = sun
        changed = 0
        errors = []
        for obj in context.selected_objects:
            if obj.type != "MESH":
                continue
            if cfg.ao_attribute.strip() and cfg.ao_attribute.strip() not in obj.data.attributes:
                errors.append(obj.name + ": AO attribute not found")
                continue
            if cfg.make_single_user and obj.data.users > 1:
                obj.data = obj.data.copy()
            mat = obj.active_material
            if mat is None:
                mat = bpy.data.materials.new("LidaAngelToon Material")
                mat.use_nodes = True
                obj.data.materials.append(mat)
            elif cfg.make_single_user and mat.users > 1:
                mat = mat.copy()
                obj.active_material = mat
            try:
                shader.apply_material(mat, cfg.preset, sun,
                    receive_shadows=cfg.receive_shadows, ao_attribute=cfg.ao_attribute,
                    hair_streak=cfg.hair_streak)
                if cfg.outline:
                    shader.add_outline(obj, cfg.outline_mm / 1000.0)
                changed += 1
            except ValueError as exc:
                errors.append(str(exc))
        if errors:
            self.report({"WARNING"}, "; ".join(errors))
        self.report({"INFO"}, "Applied LidaAngelToon to %d mesh(es)" % changed)
        return {"FINISHED"} if changed else {"CANCELLED"}


class LAT_OT_restore(bpy.types.Operator):
    bl_idname = "lida_angel_toon.restore"
    bl_label = "Restore original material"
    bl_description = "Restore the previous output and remove this add-on's outline modifier"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        n = 0
        for obj in context.selected_objects:
            if obj.type != "MESH":
                continue
            if obj.active_material and shader.restore_material(obj.active_material):
                n += 1
            for mod in list(obj.modifiers):
                if mod.name == "LidaAngelToon Outline":
                    obj.modifiers.remove(mod)
        self.report({"INFO"}, "Restored %d material(s); unused add-on assets remain available" % n)
        return {"FINISHED"}


class LAT_PT_panel(bpy.types.Panel):
    bl_label = "LidaAngelToon 0.1.0"
    bl_idname = "LAT_PT_material"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "LidaAngelToon"

    def draw(self, context):
        ui = self.layout
        cfg = context.scene.lida_angel_toon
        ui.label(text="EEVEE / active material of selected meshes")
        ui.prop(cfg, "preset")
        ui.prop(cfg, "sun")
        ui.prop(cfg, "make_single_user")
        ui.prop(cfg, "receive_shadows")
        if cfg.receive_shadows:
            ui.label(text="Use one Sun and zero world lighting", icon="INFO")
        ui.prop(cfg, "ao_attribute")
        if cfg.preset == "hair":
            ui.prop(cfg, "hair_streak")
        ui.prop(cfg, "outline")
        if cfg.outline:
            ui.prop(cfg, "outline_mm")
        ui.operator(LAT_OT_apply.bl_idname)
        ui.operator(LAT_OT_restore.bl_idname)
        ui.label(text="Fine tune: Shader Editor > LidaAngelToon")


CLASSES = (LATSettings, LAT_OT_apply, LAT_OT_restore, LAT_PT_panel)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.lida_angel_toon = PointerProperty(type=LATSettings)


def unregister():
    del bpy.types.Scene.lida_angel_toon
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
