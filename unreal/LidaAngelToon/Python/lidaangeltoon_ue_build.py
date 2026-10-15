# ============================================================================
# lidaangeltoon_ue_build.py  -  LidaAngelToon for Unreal Engine 5 (built and tested on UE 5.8)
#
# SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.0
# Copyright (c) 2026 Lida
#
# Builds the generic LidaAngelToon assets with the Unreal Python API (editor only):
#   /Game/LidaAngelToon/MPC_LidaAngelToon                         key light direction / colour / switches
#   /Game/LidaAngelToon/Materials/M_LidaAngelToon                 Unlit, opaque (toon shading in a Custom node)
#   /Game/LidaAngelToon/Materials/M_LidaAngelToon_Translucent     Unlit, translucent (opacity = BaseMap.a x BaseColor.a)
#   /Game/LidaAngelToon/Materials/M_LidaAngelToon_Outline         Unlit, masked, two-sided inverted hull (back faces only, WPO push)
#   /Game/LidaAngelToon/Materials/M_LidaAngelToon_MultiplyLayer   Unlit, modulate: dst *= lerp(1, LayerColor, BaseMap.a)
#   /Game/LidaAngelToon/Textures/T_LidaAngelToon_*                small default textures (white, black, grey, default mask)
#   /Game/LidaAngelToon/Blueprints/BP_LidaAngelToonKeyLight       copies a light's direction into the MPC every tick
#
# Usage (editor commandlet):
#   UnrealEditor-Cmd.exe <project>.uproject -run=pythonscript -script=<this file>
#   environment: LIDAANGELTOON_HLSL_DIR = folder with LidaAngelToon_UECustom_Shade.txt / _OutlineWidth.txt
#                (generated from LidaAngelToonCore.hlsl by make_ue_custom338.py)
#                LIDAANGELTOON_REBUILD = 1 to delete and rebuild existing LidaAngelToon assets of this script
#
# Nothing character specific lives here: per-material values go into Material Instances
# (see lidaangeltoon_ue_instances.py and the material table).
# ============================================================================
import os
import json
import unreal

ROOT = '/Game/LidaAngelToon'
MAT_DIR = ROOT + '/Materials'
TEX_DIR = ROOT + '/Textures'
BP_DIR = ROOT + '/Blueprints'
MPC_PATH = ROOT + '/MPC_LidaAngelToon'

at = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
LOG = []


def log(msg):
    LOG.append(msg)
    unreal.log('LidaAngelToon build: ' + msg)


# ---------------------------------------------------------------------------- parameter list (spec v1)
# (name, type, default). float3 defaults are RGB. Names = UE parameter names of the spec (= HLSL member names).
CORE_PARAMS = [
    ('ShadeTint1', 'float3', (0.85, 0.85, 0.92)), ('ShadeShift1', 'float', 0.05), ('ShadeSoft1', 'float', 0.3),
    ('ShadeTint2', 'float3', (0.85, 0.85, 0.92)), ('ShadeShift2', 'float', -0.75), ('ShadeSoft2', 'float', 0.3),
    ('UseShadeTexture', 'float', 0.0), ('ReceiveShadow', 'float', 0.85),
    ('NormalOverride', 'float3', (0.0, 0.0, 0.0)), ('NormalOverrideMix', 'float', 0.0),
    ('LitTint', 'float3', (1.0, 1.0, 1.0)),
    ('RimColor', 'float3', (0.92, 0.94, 1.0)), ('RimStrength', 'float', 0.08), ('RimWidth', 'float', 0.25), ('RimSoft', 'float', 0.15),
    ('RimLitBias', 'float', 0.4),
    ('SpecColor', 'float3', (1.0, 1.0, 1.0)), ('SpecStrength', 'float', 0.0), ('SpecSize', 'float', 0.97), ('SpecSoft', 'float', 0.02),
    ('MatCapAddStrength', 'float', 0.0), ('MatCapMulStrength', 'float', 0.0), ('Unlit', 'float', 0.0), ('HighlightKnee', 'float', 1.0),
    ('OcclusionShift', 'float', 1.0), ('OcclusionDarken', 'float', 0.35),
    ('TerminatorColor', 'float3', (1.0, 0.82, 0.8)), ('TerminatorStrength', 'float', 0.0), ('TerminatorWidth', 'float', 0.1),
    ('BaseLift', 'float', 0.0), ('BaseLiftColor', 'float3', (1.0, 0.97, 0.96)), ('BaseSaturation', 'float', 1.0),
]
GROUP_OF = {}
for n, t, d in CORE_PARAMS:
    if n.startswith('Shade') or n == 'UseShadeTexture' or n == 'LitTint':
        GROUP_OF[n] = '02 Shade'
    elif n.startswith('Rim') or n.startswith('Spec'):
        GROUP_OF[n] = '03 Rim and Spec'
    elif n.startswith('MatCap'):
        GROUP_OF[n] = '04 MatCap'
    elif n.startswith('Occlusion') or n.startswith('Terminator') or n == 'ReceiveShadow' or n.startswith('NormalOverride'):
        GROUP_OF[n] = '05 Occlusion, shadow, border'
    else:
        GROUP_OF[n] = '01 Base'
PIXEL_PINS = ['N', 'L', 'V', 'KeyColor', 'ShadowedNL', 'BaseColor', 'ShadeTexture', 'Occlusion', 'ReceiveShadowMask',
              'MatCapAdd', 'MatCapMul', 'MatCapAddMask']

