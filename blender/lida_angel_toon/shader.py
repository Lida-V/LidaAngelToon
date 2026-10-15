# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Lida
"""Model-independent soft toon nodes for Blender EEVEE.

The node math was extracted from the author's Blender look-development code.
No model names, geometry, source textures, or motion data are required.
"""
import bpy
import os
from mathutils import Vector
from .presets import PRESETS

GROUP = "LidaAngelToon"
MCUV = "LidaAngelToonMatCapUV"
VERSION = "0.1.0"
PROBE_CAL = 0.25464

def _sock(sockets, ident):
    for s in sockets:
        if s.identifier == ident:
            return s
    for s in sockets:
        if s.name == ident:
            return s
    raise KeyError(ident)

class NB:
    """node builder for one node tree"""

    def __init__(self, nt):
        self.nt = nt
        self.x = 0

    def node(self, typ, label=None, **kw):
        n = self.nt.nodes.new(typ)
        for k, v in kw.items():
            setattr(n, k, v)
        if label:
            n.label = label
            n.name = label
        n.location = (self.x, 0)
        self.x += 40
        return n

    def link(self, a, b):
        self.nt.links.new(a, b)

    def put(self, sock, v):
        if v is None:
            return
        if isinstance(v, bpy.types.NodeSocket):
            self.link(v, sock)
        else:
            sock.default_value = v

    def math(self, op, a, b=None, clamp=False, label=None):
        n = self.node('ShaderNodeMath', label, operation=op, use_clamp=clamp)
        self.put(n.inputs[0], a)
        if b is not None:
            self.put(n.inputs[1], b)
        return n.outputs[0]

    def vmath(self, op, a, b=None, scale=None, label=None):
        n = self.node('ShaderNodeVectorMath', label, operation=op)
        self.put(n.inputs[0], a)
        if b is not None:
            self.put(n.inputs[1], b)
        if scale is not None:
            self.put(n.inputs[3], scale)
        return n

    def mix(self, fac, a, b, blend='MIX', clamp=False, label=None):
        n = self.node('ShaderNodeMix', label, data_type='RGBA', blend_type=blend, clamp_result=clamp)
        self.put(_sock(n.inputs, 'Factor_Float'), fac)
        self.put(_sock(n.inputs, 'A_Color'), a)
        self.put(_sock(n.inputs, 'B_Color'), b)
        return _sock(n.outputs, 'Result_Color')

    def smooth(self, val, lo, hi, label=None):
        """smoothstep(lo, hi, val) -> 0..1"""
        n = self.node('ShaderNodeMapRange', label, data_type='FLOAT', interpolation_type='SMOOTHSTEP', clamp=True)
        self.put(_sock(n.inputs, 'Value'), val)
        self.put(_sock(n.inputs, 'From Min'), lo)
        self.put(_sock(n.inputs, 'From Max'), hi)
        _sock(n.inputs, 'To Min').default_value = 0.0
        _sock(n.inputs, 'To Max').default_value = 1.0
        return _sock(n.outputs, 'Result')
