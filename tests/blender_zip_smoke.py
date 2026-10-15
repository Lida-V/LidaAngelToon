# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Lida
"""Install the built addon ZIP into an isolated Blender scripts directory.

Set BLENDER_USER_SCRIPTS before starting Blender to a new writable test folder.
No avatar, personal preferences, or engine project is opened.
"""
import argparse
import json
import os
from pathlib import Path
import sys

import addon_utils
import bpy


def main(archive, output):
    scratch = os.environ.get('BLENDER_USER_SCRIPTS')
    if not scratch:
        raise RuntimeError('Set BLENDER_USER_SCRIPTS to an isolated test directory')
    scratch = Path(scratch).resolve()
    archive = Path(archive).resolve()
    output = Path(output).resolve()
    if scratch == Path.home() or scratch == Path(scratch.anchor):
        raise RuntimeError('Test scripts directory must be a dedicated subfolder')
    scratch.mkdir(parents=True, exist_ok=True)
    result = bpy.ops.preferences.addon_install(filepath=str(archive), overwrite=True, target='DEFAULT')
    assert result == {'FINISHED'}
    bpy.utils.refresh_script_paths()
    addon_utils.modules_refresh()
    module = addon_utils.enable('lida_angel_toon', default_set=False, persistent=False)
    assert module is not None
    module_path = Path(module.__file__).resolve()
    assert module_path.is_relative_to(scratch), 'The installed ZIP must be tested, not the source tree'
    assert hasattr(bpy.types.Scene, 'lida_angel_toon')
    bpy.context.scene.render.engine = 'BLENDER_EEVEE'
    bpy.ops.mesh.primitive_cube_add()
    cfg = bpy.context.scene.lida_angel_toon
    cfg.preset = 'cloth'
    assert bpy.ops.lida_angel_toon.apply() == {'FINISHED'}
    assert bpy.context.object.active_material.node_tree.nodes.get('LidaAngelToon')
    addon_utils.disable('lida_angel_toon', default_set=False)
    assert not hasattr(bpy.types.Scene, 'lida_angel_toon')
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {'blender': bpy.app.version_string, 'zip_install': True,
              'isolated_scripts': True, 'enable_apply_disable': True, 'model_inputs': 0}
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('LIDA_ANGEL_TOON_ZIP_SMOKE_OK', json.dumps(report))


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    main(args.archive, args.output)