MPC_SCALARS = [('KeyOverride', 0.0), ('ShadowGain', 1.25), ('AmbientMix', 0.0), ('ExposureLock', 0.0)]
# KeyDir / KeyDirOverride = direction TO the key light in UE world space (w unused)
MPC_VECTORS = [('KeyDir', (-0.668946, 0.5256, 0.5256, 0.0)), ('KeyDirOverride', (-0.668946, 0.5256, 0.5256, 0.0)),
               ('KeyColor', (1.0, 1.0, 1.0, 1.0)), ('AmbientColor', (1.0, 1.0, 1.0, 1.0))]

# ---------------------------------------------------------------------------- small HLSL snippets (own code, ASCII)
SNIP_NORMAL = ('// LidaAngelToon: shading normal = vertex normal, flipped toward the viewer on back faces\n'
               'float3 n = Nv;\n'
               'float l2 = dot(n, n);\n'
               'n = (l2 > 0.0) ? n * rsqrt(l2) : float3(0.0, 0.0, 1.0);\n'
               'return n * ((Sgn < 0.0) ? -1.0 : 1.0);\n')
SNIP_MATCAP_UV = ('// LidaAngelToon: MatCap UV in Unreal (view space +X right, +Y up; texture V = 0 is the top row)\n'
                  'float3 n = mul(Nw, (float3x3)ResolvedView.TranslatedWorldToView);\n'
                  'float l2 = dot(n, n);\n'
                  'n = (l2 > 0.0) ? n * rsqrt(l2) : float3(0.0, 0.0, 0.0);\n'
                  'return float2(n.x * 0.5 + 0.5, 0.5 - n.y * 0.5);\n')
SNIP_SHADOWED_NL = ('// LidaAngelToon: N.L with the key-light shadow (Unlit in Unreal: no shadow map, Atten = 1)\n'
                    'float l2 = dot(Lw, Lw);\n'
                    'float3 l = (l2 > 0.0) ? Lw * rsqrt(l2) : float3(0.0, 0.0, 1.0);\n'
                    'return clamp(dot(Nw, l), 0.0, 1.0) * Atten * Gain;\n')
SNIP_OUTLINE_VIEW = ('// LidaAngelToon outline (vertex shader): clip w, projection [1][1], view height in pixels\n'
                     'float4 c = mul(float4(Parameters.WorldPosition, 1.0), ResolvedView.TranslatedWorldToClip);\n'
                     'return float3(c.w, ResolvedView.ViewToClip[1][1], ResolvedView.ViewSizeAndInvSize.y);\n')
SNIP_DITHER = ('// LidaAngelToon: alpha for Masked instances. Dither = 1: keep a pixel when alpha > per-frame noise (TSR averages it,\n'
               '// like Blender "Dithered"); Dither = 0: plain cut-out at Cutoff.\n'
               'float n = InterleavedGradientNoise(Parameters.SvPosition.xy, ResolvedView.StateFrameIndexMod8);\n'
               'float t = (Dither > 0.5) ? n : Cutoff;\n'
               'return (Alpha > t) ? 1.0 : 0.0;\n')
SNIP_OUTLINE_MASK = ('// LidaAngelToon outline (pixel shader): keep back faces of the hull where the outline mask > 0.5\n'
                     'return (Sgn < 0.0 && Mb > 0.5 && Vis > 0.5) ? 1.0 : 0.0;\n')


def hlsl_dir():
    d = os.environ.get('LIDAANGELTOON_HLSL_DIR')
    if not d:
        d = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Source', 'hlsl')
    return os.path.abspath(d)


def source_dir():
    d = os.environ.get('LIDAANGELTOON_SOURCE_DIR')
    if not d:
        d = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Source')
    return os.path.abspath(d)


def read_custom(name):
    p = os.path.join(hlsl_dir(), name)
    s = open(p, 'r', encoding='ascii').read()
    return s


