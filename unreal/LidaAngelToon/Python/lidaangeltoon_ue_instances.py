# ============================================================================
# lidaangeltoon_ue_instances.py  -  LidaAngelToon for Unreal Engine 5: Material Instance helpers
#
# SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.0
# Copyright (c) 2026 Lida
#
# Generic helpers (no character data in here):
#   make_instance(path, parent, scalars, vectors, textures, switches, two_sided=None)
#   core_values(inputs, prefix='')  -> (scalars, vectors) for the 32 LidaAngelToon values
#   import_texture_file(file, folder, name, kind)  kinds: 'base' (sRGB colour), 'mask' (linear RGBA),
#                                                  'matcap' (sRGB, clamp, no mips)
# Values use the spec v1 names (HLSL / UE parameter names), e.g. {'ShadeTint1': [0.7, 0.72, 0.89], 'ShadeShift1': 0.05, ...}.
# ============================================================================
import os
import unreal

at = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary

CORE_FLOAT3 = ['ShadeTint1', 'ShadeTint2', 'NormalOverride', 'LitTint', 'RimColor', 'SpecColor', 'TerminatorColor', 'BaseLiftColor']
CORE_FLOAT = ['ShadeShift1', 'ShadeSoft1', 'ShadeShift2', 'ShadeSoft2', 'UseShadeTexture', 'ReceiveShadow', 'NormalOverrideMix',
              'RimStrength', 'RimWidth', 'RimSoft', 'RimLitBias', 'SpecStrength', 'SpecSize', 'SpecSoft', 'MatCapAddStrength',
              'MatCapMulStrength', 'Unlit', 'HighlightKnee', 'OcclusionShift', 'OcclusionDarken', 'TerminatorStrength',
              'TerminatorWidth', 'BaseLift', 'BaseSaturation']


def core_values(inputs, prefix=''):
    """Split a spec v1 value dict into scalar / vector parameters (prefix 'L2_' for the 2nd layer)."""
    sc, ve = {}, {}
    for k, v in inputs.items():
        if k in CORE_FLOAT3:
            ve[prefix + k] = list(v)[:3]
        elif k in CORE_FLOAT:
            sc[prefix + k] = float(v)
    missing = [k for k in CORE_FLOAT3 + CORE_FLOAT if k not in inputs]
    if missing:
        raise ValueError('missing values: %s' % missing)
    return sc, ve


def make_instance(path, parent, scalars=None, vectors=None, textures=None, switches=None, two_sided=None, rebuild=True):
    folder, name = path.rsplit('/', 1)
    mi = unreal.load_asset(path) if eal.does_asset_exist(path) else None
    if mi is not None and not rebuild:
        raise RuntimeError('exists: ' + path)
    if mi is None:
        mi = at.create_asset(name, folder, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, parent)
    mel.clear_all_material_instance_parameters(mi)
    for k, v in (scalars or {}).items():
        mel.set_material_instance_scalar_parameter_value(mi, k, float(v))
    for k, v in (vectors or {}).items():
        v = list(v) + [1.0] * (4 - len(v))
        mel.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(v[0], v[1], v[2], v[3]))
    for k, t in (textures or {}).items():
        mel.set_material_instance_texture_parameter_value(mi, k, t)
    for k, b in (switches or {}).items():
        mel.set_material_instance_static_switch_parameter_value(mi, k, bool(b))
    bpo = mi.get_editor_property('base_property_overrides')
    if two_sided is None:
        bpo.set_editor_property('override_two_sided', False)
    else:
        bpo.set_editor_property('override_two_sided', True)
        bpo.set_editor_property('two_sided', bool(two_sided))
    mi.set_editor_property('base_property_overrides', bpo)
    mel.update_material_instance(mi)
    eal.save_asset(path, only_if_is_dirty=False)
    return mi


def import_texture_file(file, folder, name, kind):
    path = folder + '/' + name
    task = unreal.AssetImportTask()
    task.set_editor_property('filename', file)
    task.set_editor_property('destination_path', folder)
    task.set_editor_property('destination_name', name)
    task.set_editor_property('automated', True)
    task.set_editor_property('replace_existing', True)
    task.set_editor_property('save', False)
    at.import_asset_tasks([task])
    t = unreal.load_asset(path)
    if t is None:
        raise RuntimeError('texture import failed: ' + file)
    # Set the compression BEFORE sRGB: UE may import a bluish colour texture as a normal map (TC_Normalmap, sRGB off), and
    # while the compression is still Normalmap a new sRGB = True is ignored (fixed in 0.1.0: some bluish colour base
    # maps stayed linear and looked whiter). The result is checked below.
    TCS = unreal.TextureCompressionSettings
    if kind == 'base':
        srgb, comp = True, TCS.TC_DEFAULT
    elif kind == 'base_exact':          # uncompressed 8-bit (for pixel comparisons)
        srgb, comp = True, TCS.TC_EDITOR_ICON
    elif kind == 'base_bc7':            # sRGB colour + alpha, BC7 (good quality for soft toon gradients)
        srgb, comp = True, TCS.TC_BC7
    elif kind == 'mask_bc7':            # linear RGBA (AngelToonMask), BC7: keeps all four channels, sampler type Linear Color
        srgb, comp = False, TCS.TC_BC7
    elif kind == 'mask':                # linear RGBA, uncompressed
        srgb, comp = False, TCS.TC_VECTOR_DISPLACEMENTMAP
    elif kind == 'matcap':              # sRGB, clamp to edge, no mips, uncompressed
        srgb, comp = True, TCS.TC_EDITOR_ICON
    else:
        raise ValueError(kind)
    t.set_editor_property('compression_settings', comp)
    t.set_editor_property('srgb', srgb)
    if kind == 'base_exact':
        t.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_WORLD)
        t.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
    elif kind == 'matcap':
        t.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_WORLD)
        t.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        t.set_editor_property('address_x', unreal.TextureAddress.TA_CLAMP)
        t.set_editor_property('address_y', unreal.TextureAddress.TA_CLAMP)
    if t.get_editor_property('srgb') != srgb or t.get_editor_property('compression_settings') != comp:
        raise RuntimeError('texture settings not applied: %s (srgb %s, compression %s)' % (
            path, t.get_editor_property('srgb'), t.get_editor_property('compression_settings')))
    eal.save_asset(path, only_if_is_dirty=False)
    return t
