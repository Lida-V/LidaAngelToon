# ============================================================================
# core338.py  -  LidaAngelToon: numpy reference of LidaAngelToonCore.hlsl (same math, same [Sxx] tags)
#
# SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.0
#
# Copyright (c) 2026 Lida
# ============================================================================
"""core338.py  -  LidaAngelToon spec v1 (toonspec338): the same math as hlsl/LidaAngelToonCore.hlsl in numpy.
(Claude Opus 5.5, 2026-10-15)

Each step carries the same tag [S01]..[S24] as the HLSL, so the two can be read side by side.
All colours are linear. Arrays: vectors are (..., 3), scalars are (...).
The material is a dict with the HLSL field names (see FIELDS); values may be scalars or arrays
that broadcast against the pixel arrays.

Used by scripts/v02_compare338.py to check the formula against Blender renders (EEVEE, 1 sample, AOVs).
"""
import numpy as np

# HLSL field name <- Blender node-group input name (LidaSoftToon)
FIELDS = [
    ('ShadeTint1', 'Shade Tint 1', 3), ('ShadeShift1', 'Shade Shift 1', 1), ('ShadeSoft1', 'Shade Soft 1', 1),
    ('ShadeTint2', 'Shade Tint 2', 3), ('ShadeShift2', 'Shade Shift 2', 1), ('ShadeSoft2', 'Shade Soft 2', 1),
    ('UseShadeTexture', 'Use Shade Texture', 1), ('ReceiveShadow', 'Receive Shadow', 1),
    ('NormalOverride', 'Normal Override', 3), ('NormalOverrideMix', 'Normal Override Mix', 1),
    ('LitTint', 'Lit Tint', 3),
    ('RimColor', 'Rim Color', 3), ('RimStrength', 'Rim Strength', 1), ('RimWidth', 'Rim Width', 1),
    ('RimSoft', 'Rim Soft', 1), ('RimLitBias', 'Rim Lit Bias', 1),
    ('SpecColor', 'Spec Color', 3), ('SpecStrength', 'Spec Strength', 1), ('SpecSize', 'Spec Size', 1), ('SpecSoft', 'Spec Soft', 1),
    ('MatCapAddStrength', 'MatCap Add Strength', 1), ('MatCapMulStrength', 'MatCap Mul Strength', 1),
    ('Unlit', 'Unlit', 1), ('HighlightKnee', 'Highlight Knee', 1),
    ('OcclusionShift', 'Occlusion Shift', 1), ('OcclusionDarken', 'Occlusion Darken', 1),
    ('TerminatorColor', 'Terminator Color', 3), ('TerminatorStrength', 'Terminator Strength', 1),
    ('TerminatorWidth', 'Terminator Width', 1),
    ('BaseLift', 'Base Lift', 1), ('BaseLiftColor', 'Base Lift Color', 3), ('BaseSaturation', 'Base Saturation', 1),
]
# per-pixel inputs that come from Blender group inputs when they are not linked
INPUT_DEFAULTS = {'Shade Texture': 'ShadeTexture', 'MatCap Add': 'MatCapAdd', 'MatCap Mul': 'MatCapMul',
                  'MatCap Add Mask': 'MatCapAddMask', 'Occlusion': 'Occlusion', 'Base Color': 'BaseColor'}
LUMA = np.array([0.2126729, 0.7151522, 0.0721750])


def material_from_blender_inputs(inp):
    """dict of Blender input name -> value  ->  dict of HLSL field -> numpy value"""
    m = {}
    for f, b, n in FIELDS:
        v = inp[b]
        m[f] = np.asarray(v[:3] if n == 3 else v, dtype=np.float64)
    return m


def clamp01(x):
    return np.clip(x, 0.0, 1.0)


def smoothstep(lo, hi, x):
    lo = np.asarray(lo, np.float64); hi = np.asarray(hi, np.float64)
    d = hi - lo
    with np.errstate(divide='ignore', invalid='ignore'):
        t = np.where(d != 0.0, (x - lo) / np.where(d != 0.0, d, 1.0), 0.0)
    t = np.clip(t, 0.0, 1.0)
    return (3.0 - 2.0 * t) * (t * t)


def _f(x):
    """scalar factor -> broadcastable over (...,3)"""
    return np.asarray(x, np.float64)[..., None]


def mix3(a, b, f):
    t = _f(np.clip(f, 0.0, 1.0))
    return a * (1.0 - t) + b * t


def mix1(a, b, f):
    t = np.clip(f, 0.0, 1.0)
    return a * (1.0 - t) + b * t


def dot(a, b):
    return np.sum(a * b, axis=-1)


def safe_normalize(v):
    l2 = dot(v, v)
    with np.errstate(divide='ignore', invalid='ignore'):
        r = np.where(l2 > 0.0, 1.0 / np.sqrt(np.where(l2 > 0.0, l2, 1.0)), 0.0)
    return v * r[..., None]


def luminance(c):
    return dot(c, LUMA)


SHADOW_GAIN_BLENDER = 1.0 / (np.pi * 0.25464)   # = 1.2500: the Blender probe gives 1/pi per unit N.L, divided by 0.25464


def shadowed_nl(NL, atten, gain=SHADOW_GAIN_BLENDER):
    return clamp01(NL) * atten * gain