# ---------------------------------------------------------------------------- helpers
class Graph:
    def __init__(self, mat):
        self.mat = mat

    def node(self, cls, x, y, **props):
        e = mel.create_material_expression(self.mat, cls, x, y)
        for k, v in props.items():
            e.set_editor_property(k, v)
        return e

    def scalar(self, name, default, x, y, group=None):
        e = self.node(unreal.MaterialExpressionScalarParameter, x, y, parameter_name=name, default_value=float(default))
        if group:
            e.set_editor_property('group', group)
        return e

    def vector(self, name, default, x, y, group=None):
        d = list(default) + [1.0] * (4 - len(default))
        e = self.node(unreal.MaterialExpressionVectorParameter, x, y, parameter_name=name,
                      default_value=unreal.LinearColor(d[0], d[1], d[2], d[3]))
        if group:
            e.set_editor_property('group', group)
        return e

    def rgb(self, src, out, x, y):
        m = self.node(unreal.MaterialExpressionComponentMask, x, y, r=True, g=True, b=True, a=False)
        self.link(src, out, m, '')
        return m

    def chan(self, src, out, c, x, y):
        m = self.node(unreal.MaterialExpressionComponentMask, x, y, r=(c == 'r'), g=(c == 'g'), b=(c == 'b'), a=(c == 'a'))
        self.link(src, out, m, '')
        return m

    def tex(self, name, texture, sampler, x, y, group=None, uv=None):
        e = self.node(unreal.MaterialExpressionTextureSampleParameter2D, x, y, parameter_name=name, texture=texture,
                      sampler_type=sampler)
        if group:
            e.set_editor_property('group', group)
        if uv is not None:
            self.link(uv[0], uv[1], e, 'UVs')
        return e

    def custom(self, code, inputs, out_type, desc, x, y):
        e = self.node(unreal.MaterialExpressionCustom, x, y, code=code, output_type=out_type, description=desc)
        ins = []
        for n in inputs:
            ci = unreal.CustomInput()
            ci.set_editor_property('input_name', n)
            ins.append(ci)
        e.set_editor_property('inputs', ins)
        return e

    def mpc(self, collection, name, x, y):
        e = mel.create_material_expression(self.mat, unreal.MaterialExpressionCollectionParameter, x, y)
        e.set_editor_property('collection', collection)
        e.set_editor_property('parameter_name', name)
        return e

    def link(self, a, a_out, b, b_in):
        ok = mel.connect_material_expressions(a, a_out, b, b_in)
        if not ok:
            raise RuntimeError('connect failed %s.%r -> %s.%r (inputs %s)' % (
                a.get_name(), a_out, b.get_name(), b_in, mel.get_material_expression_input_names(b)))

    def out(self, a, a_out, prop):
        ok = mel.connect_material_property(a, a_out, prop)
        if not ok:
            raise RuntimeError('connect to property failed %s.%r -> %s' % (a.get_name(), a_out, prop))

    def lerp(self, a, b, alpha, x, y):
        e = self.node(unreal.MaterialExpressionLinearInterpolate, x, y)
        for src, pin in ((a, 'A'), (b, 'B'), (alpha, 'Alpha')):
            if isinstance(src, (int, float)):
                e.set_editor_property('const_' + pin.lower(), float(src))
            else:
                self.link(src[0], src[1], e, pin)
        return e

    def mul(self, a, b, x, y):
        e = self.node(unreal.MaterialExpressionMultiply, x, y)
        for src, pin in ((a, 'A'), (b, 'B')):
            if isinstance(src, (int, float)):
                e.set_editor_property('const_' + pin.lower(), float(src))
            else:
                self.link(src[0], src[1], e, pin)
        return e

    def add(self, a, b, x, y):
        e = self.node(unreal.MaterialExpressionAdd, x, y)
        self.link(a[0], a[1], e, 'A')
        self.link(b[0], b[1], e, 'B')
        return e

    def switch(self, name, default, true_src, false_src, x, y, group=None):
        e = self.node(unreal.MaterialExpressionStaticSwitchParameter, x, y, parameter_name=name, default_value=bool(default))
        if group:
            e.set_editor_property('group', group)
        self.link(true_src[0], true_src[1], e, 'True')
        self.link(false_src[0], false_src[1], e, 'False')
        return e


def existing(path):
    """Existing asset to rebuild in place (LIDAANGELTOON_REBUILD=1), or None. Assets are never deleted."""
    if eal.does_asset_exist(path):
        if os.environ.get('LIDAANGELTOON_REBUILD') == '1':
            log('rebuild in place ' + path)
            return unreal.load_asset(path)
        raise RuntimeError('asset exists (set LIDAANGELTOON_REBUILD=1 to rebuild in place): ' + path)
    return None


def delete_if(path):
    # kept for the texture import (replace_existing re-imports over the same asset)
    existing(path)


def new_material(name, folder=MAT_DIR):
    path = folder + '/' + name
    m = existing(path)
    if m is not None:
        # UE 5.8: one delete_all_material_expressions call removes only about half of the nodes, so repeat
        for _ in range(40):
            if mel.get_num_material_expressions(m) == 0:
                break
            mel.delete_all_material_expressions(m)
        if mel.get_num_material_expressions(m) != 0:
            raise RuntimeError('could not clear ' + path)
        for p in (unreal.MaterialProperty.MP_EMISSIVE_COLOR, unreal.MaterialProperty.MP_OPACITY,
                  unreal.MaterialProperty.MP_OPACITY_MASK, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET):
            try:
                mel.disconnect_material_property(m, p)
            except Exception:  # noqa
                pass
        m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_OPAQUE)
        m.set_editor_property('two_sided', False)
    else:
        m = at.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    for u in (unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH, unreal.MaterialUsage.MATUSAGE_MORPH_TARGETS,
              unreal.MaterialUsage.MATUSAGE_STATIC_LIGHTING):
        try:
            mel.set_base_material_usage(m, u)
        except Exception:  # noqa
            pass
    return m


# ---------------------------------------------------------------------------- default textures
def write_png(path, w, h, rgba_bytes):
    """Minimal RGBA8 PNG writer (stdlib only)."""
    import struct, zlib
    raw = b''.join(b'\x00' + rgba_bytes[y * w * 4:(y + 1) * w * 4] for y in range(h))

    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    data = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)) +         chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b'')
    open(path, 'wb').write(data)


def import_texture(file, folder, name, srgb, compression, mips=True, clamp=False, lod_group=None):
    path = folder + '/' + name
    delete_if(path)
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
    t.set_editor_property('srgb', srgb)
    t.set_editor_property('compression_settings', compression)
    if not mips:
        t.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    if clamp:
        t.set_editor_property('address_x', unreal.TextureAddress.TA_CLAMP)
        t.set_editor_property('address_y', unreal.TextureAddress.TA_CLAMP)
    if lod_group is not None:
        t.set_editor_property('lod_group', lod_group)
    eal.save_asset(path, only_if_is_dirty=False)
    return t