GROUP_INPUTS = [('Base Color', 'NodeSocketColor', (1, 1, 1, 1), '基本色（材質がいま計算している色。必要なら焼き込んだ基本色の画像）'), ('Shade Texture', 'NodeSocketColor', (1, 1, 1, 1), '影色の画像（髪だけ。MToon の shadeMultiplyTexture と同じ）'), ('Use Shade Texture', 'NodeSocketFloat', 0.0, '1＝影色を画像から、0＝基本色から'), ('Shade Tint 1', 'NodeSocketColor', (0.82, 0.8, 0.9, 1), '1 段目の影の色味（基本色に掛ける）'), ('Shade Shift 1', 'NodeSocketFloat', 0.0, '1 段目の影の境目の位置（N·L、−1〜1）。大きいほど影が広い'), ('Shade Soft 1', 'NodeSocketFloat', 0.25, '1 段目の境目のやわらかさ（坂の半分の幅）'), ('Shade Tint 2', 'NodeSocketColor', (0.88, 0.88, 0.94, 1), '2 段目の影の色味（1 段目にさらに掛ける）'), ('Shade Shift 2', 'NodeSocketFloat', -0.5, '2 段目の境目の位置'), ('Shade Soft 2', 'NodeSocketFloat', 0.3, '2 段目の境目のやわらかさ'), ('Receive Shadow', 'NodeSocketFloat', 1.0, '落ち影を受ける強さ（0＝受けない）'), ('Normal Override', 'NodeSocketVector', (0, 0, 0), '向きの差し替え（使うときだけ）'), ('Normal Override Mix', 'NodeSocketFloat', 0.0, '向きの差し替えの割合'), ('Lit Tint', 'NodeSocketColor', (1, 1, 1, 1), '明るい所の色味'), ('Rim Color', 'NodeSocketColor', (0.9, 0.92, 1.0, 1), '縁の光の色'), ('Rim Strength', 'NodeSocketFloat', 0.0, '縁の光の強さ（足す）'), ('Rim Width', 'NodeSocketFloat', 0.25, '縁の光の幅（1−N·V で、縁からどこまで）'), ('Rim Soft', 'NodeSocketFloat', 0.15, '縁の光のやわらかさ'), ('Rim Lit Bias', 'NodeSocketFloat', 0.5, '縁の光を明るい側だけに寄せる割合（0＝全周）'), ('Spec Color', 'NodeSocketColor', (1, 1, 1, 1), 'つやの色'), ('Spec Strength', 'NodeSocketFloat', 0.0, 'つやの強さ（足す）'), ('Spec Size', 'NodeSocketFloat', 0.97, 'つやの大きさ（N·H のしきい、1 に近いほど小さい）'), ('Spec Soft', 'NodeSocketFloat', 0.02, 'つやの縁のやわらかさ'), ('MatCap Add', 'NodeSocketColor', (0, 0, 0, 1), 'MatCap（足す用）の色'), ('MatCap Add Strength', 'NodeSocketFloat', 0.0, 'MatCap を足す強さ'), ('MatCap Mul', 'NodeSocketColor', (0.5, 0.5, 0.5, 1), 'MatCap（掛ける用、0.5＝そのまま）の色'), ('MatCap Mul Strength', 'NodeSocketFloat', 0.0, 'MatCap を掛ける強さ'), ('Unlit', 'NodeSocketFloat', 0.0, '光に関係なく基本色を見せる割合（目など）'), ('Highlight Knee', 'NodeSocketFloat', 0.85, '明るすぎる所を 1.0 へなだらかに寄せ始める明るさ（1＝しない）'), ('Occlusion', 'NodeSocketFloat', 1.0, '奥の暗さ（焼いた AO、1＝開いている、0＝奥まった所）。頂点の値 lida_angel_toon_ao'), ('Occlusion Shift', 'NodeSocketFloat', 0.0, '奥まった所で光（N·L）を下げる量＝影 1・影 2 の色で暗くなる'), ('Occlusion Darken', 'NodeSocketFloat', 0.0, '奥まった所に影 2 の色味をさらに掛ける割合'), ('Terminator Color', 'NodeSocketColor', (1.0, 0.75, 0.73, 1), '明るい所から影へ移る所の細い帯の色（掛ける）'), ('Terminator Strength', 'NodeSocketFloat', 0.0, 'その帯の強さ'), ('Terminator Width', 'NodeSocketFloat', 0.1, 'その帯の幅（N·L）'), ('MatCap Add Mask', 'NodeSocketFloat', 1.0, 'MatCap を足す場所の割合（髪の毛筋・天使の輪の範囲）'), ('Base Lift', 'NodeSocketFloat', 0.0, '基本色を Base Lift Color へ寄せる割合（肌を少し白く）'), ('Base Lift Color', 'NodeSocketColor', (1.0, 0.97, 0.96, 1), '寄せる先の色'), ('Base Saturation', 'NodeSocketFloat', 1.0, '基本色の彩度（1＝そのまま、小さいほど赤みが減る）')]