def matcap_uv(normal_vs):
    n = safe_normalize(normal_vs)
    return n[..., :2] * 0.5 + 0.5


def highlight_knee(c, k):
    m = np.max(c, axis=-1)                                   # [S22]
    over = np.maximum(m - k, 0.0)
    rng = np.maximum(1.0 - k, 0.001)
    y = np.minimum(m, k) + rng * (1.0 - np.exp(-(over / rng)))  # [S23]
    return c * (y / np.maximum(m, 0.0001))[..., None]       # [S24]


def shade(i, m, want=None):
    """i: dict of per-pixel inputs (HLSL names), m: material dict (HLSL names). Returns linear colour (...,3).
    want: optional dict that receives intermediate values (t1, t2, Ls, occ) for checks."""
    # [S01]
    N = safe_normalize(mix3(i['N'], m['NormalOverride'], m['NormalOverrideMix']))
    L = safe_normalize(i['L'])
    V = safe_normalize(i['V'])
    NL = dot(N, L)
    # [S02]
    NLs = np.minimum(NL, i['ShadowedNL'])
    Ls0 = mix1(NL, NLs, m['ReceiveShadow'] * i['ReceiveShadowMask'])
    # [S03]
    occ = smoothstep(0.05, 0.9, 1.0 - i['Occlusion'])
    Ls = Ls0 - occ * m['OcclusionShift']
    # [S04]
    t1 = smoothstep(m['ShadeShift1'] - m['ShadeSoft1'], m['ShadeShift1'] + m['ShadeSoft1'], Ls)
    t2 = smoothstep(m['ShadeShift2'] - m['ShadeSoft2'], m['ShadeShift2'] + m['ShadeSoft2'], Ls)
    # [S05]
    base = mix3(i['BaseColor'], m['BaseLiftColor'], m['BaseLift'])
    gray = luminance(base)
    base = mix3(np.repeat(gray[..., None], 3, axis=-1), base, m['BaseSaturation'])
    # [S06]
    shade_src = mix3(base, i['ShadeTexture'], m['UseShadeTexture'])
    shade1 = shade_src * m['ShadeTint1']
    shade2 = shade1 * m['ShadeTint2']
    lit = (base * m['LitTint']) * i['KeyColor']
    # [S07]
    c = mix3(shade2, shade1, t2)
    c = mix3(c, lit, t1)
    # [S08]
    s1 = m['ShadeShift1']
    band = smoothstep(s1 - m['TerminatorWidth'], s1, Ls) * (1.0 - smoothstep(s1, s1 + m['TerminatorWidth'], Ls))
    c = mix3(c, c * m['TerminatorColor'], band * m['TerminatorStrength'])
    # [S09]
    c = mix3(c, c * m['ShadeTint2'], occ * m['OcclusionDarken'])
    open_k = 1.0 - occ                                       # [S10]
    # [S11]
    nv = np.maximum(dot(N, V), 0.0)
    fres = 1.0 - nv
    rim = smoothstep((1.0 - m['RimWidth']) - m['RimSoft'], (1.0 - m['RimWidth']) + m['RimSoft'], fres)
    rbias = mix1(1.0, t1, m['RimLitBias'])
    rim_k = ((rim * rbias) * m['RimStrength']) * open_k
    c = c + m['RimColor'] * _f(clamp01(rim_k))              # [S12]
    # [S13]
    H = safe_normalize(L + V)
    nh = np.maximum(dot(N, H), 0.0)
    sp = smoothstep(m['SpecSize'] - m['SpecSoft'], m['SpecSize'] + m['SpecSoft'], nh)
    sp_k = ((sp * t1) * m['SpecStrength']) * open_k
    c = c + m['SpecColor'] * _f(clamp01(sp_k))              # [S14]
    # [S15]
    mcm = c * (i['MatCapMul'] * 2.0)
    c = mix3(c, mcm, m['MatCapMulStrength'])
    mca_k = (m['MatCapAddStrength'] * i['MatCapAddMask']) * open_k  # [S16]
    c = c + i['MatCapAdd'] * _f(clamp01(mca_k))
    # [S17]
    c = mix3(c, base, m['Unlit'])
    if want is not None:
        want.update(t1=t1, t2=t2, Ls=Ls, occ=occ, NL=NL)
    # [S18]
    return highlight_knee(c, m['HighlightKnee'])


def shade_two_layer(iA, mA, iB, mB, maskB):              # [S19]
    return mix3(shade(iA, mA), shade(iB, mB), maskB)


def outline_color(base, tint):                           # [S20]
    return base * tint


def outline_visible(mask):
    return (np.asarray(mask) > 0.5).astype(np.float64)


def pixel_world_size(clip_w, proj_m11, screen_h):
    return 2.0 * clip_w / (proj_m11 * screen_h)


def outline_pixels(width_world, pixel_world, gain, min_px, max_px):
    return np.clip(gain * width_world / np.maximum(pixel_world, 1e-8), min_px, max_px)


# sRGB helpers (for comparisons)
def srgb_to_linear(x):
    x = np.asarray(x, np.float64)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(x):
    x = np.clip(np.asarray(x, np.float64), 0.0, None)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)