def make_texture(name, rgba8, srgb):
    """4x4 texture of one colour (uncompressed, no mips). rgba8 = 8-bit codes as stored."""
    d = os.path.join(source_dir(), 'textures')
    os.makedirs(d, exist_ok=True)
    f = os.path.join(d, name + '.png')
    write_png(f, 4, 4, bytes(bytearray(list(rgba8) * 16)))
    return import_texture(f, TEX_DIR, name, srgb, unreal.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP, mips=False)


# ---------------------------------------------------------------------------- MPC
def make_mpc():
    mpc = existing(MPC_PATH)
    if mpc is not None:
        have = set(str(n) for n in mpc.get_scalar_parameter_names()) | set(str(n) for n in mpc.get_vector_parameter_names())
        if all(n in have for n, d in MPC_SCALARS + MPC_VECTORS):
            log('MPC kept as is (all parameters present)')
            return mpc
    else:
        mpc = at.create_asset('MPC_LidaAngelToon', ROOT, unreal.MaterialParameterCollection, unreal.MaterialParameterCollectionFactoryNew())
    sp = []
    for n, d in MPC_SCALARS:
        p = unreal.CollectionScalarParameter()
        p.set_editor_property('parameter_name', n)
        p.set_editor_property('default_value', d)
        sp.append(p)
    vp = []
    for n, d in MPC_VECTORS:
        p = unreal.CollectionVectorParameter()
        p.set_editor_property('parameter_name', n)
        p.set_editor_property('default_value', unreal.LinearColor(*d))
        vp.append(p)
    mpc.set_editor_property('scalar_parameters', sp)
    mpc.set_editor_property('vector_parameters', vp)
    eal.save_asset(MPC_PATH, only_if_is_dirty=False)
    log('MPC with %d scalars, %d vectors' % (len(sp), len(vp)))
    return mpc