def build_group():
    if GROUP in bpy.data.node_groups:
        group = bpy.data.node_groups[GROUP]
        if group.get('lida_angel_toon_version') != VERSION:
            raise ValueError('A different LidaAngelToon node group already exists; rename it before applying')
        return group
    nt = bpy.data.node_groups.new(GROUP, 'ShaderNodeTree')
    nt.description = 'LidaAngelToon 0.1.0: soft EEVEE lighting with optional AO and cast shadows.'
    nt['lida_angel_toon_version'] = VERSION
    for name, typ, dv, desc in GROUP_INPUTS:
        s = nt.interface.new_socket(name, in_out='INPUT', socket_type=typ)
        s.description = desc
        try:
            s.default_value = dv
        except Exception:
            pass
        if typ == 'NodeSocketFloat':
            s.min_value, s.max_value = (-2.0, 4.0)
    nt.interface.new_socket('Shader', in_out='OUTPUT', socket_type='NodeSocketShader')
    nt.interface.new_socket('Color', in_out='OUTPUT', socket_type='NodeSocketColor')
    nt.interface.new_socket('Lit', in_out='OUTPUT', socket_type='NodeSocketFloat')
    b = NB(nt)
    gi = b.node('NodeGroupInput', 'In')
    go = b.node('NodeGroupOutput', 'Out')
    I = {s.name: s for s in gi.outputs}
    kd = b.node('ShaderNodeCombineXYZ', 'KeyDir')
    kc = b.node('ShaderNodeRGB', 'KeyColor')
    kc.outputs[0].default_value = (1, 1, 1, 1)
    ke = b.node('ShaderNodeValue', 'KeyEnergy')
    ke.outputs[0].default_value = 1.0
    geo = b.node('ShaderNodeNewGeometry', 'Geometry')
    nmix = b.node('ShaderNodeMix', 'NormalMix', data_type='VECTOR')
    b.put(_sock(nmix.inputs, 'Factor_Float'), I['Normal Override Mix'])
    b.put(_sock(nmix.inputs, 'A_Vector'), geo.outputs['Normal'])
    b.put(_sock(nmix.inputs, 'B_Vector'), I['Normal Override'])
    N = b.vmath('NORMALIZE', _sock(nmix.outputs, 'Result_Vector'), label='N').outputs[0]
    L = b.vmath('NORMALIZE', kd.outputs[0], label='L').outputs[0]
    V = b.vmath('NORMALIZE', geo.outputs['Incoming'], label='V').outputs[0]
    NL = b.vmath('DOT_PRODUCT', N, L, label='NdotL').outputs[1]
    dif = b.node('ShaderNodeBsdfDiffuse', 'Probe')
    dif.inputs['Color'].default_value = (1, 1, 1, 1)
    dif.inputs['Roughness'].default_value = 0.0
    b.link(N, dif.inputs['Normal'])
    s2r = b.node('ShaderNodeShaderToRGB', 'ProbeRGB')
    b.link(dif.outputs[0], s2r.inputs[0])
    bw = b.node('ShaderNodeRGBToBW', 'ProbeBW')
    b.link(s2r.outputs[0], bw.inputs[0])
    kscale = b.math('MULTIPLY', ke.outputs[0], PROBE_CAL, label='ProbeScale')
    kcl = b.node('ShaderNodeRGBToBW', 'KeyColorBW')
    b.link(kc.outputs[0], kcl.inputs[0])
    kscale2 = b.math('MULTIPLY', kscale, kcl.outputs[0])
    probe = b.math('DIVIDE', bw.outputs[0], b.math('MAXIMUM', kscale2, 0.0001), label='ProbeNL')
    nls = b.math('MINIMUM', NL, probe, label='NL_shadowed')
    rs = b.node('ShaderNodeMix', 'ReceiveShadowMix', data_type='FLOAT')
    b.put(_sock(rs.inputs, 'Factor_Float'), I['Receive Shadow'])
    b.put(_sock(rs.inputs, 'A_Float'), NL)
    b.put(_sock(rs.inputs, 'B_Float'), nls)
    Ls0 = _sock(rs.outputs, 'Result_Float')
    occ = b.smooth(b.math('SUBTRACT', 1.0, I['Occlusion']), 0.05, 0.9, label='Occ')
    Ls = b.math('SUBTRACT', Ls0, b.math('MULTIPLY', occ, I['Occlusion Shift']), label='Ls_occ')
    t1 = b.smooth(Ls, b.math('SUBTRACT', I['Shade Shift 1'], I['Shade Soft 1']), b.math('ADD', I['Shade Shift 1'], I['Shade Soft 1']), label='t1_lit')
    t2 = b.smooth(Ls, b.math('SUBTRACT', I['Shade Shift 2'], I['Shade Soft 2']), b.math('ADD', I['Shade Shift 2'], I['Shade Soft 2']), label='t2_shade1')
    base = b.mix(I['Base Lift'], I['Base Color'], I['Base Lift Color'], label='BaseLift')
    bbw = b.node('ShaderNodeRGBToBW', 'BaseGray')
    b.link(base, bbw.inputs[0])
    base = b.mix(I['Base Saturation'], bbw.outputs[0], base, label='BaseSaturation')
    shade_src = b.mix(I['Use Shade Texture'], base, I['Shade Texture'], label='ShadeSource')
    shade1 = b.mix(1.0, shade_src, I['Shade Tint 1'], blend='MULTIPLY', label='Shade1')
    shade2 = b.mix(1.0, shade1, I['Shade Tint 2'], blend='MULTIPLY', label='Shade2')
    lit = b.mix(1.0, base, I['Lit Tint'], blend='MULTIPLY', label='LitA')
    lit = b.mix(1.0, lit, kc.outputs[0], blend='MULTIPLY', label='LitB')
    c = b.mix(t2, shade2, shade1, label='Shade12')
    c = b.mix(t1, c, lit, label='LitShade')
    s1 = I['Shade Shift 1']
    band = b.math('MULTIPLY', b.smooth(Ls, b.math('SUBTRACT', s1, I['Terminator Width']), s1), b.math('SUBTRACT', 1.0, b.smooth(Ls, s1, b.math('ADD', s1, I['Terminator Width']))), label='TermBand')
    c = b.mix(b.math('MULTIPLY', band, I['Terminator Strength']), c, b.mix(1.0, c, I['Terminator Color'], blend='MULTIPLY'), label='Terminator')
    c = b.mix(b.math('MULTIPLY', occ, I['Occlusion Darken']), c, b.mix(1.0, c, I['Shade Tint 2'], blend='MULTIPLY'), label='OccDarken')
    open_ = b.math('SUBTRACT', 1.0, occ, label='Open')
    nv = b.math('MAXIMUM', b.vmath('DOT_PRODUCT', N, V).outputs[1], 0.0)
    fres = b.math('SUBTRACT', 1.0, nv, label='Fresnel')
    rlo = b.math('SUBTRACT', b.math('SUBTRACT', 1.0, I['Rim Width']), I['Rim Soft'])
    rhi = b.math('ADD', b.math('SUBTRACT', 1.0, I['Rim Width']), I['Rim Soft'])
    rim = b.smooth(fres, rlo, rhi, label='Rim')
    rbias = b.node('ShaderNodeMix', 'RimBias', data_type='FLOAT')
    b.put(_sock(rbias.inputs, 'Factor_Float'), I['Rim Lit Bias'])
    _sock(rbias.inputs, 'A_Float').default_value = 1.0
    b.put(_sock(rbias.inputs, 'B_Float'), t1)
    rimk = b.math('MULTIPLY', b.math('MULTIPLY', b.math('MULTIPLY', rim, _sock(rbias.outputs, 'Result_Float')), I['Rim Strength']), open_, label='RimAmount')
    c = b.mix(rimk, c, I['Rim Color'], blend='ADD', label='AddRim')
    H = b.vmath('NORMALIZE', b.vmath('ADD', L, V).outputs[0]).outputs[0]
    nh = b.math('MAXIMUM', b.vmath('DOT_PRODUCT', N, H).outputs[1], 0.0, label='NdotH')
    sp = b.smooth(nh, b.math('SUBTRACT', I['Spec Size'], I['Spec Soft']), b.math('ADD', I['Spec Size'], I['Spec Soft']), label='Spec')
    spk = b.math('MULTIPLY', b.math('MULTIPLY', b.math('MULTIPLY', sp, t1), I['Spec Strength']), open_, label='SpecAmount')
    c = b.mix(spk, c, I['Spec Color'], blend='ADD', label='AddSpec')
    mcm = b.mix(1.0, c, b.vmath('SCALE', I['MatCap Mul'], scale=2.0).outputs[0], blend='MULTIPLY')
    c = b.mix(I['MatCap Mul Strength'], c, mcm, label='MatCapMul')
    c = b.mix(b.math('MULTIPLY', b.math('MULTIPLY', I['MatCap Add Strength'], I['MatCap Add Mask']), open_), c, I['MatCap Add'], blend='ADD', label='MatCapAdd')
    c = b.mix(I['Unlit'], c, base, label='Unlit')
    sep = b.node('ShaderNodeSeparateColor', 'KneeSep')
    b.link(c, sep.inputs[0])
    m = b.math('MAXIMUM', b.math('MAXIMUM', sep.outputs[0], sep.outputs[1]), sep.outputs[2], label='MaxCh')
    k = I['Highlight Knee']
    over = b.math('MAXIMUM', b.math('SUBTRACT', m, k), 0.0)
    rng = b.math('MAXIMUM', b.math('SUBTRACT', 1.0, k), 0.001)
    y = b.math('ADD', b.math('MINIMUM', m, k), b.math('MULTIPLY', rng, b.math('SUBTRACT', 1.0, b.math('EXPONENT', b.math('MULTIPLY', b.math('DIVIDE', over, rng), -1.0)))))
    sc = b.math('DIVIDE', y, b.math('MAXIMUM', m, 0.0001), label='KneeScale')
    cv = b.vmath('SCALE', c, scale=sc).outputs[0]
    em = b.node('ShaderNodeEmission', 'ToonEmission')
    em.inputs['Strength'].default_value = 1.0
    b.link(cv, em.inputs['Color'])
    b.link(em.outputs[0], go.inputs['Shader'])
    b.link(cv, go.inputs['Color'])
    b.link(t1, go.inputs['Lit'])
    return nt

