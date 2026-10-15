# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Lida
"""Create primitive-only evidence; never loads an avatar or external model.

Run: blender -b --factory-startup --python tests/blender_smoke.py -- --output <directory>
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'blender'))
import lida_angel_toon as addon
from lida_angel_toon import shader


def mesh_hash(obj):
    return hashlib.sha256(repr([(tuple(v.co)) for v in obj.data.vertices]).encode()).hexdigest()


def main(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    # The command uses factory-startup; remove only that new test scene's defaults.
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    addon.register()
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 720
    scene.render.resolution_y = 360
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.view_settings.view_transform = 'Standard'
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.0
    scene.render.film_transparent = False
    sun = shader.ensure_sun(scene)
    records = []
    hashes = {}
    for i, preset in enumerate(('cloth', 'hair', 'metal')):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, location=((i - 1) * 2.5, 0, 0))
        obj = bpy.context.object
        obj.name = 'Test ' + preset
        bpy.ops.object.shade_smooth()
        mat = bpy.data.materials.new('Test Material ' + preset)
        mat.use_nodes = True
        nt = mat.node_tree
        bsdf = nt.nodes.get('Principled BSDF')
        color = nt.nodes.new('ShaderNodeRGB')
        color.outputs[0].default_value = (0.62, 0.55, 0.78, 1)
        nt.links.new(color.outputs[0], bsdf.inputs['Base Color'])
        obj.data.materials.append(mat)
        before = mesh_hash(obj)
        cfg = scene.lida_angel_toon
        cfg.sun = sun
        cfg.preset = preset
        cfg.outline = True
        cfg.outline_mm = 1.2
        cfg.hair_streak = preset == 'hair'
        assert bpy.ops.lida_angel_toon.apply() == {'FINISHED'}
        node = mat.node_tree.nodes.get('LidaAngelToon')
        assert node is not None and node.inputs['Base Color'].is_linked
        assert node.inputs['Base Color'].links[0].from_node == color
        assert mesh_hash(obj) == before
        assert shader.restore_material(mat)
        assert nt.nodes.get('Material Output').is_active_output
        # Reapplying must not duplicate nodes, group drivers, or outline modifiers.
        assert bpy.ops.lida_angel_toon.apply() == {'FINISHED'}
        assert sum(1 for n in nt.nodes if n.type == 'GROUP' and n.node_tree.name == shader.GROUP) == 1
        assert sum(1 for m in obj.modifiers if m.name == 'LidaAngelToon Outline') == 1
        hashes[obj.name] = before
        records.append({'preset': preset, 'geometry_unchanged': True, 'base_link_preserved': True,
                        'restore_reapply': True})
    # Also exercise constant alpha, cast-shadow input, and a user AO attribute.
    obj = bpy.context.object
    mat = obj.active_material
    attr = obj.data.attributes.new('test_occlusion', 'FLOAT', 'POINT')
    for item in attr.data:
        item.value = 0.8
    mat.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.8
    shader.apply_material(mat, 'metal', sun, receive_shadows=True, ao_attribute='test_occlusion')
    assert mat.surface_render_method == 'DITHERED'
    assert mat.node_tree.nodes['LidaAngelToon'].inputs['Occlusion'].is_linked
    # Return it to the opaque default for the overview image.
    mat.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 1.0
    shader.apply_material(mat, 'metal', sun)

    # Every user-facing preset must construct valid nodes without model data.
    for preset in shader.PRESETS:
        probe = bpy.data.materials.new('Preset Check ' + preset)
        probe.use_nodes = True
        shader.apply_material(probe, preset, sun)
        assert probe.node_tree.nodes['LidaAngelToon'].node_tree == bpy.data.node_groups[shader.GROUP]

    camera_data = bpy.data.cameras.new('Test Camera')
    camera = bpy.data.objects.new('Test Camera', camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0, -11, 3.5)
    direction = Vector((0, 0, 0)) - camera.location
    camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    camera_data.type = 'ORTHO'
    camera_data.ortho_scale = 9
    scene.camera = camera
    bpy.context.view_layer.update()
    assert not [d for d in bpy.data.node_groups[shader.GROUP].animation_data.drivers if not d.is_valid]
    assert len(bpy.data.node_groups[shader.GROUP].animation_data.drivers) == 7
    blend = output / 'primitive-smoke.blend'
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True, relative_remap=True)
    bpy.ops.wm.open_mainfile(filepath=str(blend), load_ui=False)
    scene = bpy.context.scene
    for name, before in hashes.items():
        assert mesh_hash(bpy.data.objects[name]) == before
    packed = [img.name for img in bpy.data.images if img.packed_file]
    assert len(packed) >= 4
    assert not [img.name for img in bpy.data.images if img.source == 'FILE' and not img.packed_file
                and not Path(bpy.path.abspath(img.filepath)).exists()]
    image = output / 'primitive-smoke.png'
    scene.render.filepath = str(image)
    bpy.ops.render.render(write_still=True)
    assert image.exists() and image.stat().st_size > 1000
    report = {'blender': bpy.app.version_string, 'addon': list(addon.bl_info['version']),
              'checks': records, 'alpha_and_ao_input': True, 'save_reload': True,
              'shared_group_drivers': 7, 'presets_built': len(shader.PRESETS), 'packed_images': len(packed),
              'render_file': image.name, 'render_sha256': hashlib.sha256(image.read_bytes()).hexdigest(),
              'model_inputs': 0}
    (output / 'smoke-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    addon.unregister()
    print('LIDA_ANGEL_TOON_SMOKE_OK', json.dumps(report))


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    main(parser.parse_args(args).output)