# ---------------------------------------------------------------------------- shared toon graph
def toon_graph(m, mpc, tex, translucent):
    g = Graph(m)
    shade_code = read_custom('LidaAngelToon_UECustom_Shade.txt')
    X = -3400
    # ---- per-pixel geometry
    vn = g.node(unreal.MaterialExpressionVertexNormalWS, X, -1200)
    sgn = g.node(unreal.MaterialExpressionTwoSidedSign, X, -1100)
    nrm = g.custom(SNIP_NORMAL, ['Nv', 'Sgn'], unreal.CustomMaterialOutputType.CMOT_FLOAT3, 'AT_Normal', X + 300, -1150)
    g.link(vn, '', nrm, 'Nv'); g.link(sgn, '', nrm, 'Sgn')
    kd = g.rgb(g.mpc(mpc, 'KeyDir', X, -950), '', X + 250, -950)
    kdo = g.rgb(g.mpc(mpc, 'KeyDirOverride', X, -850), '', X + 250, -850)
    kov = g.mpc(mpc, 'KeyOverride', X, -750)
    L = g.lerp((kd, ''), (kdo, ''), (kov, ''), X + 450, -900)
    V = g.node(unreal.MaterialExpressionCameraVectorWS, X + 450, -700)
    kc = g.rgb(g.mpc(mpc, 'KeyColor', X, -600), '', X + 250, -600)
    sg = g.mpc(mpc, 'ShadowGain', X, -500)
    snl = g.custom(SNIP_SHADOWED_NL, ['Nw', 'Lw', 'Atten', 'Gain'], unreal.CustomMaterialOutputType.CMOT_FLOAT1, 'AT_ShadowedNL', X + 700, -600)
    g.link(nrm, '', snl, 'Nw'); g.link(L, '', snl, 'Lw'); g.link(sg, '', snl, 'Gain')
    one = g.node(unreal.MaterialExpressionConstant, X + 450, -500, r=1.0)
    g.link(one, '', snl, 'Atten')
    # ---- textures
    base = g.tex('BaseMap', tex['white'], unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, X, -300, '01 Base')
    bcol = g.vector('BaseColor', (1, 1, 1, 1), X, -100, '01 Base')
    bc = g.mul((base, 'RGB'), (g.rgb(bcol, '', X + 250, -100), ''), X + 450, -250)
    shm = g.tex('ShadeMap', tex['white'], unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, X, 50, '02 Shade')
    shc = g.vector('ShadeColor', (1, 1, 1, 1), X, 150, '02 Shade')
    shmc = g.mul((shm, 'RGB'), (g.rgb(shc, '', X + 250, 150), ''), X + 450, 100)
    # mask: texture (default) or vertex colour (static switch)
    mtex = g.tex('AngelToonMask', tex['mask'], unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR, X, 250, '06 Mask')
    vc = g.node(unreal.MaterialExpressionVertexColor, X, 450)
    vca = g.node(unreal.MaterialExpressionAppendVector, X + 250, 450)
    g.link(vc, '', vca, 'A'); g.link(vc, 'A', vca, 'B')
    msk = g.switch('MaskFromVertexColor', False, (vca, ''), (mtex, 'RGBA'), X + 450, 300, '06 Mask')
    mR = g.chan(msk, '', 'r', X + 650, 200)
    mG = g.chan(msk, '', 'g', X + 650, 300)
    mA = g.chan(msk, '', 'a', X + 650, 400)
    rsu = g.scalar('ReceiveShadowUseMaskA', 0.0, X + 650, 500, '06 Mask')
    rsm = g.lerp(1.0, (mA, ''), (rsu, ''), X + 900, 450)
    mau = g.scalar('MatCapAddUseMaskA', 0.0, X + 650, 600, '06 Mask')
    mam = g.lerp(1.0, (mA, ''), (mau, ''), X + 900, 580)
    # MatCap: UV from the view-space normal, add / multiply = texture or colour
    mcuv = g.custom(SNIP_MATCAP_UV, ['Nw'], unreal.CustomMaterialOutputType.CMOT_FLOAT2, 'AT_MatCapUV', X + 300, 750)
    g.link(nrm, '', mcuv, 'Nw')
    mca_t = g.tex('MatCapAddMap', tex['black'], unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, X + 550, 700, '04 MatCap', uv=(mcuv, ''))
    mcm_t = g.tex('MatCapMulMap', tex['grey'], unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, X + 550, 950, '04 MatCap', uv=(mcuv, ''))

    def matcap_pair(prefix, y):
        ac = g.rgb(g.vector(prefix + 'MatCapAddColor', (0, 0, 0, 1), X + 800, y, '04 MatCap'), '', X + 1050, y)
        au = g.scalar(prefix + 'UseMatCapAddMap', 0.0, X + 800, y + 100, '04 MatCap')
        a = g.lerp((ac, ''), (mca_t, 'RGB'), (au, ''), X + 1250, y)
        mc = g.rgb(g.vector(prefix + 'MatCapMulColor', (0.5, 0.5, 0.5, 1), X + 800, y + 200, '04 MatCap'), '', X + 1050, y + 200)
        mu = g.scalar(prefix + 'UseMatCapMulMap', 0.0, X + 800, y + 300, '04 MatCap')
        b = g.lerp((mc, ''), (mcm_t, 'RGB'), (mu, ''), X + 1250, y + 200)
        return a, b

    mcaA, mcmA = matcap_pair('', 700)

    def shade_node(prefix, mca, mcm, y, group_prefix=''):
        cs = g.custom(shade_code, PIXEL_PINS + [n for n, t, d in CORE_PARAMS], unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                      'LidaAngelToon_Shade' + ('_' + prefix.strip('_') if prefix else ''), -600, y)
        pix = {'N': (nrm, ''), 'L': (L, ''), 'V': (V, ''), 'KeyColor': (kc, ''), 'ShadowedNL': (snl, ''), 'BaseColor': (bc, ''),
               'ShadeTexture': (shmc, ''), 'Occlusion': (mR, ''), 'ReceiveShadowMask': (rsm, ''), 'MatCapAdd': (mca, ''),
               'MatCapMul': (mcm, ''), 'MatCapAddMask': (mam, '')}
        for k, (s, o) in pix.items():
            g.link(s, o, cs, k)
        yy = y - 1600
        for n, t, d in CORE_PARAMS:
            grp = (group_prefix + GROUP_OF[n]) if group_prefix else GROUP_OF[n]
            if t == 'float3':
                p = g.vector(prefix + n, d, -1300, yy, grp)
                g.link(g.rgb(p, '', -1000, yy), '', cs, n)
            else:
                p = g.scalar(prefix + n, d, -1300, yy, grp)
                g.link(p, '', cs, n)
            yy += 100
        return cs

    shA = shade_node('', mcaA, mcmA, 0)
    # layer 2 (two-layer materials, e.g. skin + cloth in one texture): same per-pixel inputs, own values / MatCap choice
    mcaB, mcmB = matcap_pair('L2_', 4200)
    shB = shade_node('L2_', mcaB, mcmB, 5000, group_prefix='07 Layer2 ')
    mGs = g.node(unreal.MaterialExpressionSaturate, -300, 2600)
    g.link(mG, '', mGs, '')
    two = g.lerp((shA, ''), (shB, ''), (mGs, ''), -100, 2500)
    col = g.switch('TwoLayer', False, (two, ''), (shA, ''), 150, 0, '07 Layer2')
    # ambient (optional, MPC AmbientMix = 0 by default) and exposure lock
    amc = g.rgb(g.mpc(mpc, 'AmbientColor', 150, 300), '', 400, 300)
    amx = g.mpc(mpc, 'AmbientMix', 150, 400)
    amb = g.mul((g.mul((bc, ''), (amc, ''), 600, 300), ''), (amx, ''), 800, 300)
    c2 = g.add((col, ''), (amb, ''), 1000, 0)
    exl = g.mpc(mpc, 'ExposureLock', 1000, 300)
    eai = g.node(unreal.MaterialExpressionEyeAdaptationInverse, 1250, 0)
    ins = mel.get_material_expression_input_names(eai)
    g.link(c2, '', eai, ins[0]); g.link(exl, '', eai, ins[1])
    g.out(eai, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    op = g.mul((base, 'A'), (bcol, 'A'), X + 650, 0)
    if translucent:
        g.out(op, '', unreal.MaterialProperty.MP_OPACITY)
    else:
        # used only when an instance overrides the blend mode to Masked: dithered alpha (TSR resolves it),
        # the Unreal counterpart of Blender's "Dithered" alpha (feathers)
        dt = g.custom(SNIP_DITHER, ['Alpha', 'Dither', 'Cutoff'], unreal.CustomMaterialOutputType.CMOT_FLOAT1, 'AT_DitherAlpha', X + 900, 0)
        g.link(op, '', dt, 'Alpha')
        g.link(g.scalar('AlphaDither', 1.0, X + 650, 100, '09 Alpha (Masked instances)'), '', dt, 'Dither')
        g.link(g.scalar('AlphaCutoff', 0.5, X + 650, 200, '09 Alpha (Masked instances)'), '', dt, 'Cutoff')
        g.out(dt, '', unreal.MaterialProperty.MP_OPACITY_MASK)
    return g


def make_toon(name, mpc, tex, translucent):
    m = new_material(name)
    if translucent:
        m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    toon_graph(m, mpc, tex, translucent)
    mel.recompile_material(m)
    eal.save_asset(MAT_DIR + '/' + name, only_if_is_dirty=False)
    log('%s: %d expressions' % (name, mel.get_num_material_expressions(m)))
    return m


def make_outline(mpc, tex):
    name = 'M_LidaAngelToon_Outline'
    m = new_material(name)
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED)
    m.set_editor_property('two_sided', True)
    m.set_editor_property('opacity_mask_clip_value', 0.5)
    g = Graph(m)
    ow_code = read_custom('LidaAngelToon_UECustom_OutlineWidth.txt')
    # width rule (spec v1 rule B by default): px = clamp(gain * width / pixelWorld, min, max)
    wmm = g.scalar('OutlineWidthMM', 0.55, -1800, -400, '08 Outline')
    wcm = g.mul((wmm, ''), 0.1, -1550, -400)
    rule = g.scalar('OutlinePixelRule', 1.0, -1800, -300, '08 Outline')
    gain = g.lerp(1.0, (g.scalar('OutlineGain', 1.5, -1800, -200, '08 Outline'), ''), (rule, ''), -1550, -250)
    mn = g.lerp(0.0, (g.scalar('OutlineMinPx', 1.0, -1800, -100, '08 Outline'), ''), (rule, ''), -1550, -150)
    mx = g.lerp(100000.0, (g.scalar('OutlineMaxPx', 2.0, -1800, 0, '08 Outline'), ''), (rule, ''), -1550, -50)
    vv = g.custom(SNIP_OUTLINE_VIEW, [], unreal.CustomMaterialOutputType.CMOT_FLOAT3, 'AT_OutlineView', -1550, 100)
    ow = g.custom(ow_code, ['WidthWorld', 'Depth', 'ProjM11', 'ViewHeightPx', 'Gain', 'MinPx', 'MaxPx'],
                  unreal.CustomMaterialOutputType.CMOT_FLOAT1, 'LidaAngelToon_OutlineWidth', -1100, -200)
    g.link(wcm, '', ow, 'WidthWorld')
    g.link(g.chan(vv, '', 'r', -1300, 100), '', ow, 'Depth')
    g.link(g.chan(vv, '', 'g', -1300, 200), '', ow, 'ProjM11')
    g.link(g.chan(vv, '', 'b', -1300, 300), '', ow, 'ViewHeightPx')
    g.link(gain, '', ow, 'Gain'); g.link(mn, '', ow, 'MinPx'); g.link(mx, '', ow, 'MaxPx')
    vn = g.node(unreal.MaterialExpressionVertexNormalWS, -1100, -400)
    wpo = g.mul((vn, ''), (ow, ''), -800, -300)
    g.out(wpo, '', unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    # pixel: colour = base x tint (two-layer: tint by mask G), visible = back face and mask B > 0.5
    base = g.tex('BaseMap', tex['white'], unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, -1800, 500, '01 Base')
    bcol = g.vector('BaseColor', (1, 1, 1, 1), -1800, 750, '01 Base')
    bc = g.mul((base, 'RGB'), (g.rgb(bcol, '', -1550, 750), ''), -1300, 600)
    mtex = g.tex('AngelToonMask', tex['mask'], unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR, -1800, 950, '06 Mask')
    vc = g.node(unreal.MaterialExpressionVertexColor, -1800, 1200)
    vca = g.node(unreal.MaterialExpressionAppendVector, -1550, 1200)
    g.link(vc, '', vca, 'A'); g.link(vc, 'A', vca, 'B')
    msk = g.switch('MaskFromVertexColor', False, (vca, ''), (mtex, 'RGBA'), -1300, 1000, '06 Mask')
    tA = g.rgb(g.vector('OutlineTint', (0.62, 0.62, 0.74, 1), -1300, 1300, '08 Outline'), '', -1050, 1300)
    tB = g.rgb(g.vector('L2_OutlineTint', (0.66, 0.48, 0.48, 1), -1300, 1400, '07 Layer2'), '', -1050, 1400)
    mG = g.node(unreal.MaterialExpressionSaturate, -1050, 1100)
    g.link(g.chan(msk, '', 'g', -1100, 1100), '', mG, '')
    tAB = g.lerp((tA, ''), (tB, ''), (mG, ''), -800, 1350)
    tint = g.switch('TwoLayer', False, (tAB, ''), (tA, ''), -600, 1300, '07 Layer2')
    colr = g.mul((bc, ''), (tint, ''), -400, 700)
    exl = g.mpc(mpc, 'ExposureLock', -400, 900)
    eai = g.node(unreal.MaterialExpressionEyeAdaptationInverse, -150, 700)
    ins = mel.get_material_expression_input_names(eai)
    g.link(colr, '', eai, ins[0]); g.link(exl, '', eai, ins[1])
    g.out(eai, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    sgn = g.node(unreal.MaterialExpressionTwoSidedSign, -800, 1700)
    vis = g.scalar('OutlineVisible', 1.0, -800, 1800, '08 Outline')
    om = g.custom(SNIP_OUTLINE_MASK, ['Sgn', 'Mb', 'Vis'], unreal.CustomMaterialOutputType.CMOT_FLOAT1, 'AT_OutlineMask', -500, 1700)
    g.link(sgn, '', om, 'Sgn'); g.link(g.chan(msk, '', 'b', -800, 1600), '', om, 'Mb'); g.link(vis, '', om, 'Vis')
    g.out(om, '', unreal.MaterialProperty.MP_OPACITY_MASK)
    mel.recompile_material(m)
    eal.save_asset(MAT_DIR + '/' + name, only_if_is_dirty=False)
    log('%s: %d expressions' % (name, mel.get_num_material_expressions(m)))
    return m


def make_multiply_layer(mpc, tex):
    name = 'M_LidaAngelToon_MultiplyLayer'
    m = new_material(name)
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MODULATE)
    g = Graph(m)
    base = g.tex('BaseMap', tex['white'], unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, -900, 0, '01 Base')
    lc = g.rgb(g.vector('LayerColor', (0.306718, 0.0, 0.061516, 1), -900, 250, '01 Base'), '', -650, 250)
    st = g.scalar('LayerStrength', 1.0, -900, 350, '01 Base')
    a = g.node(unreal.MaterialExpressionSaturate, -450, 300)
    g.link(g.mul((base, 'A'), (st, ''), -650, 350), '', a, '')
    c = g.lerp(1.0, (lc, ''), (a, ''), -250, 100)
    g.out(c, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(m)
    eal.save_asset(MAT_DIR + '/' + name, only_if_is_dirty=False)
    log('%s: %d expressions' % (name, mel.get_num_material_expressions(m)))
    return m


# ---------------------------------------------------------------------------- key light blueprint
def make_keylight_bp(mpc):
    """BP_LidaAngelToonKeyLight: every tick (and in the construction script) writes
    MPC KeyDir = -(forward vector of KeyLight). KeyLight = any actor (a DirectionalLight);
    when empty at BeginPlay, the first DirectionalLight of the level is taken.
    KeyColor stays the MPC value (set it on the MPC asset or from your own logic)."""
    name = 'BP_LidaAngelToonKeyLight'
    path = BP_DIR + '/' + name
    bel = unreal.BlueprintEditorLibrary
    pin = unreal.BlueprintGraphPinLibrary
    steps = []
    old = existing(path)

    def ok(label, v):
        good = bool(v)
        steps.append([label, good])
        if not good:
            log('BP step failed: ' + label)
        return v

    if old is not None:
        bp = old
        for gname in ('EventGraph', 'UserConstructionScript'):
            ge0 = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, gname)
            nodes = [n for n in ge0.list_all_nodes() if not isinstance(n, (unreal.K2Node_FunctionEntry, unreal.K2Node_Event))]
            if nodes:
                ge0.remove_nodes(nodes)
    else:
        f = unreal.BlueprintFactory()
        f.set_editor_property('parent_class', unreal.Actor)
        bp = at.create_asset(name, BP_DIR, unreal.Blueprint, f)
    if 'KeyLight' not in [str(n) for n in bel.list_member_variable_names(bp)]:
        ok('variable KeyLight', bel.add_member_variable(bp, 'KeyLight', bel.get_object_reference_type(unreal.Actor)))
    bel.set_blueprint_variable_instance_editable(bp, 'KeyLight', True)
    mpc_path = mpc.get_path_name()

    def add_event(ev_name, y):
        for pos in (lambda: unreal.Vector2f(0.0, y), lambda: unreal.IntPoint(0, int(y)), lambda: unreal.Vector2D(0.0, y)):
            try:
                return bel.add_event_override(bp, ev_name, pos())
            except Exception:  # noqa
                pass
        return None

    def link(a, b, label):
        return ok(label, a is not None and b is not None and pin.try_create_connection(a, b))

    def chain(ge, exec_pin, tag):
        get_kl = ge.add_get_member_variable_node('KeyLight')
        isv = ge.add_call_function_node('/Script/Engine.KismetSystemLibrary:IsValid')
        link(bel.find_output_pin(get_kl, 'KeyLight'), bel.find_input_pin(isv, 'Object'), tag + ' KeyLight->IsValid')
        br = ge.add_branch_node()
        link(exec_pin, bel.find_execute_pin(br), tag + ' exec->Branch')
        link(bel.find_output_pin(isv, 'ReturnValue'), bel.find_condition_pin(br), tag + ' IsValid->Condition')
        get_kl2 = ge.add_get_member_variable_node('KeyLight')
        fwd = ge.add_call_function_node('/Script/Engine.Actor:GetActorForwardVector')
        link(bel.find_output_pin(get_kl2, 'KeyLight'), bel.find_self_pin(fwd), tag + ' KeyLight->GetActorForwardVector')
        neg = ge.add_call_function_node('/Script/Engine.KismetMathLibrary:NegateVector')
        link(bel.find_output_pin(fwd, 'ReturnValue'), bel.find_input_pin_by_index(neg, 0), tag + ' Forward->Negate')
        conv = ge.add_call_function_node('/Script/Engine.KismetMathLibrary:Conv_VectorToLinearColor')
        link(bel.find_output_pin(neg, 'ReturnValue'), bel.find_input_pin_by_index(conv, 0), tag + ' Negate->ToLinearColor')
        s1 = ge.add_call_function_node('/Script/Engine.KismetMaterialLibrary:SetVectorParameterValue')
        ok(tag + ' Collection pin', pin.set_pin_value(bel.find_input_pin(s1, 'Collection'), mpc_path))
        ok(tag + ' ParameterName pin', pin.set_pin_value(bel.find_input_pin(s1, 'ParameterName'), 'KeyDir'))
        link(bel.find_output_pin(conv, 'ReturnValue'), bel.find_input_pin(s1, 'ParameterValue'), tag + ' Color->ParameterValue')
        link(bel.find_then_pin(br), bel.find_execute_pin(s1), tag + ' Branch.True->SetVectorParameterValue')

    ge = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, 'EventGraph')
    ev = ge.find_event_node('ReceiveTick') or add_event('ReceiveTick', 300.0)
    ok('event Tick', ev)
    chain(ge, bel.find_then_pin(ev), 'Tick')
    evb = ge.find_event_node('ReceiveBeginPlay') or add_event('ReceiveBeginPlay', 0.0)
    ok('event BeginPlay', evb)
    get_kl = ge.add_get_member_variable_node('KeyLight')
    isv = ge.add_call_function_node('/Script/Engine.KismetSystemLibrary:IsValid')
    link(bel.find_output_pin(get_kl, 'KeyLight'), bel.find_input_pin(isv, 'Object'), 'BeginPlay KeyLight->IsValid')
    br = ge.add_branch_node()
    link(bel.find_then_pin(evb), bel.find_execute_pin(br), 'BeginPlay exec->Branch')
    link(bel.find_output_pin(isv, 'ReturnValue'), bel.find_condition_pin(br), 'BeginPlay IsValid->Condition')
    gaoc = ge.add_call_function_node('/Script/Engine.GameplayStatics:GetActorOfClass')
    ok('ActorClass pin', pin.set_pin_value(bel.find_input_pin(gaoc, 'ActorClass'), '/Script/Engine.DirectionalLight'))
    setkl = ge.add_set_member_variable_node('KeyLight')
    link(bel.find_else_pin(br), bel.find_execute_pin(gaoc), 'BeginPlay Branch.False->GetActorOfClass')
    link(bel.find_then_pin(gaoc), bel.find_execute_pin(setkl), 'BeginPlay GetActorOfClass->Set KeyLight')
    link(bel.find_output_pin(gaoc, 'ReturnValue'), bel.find_input_pin(setkl, 'KeyLight'), 'BeginPlay GetActorOfClass->KeyLight')
    try:
        gc = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, 'UserConstructionScript')
        chain(gc, gc.find_graph_entry_pin(), 'Construction')
    except Exception as e:  # noqa
        log('construction script skipped: ' + repr(e)[:200])
    compiled = bel.compile_blueprint(bp)
    errs = [n.get_name() for n in ge.list_nodes_with_errors()]
    warns = [n.get_name() for n in ge.list_nodes_with_warnings()]
    eal.save_asset(path, only_if_is_dirty=False)
    failed = [s for s in steps if not s[1]]
    log('BP %s compiled=%s errors=%s warnings=%s failed_steps=%d nodes=%d' % (name, compiled, errs, warns, len(failed), len(ge.list_all_nodes())))
    return {'path': path, 'compiled': compiled, 'errors': errs, 'warnings': warns, 'steps': steps, 'nodes': len(ge.list_all_nodes())}