def build_matcap_uv():
    if MCUV in bpy.data.node_groups:
        return bpy.data.node_groups[MCUV]
    nt = bpy.data.node_groups.new(MCUV, 'ShaderNodeTree')
    nt.interface.new_socket('Vector', in_out='OUTPUT', socket_type='NodeSocketVector')
    b = NB(nt)
    go = b.node('NodeGroupOutput', 'Out')
    geo = b.node('ShaderNodeNewGeometry', 'Geometry')
    vt = b.node('ShaderNodeVectorTransform', 'ToCamera', vector_type='NORMAL', convert_from='WORLD', convert_to='CAMERA')
    b.link(geo.outputs['Normal'], vt.inputs[0])
    n = b.vmath('NORMALIZE', vt.outputs[0]).outputs[0]
    uv = b.vmath('MULTIPLY_ADD', n, (0.5, 0.5, 0.0))
    uv.inputs[2].default_value = (0.5, 0.5, 0.0)
    b.link(uv.outputs[0], go.inputs[0])
    return nt


MATCAPS = {
    'cloth': ('Sheen.png', 'ADD', 0.04),
    'hair': ('HairRing.png', 'ADD', 0.40),
    'metal': ('Metal.png', 'MULTIPLY', 0.8),
    'gem': ('Gem.png', 'ADD', 0.5),
    'eye': ('Eye.png', 'ADD', 0.65),
    'nail': ('Sheen.png', 'ADD', 0.12),
    'feather': ('Sheen.png', 'ADD', 0.03),
}