def build_all():
    res = {}
    tex = {'white': make_texture('T_LidaAngelToon_White', (255, 255, 255, 255), True),
           'black': make_texture('T_LidaAngelToon_Black', (0, 0, 0, 255), True),
           # sampled as an sRGB colour in MatCapMulMap: 188 = sRGB code of linear 0.5 (= no change)
           'grey': make_texture('T_LidaAngelToon_Grey50', (188, 188, 188, 255), True),
           # default AngelToonMask: R occlusion 1 (open), G two-layer 0, B outline 1, A 1
           'mask': make_texture('T_LidaAngelToon_DefaultMask', (255, 0, 255, 255), False)}
    mpc = make_mpc()
    res['M_LidaAngelToon'] = make_toon('M_LidaAngelToon', mpc, tex, False).get_path_name()
    res['M_LidaAngelToon_Translucent'] = make_toon('M_LidaAngelToon_Translucent', mpc, tex, True).get_path_name()
    res['M_LidaAngelToon_Outline'] = make_outline(mpc, tex).get_path_name()
    res['M_LidaAngelToon_MultiplyLayer'] = make_multiply_layer(mpc, tex).get_path_name()
    try:
        res['BP'] = make_keylight_bp(mpc)
    except Exception as e:  # noqa
        import traceback
        res['BP'] = {'error': repr(e)[:400], 'trace': traceback.format_exc()[-1500:]}
        log('BP failed: ' + repr(e)[:300])
    res['log'] = LOG
    return res


if __name__ == '__main__':
    out = build_all()
    p = os.environ.get('LIDAANGELTOON_BUILD_REPORT')
    if p:
        json.dump(out, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