def ensure_sun(scene, sun=None):
    """Use an explicitly chosen or existing sun; create one only when absent."""
    if sun is not None:
        if sun.type != 'LIGHT' or sun.data.type != 'SUN':
            raise ValueError('Main light must be a Sun')
        return sun
    sun = next((o for o in scene.objects if o.type == 'LIGHT' and o.data.type == 'SUN'), None)
    if sun:
        return sun
    data = bpy.data.lights.new('LidaAngelToon Sun', 'SUN')
    data.energy = 1.0
    data.angle = 0.10472
    sun = bpy.data.objects.new('LidaAngelToon Sun', data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = Vector((-0.45, -0.70, 0.70)).to_track_quat('Z', 'Y').to_euler()
    return sun


def bind_sun(group, sun):
    """All materials share one scene sun. Replace only these owned drivers."""
    paths = [('nodes["KeyDir"].inputs[%d].default_value' % i, None,
              sun, 'OBJECT', 'matrix_world[2][%d]' % i) for i in range(3)]
    paths += [('nodes["KeyColor"].outputs[0].default_value', i,
               sun.data, 'LIGHT', 'color[%d]' % i) for i in range(3)]
    paths += [('nodes["KeyEnergy"].outputs[0].default_value', None,
               sun.data, 'LIGHT', 'energy')]
    for path, index, target, id_type, data_path in paths:
        if index is None:
            group.driver_remove(path)
            fc = group.driver_add(path)
        else:
            group.driver_remove(path, index)
            fc = group.driver_add(path, index)
        driver = fc.driver
        driver.type = 'AVERAGE'
        for variable in list(driver.variables):
            driver.variables.remove(variable)
        variable = driver.variables.new()
        variable.name = 'light_value'
        variable.type = 'SINGLE_PROP'
        variable.targets[0].id_type = id_type
        variable.targets[0].id = target
        variable.targets[0].data_path = data_path
        while fc.keyframe_points:
            fc.keyframe_points.remove(fc.keyframe_points[0])
        fc.update()


def _owned(node):
    node['lida_angel_toon_owned'] = True
    return node


def _texture(nodes, filename, colorspace='sRGB'):
    path = os.path.join(os.path.dirname(__file__), 'assets', filename)
    image = bpy.data.images.load(path, check_existing=True)
    image.colorspace_settings.name = colorspace
    # A saved user's blend remains usable after updating/removing the add-on.
    if not image.packed_file:
        image.pack()
    node = _owned(nodes.new('ShaderNodeTexImage'))
    node.name = 'LidaAngelToon ' + os.path.splitext(filename)[0]
    node.image = image
    return node


def apply_material(material, preset, sun, *, receive_shadows=False,
                   ao_attribute='', hair_streak=False):
    """Apply to a Principled material without editing geometry or source nodes.

    ShaderEditor inputs remain editable after applying a preset. AO is optional:
    a float attribute with 1=open and 0=occluded. No baking occurs here.
    """
    if preset not in PRESETS:
        raise ValueError('Unknown material preset: ' + preset)
    material.use_nodes = True
    nt = material.node_tree
    original = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if original is None:
        raise ValueError(material.name + ': a Principled BSDF is required')
    output = next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'
                   and n.is_active_output and not n.get('lida_angel_toon_owned')), None)
    if 'lida_angel_toon_previous_output' not in material:
        if output is None:
            raise ValueError(material.name + ': original Material Output not found')
        material['lida_angel_toon_previous_output'] = output.name
    if 'lida_angel_toon_previous_render_method' not in material:
        material['lida_angel_toon_previous_render_method'] = material.surface_render_method
    for node in list(nt.nodes):
        if node.get('lida_angel_toon_owned'):
            nt.nodes.remove(node)
    group = build_group()
    group.description = 'LidaAngelToon: soft two-step EEVEE lighting. Optional single-sun cast-shadow probe.'
    bind_sun(group, sun)
    toon = _owned(nt.nodes.new('ShaderNodeGroup'))
    toon.node_tree = group
    toon.name = 'LidaAngelToon'
    toon.label = 'LidaAngelToon / ' + preset
    toon.location = (original.location.x + 320, original.location.y)
    for name, value in PRESETS[preset].items():
        socket = toon.inputs.get(name)
        if socket is None:
            continue
        if socket.type == 'RGBA' and len(value) == 3:
            value = (*value, 1.0)
        socket.default_value = value
    toon.inputs['Receive Shadow'].default_value = 1.0 if receive_shadows else 0.0
    for src_name, dst_name in [('Base Color', 'Base Color'), ('Normal', 'Normal Override')]:
        socket = original.inputs[src_name]
        if socket.is_linked:
            nt.links.new(socket.links[0].from_socket, toon.inputs[dst_name])
            if src_name == 'Normal':
                toon.inputs['Normal Override Mix'].default_value = 1.0
        elif src_name == 'Base Color':
            toon.inputs[dst_name].default_value = socket.default_value
    if ao_attribute.strip():
        attr = _owned(nt.nodes.new('ShaderNodeAttribute'))
        attr.attribute_name = ao_attribute.strip()
        nt.links.new(attr.outputs['Fac'], toon.inputs['Occlusion'])
    if preset in MATCAPS:
        filename, mode, strength = MATCAPS[preset]
        tex = _texture(nt.nodes, filename)
        uv = _owned(nt.nodes.new('ShaderNodeGroup'))
        uv.node_tree = build_matcap_uv()
        nt.links.new(uv.outputs['Vector'], tex.inputs['Vector'])
        slot = 'MatCap Mul' if mode == 'MULTIPLY' else 'MatCap Add'
        nt.links.new(tex.outputs['Color'], toon.inputs[slot])
        toon.inputs[slot + ' Strength'].default_value = strength
    if preset == 'hair' and hair_streak:
        tex = _texture(nt.nodes, 'HairStreak.png', 'Non-Color')
        nt.links.new(tex.outputs['Color'], toon.inputs['MatCap Add Mask'])
    out = _owned(nt.nodes.new('ShaderNodeOutputMaterial'))
    out.name = 'LidaAngelToon Output'
    out.location = (toon.location.x + 420, toon.location.y)
    alpha = original.inputs['Alpha']
    if alpha.is_linked or alpha.default_value < 1.0:
        transparent = _owned(nt.nodes.new('ShaderNodeBsdfTransparent'))
        mix = _owned(nt.nodes.new('ShaderNodeMixShader'))
        if alpha.is_linked:
            nt.links.new(alpha.links[0].from_socket, mix.inputs[0])
        else:
            mix.inputs[0].default_value = alpha.default_value
        nt.links.new(transparent.outputs[0], mix.inputs[1])
        nt.links.new(toon.outputs['Shader'], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs['Surface'])
        material.surface_render_method = 'DITHERED'
    else:
        nt.links.new(toon.outputs['Shader'], out.inputs['Surface'])
    out.is_active_output = True
    material['lida_angel_toon_preset'] = preset
    material['lida_angel_toon_version'] = VERSION
    return toon


def restore_material(material):
    """Restore the original output; keep generated data and user's fine tuning."""
    name = material.get('lida_angel_toon_previous_output')
    if not name or not material.node_tree:
        return False
    out = material.node_tree.nodes.get(name)
    if out is None or out.type != 'OUTPUT_MATERIAL':
        return False
    out.is_active_output = True
    old_method = material.get('lida_angel_toon_previous_render_method')
    if old_method:
        material.surface_render_method = old_method
    return True


def add_outline(obj, width_m):
    """Optional inverted hull. The original mesh coordinates are unchanged."""
    if obj.type != 'MESH':
        raise ValueError('Outline requires a mesh')
    name = 'LidaAngelToon Outline'
    modifier = obj.modifiers.get(name)
    if modifier is not None:
        modifier.thickness = width_m
        return modifier
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        em = nt.nodes.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = (0.12, 0.10, 0.16, 1.0)
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(em.outputs[0], out.inputs['Surface'])
        mat.use_backface_culling = True
    count = len(obj.data.materials)
    obj.data.materials.append(mat)
    modifier = obj.modifiers.new(name, 'SOLIDIFY')
    modifier.thickness = width_m
    modifier.offset = 1.0
    modifier.use_flip_normals = True
    modifier.use_rim = False
    modifier.use_even_offset = False
    modifier.use_quality_normals = True
    modifier.material_offset = count
    return modifier
