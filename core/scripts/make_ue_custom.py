# ============================================================================
# make_ue_custom.py  -  LidaAngelToon: generate the Unreal Engine Custom-node bodies from the core
#
# SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.1
#
# Copyright (c) 2026 Lida
# ============================================================================
"""Generate the Unreal Engine Custom-node bodies from core/LidaAngelToonCore.hlsl (the single source).

python -I core/scripts/make_ue_custom.py <repository root> [<out hlsl folder> [<out syntax-check file>]]

Defaults (inside the repository):
  <repository root>/unreal/LidaAngelToon/Source/hlsl/LidaAngelToon_UECustom_Shade.txt
      body of the Custom node that returns the shaded colour (float3)
  <repository root>/unreal/LidaAngelToon/Source/hlsl/LidaAngelToon_UECustom_OutlineWidth.txt
      body that returns the outline push length in world units (float1)
  <repository root>/core/tests/ue_custom_check.hlsl
      the bodies wrapped like Unreal does (a function per Custom node), to be compiled with fxc / dxc as a
      syntax check.

How the trick works: an Unreal Custom node pastes its text INSIDE a generated function, so the core's
types are declared locally and the core's functions become member functions of a local struct
(the common "struct of functions" way to use helper functions in a Custom node).

The generated text is the same as the one shipped in unreal/LidaAngelToon/Source/hlsl (run it after any
change of the core); tests/test_repository_consistency.py checks this.
"""
import os, re, sys

root = os.path.abspath(sys.argv[1])
out_dir = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.join(root, 'unreal', 'LidaAngelToon', 'Source', 'hlsl')
chk_file = os.path.abspath(sys.argv[3]) if len(sys.argv) > 3 else os.path.join(root, 'core', 'tests', 'ue_custom_check.hlsl')
core = open(os.path.join(root, 'core', 'LidaAngelToonCore.hlsl'), encoding='ascii').read()


def block(name):
    m = re.search(r'//@@%s_BEGIN\n(.*?)//@@%s_END' % (name, name), core, re.S)
    assert m, name
    return m.group(1)


types = block('ANGELTOON_TYPES')
funcs = block('ANGELTOON_FUNCS').replace('ANGELTOON_FUNC ', '')

MAT = re.findall(r'^\s*(float3|float)\s+(\w+);', types.split('struct AngelToonInput')[0], re.M)
INP = re.findall(r'^\s*(float3|float)\s+(\w+);', types.split('struct AngelToonInput')[1], re.M)
assert len(MAT) == 32 and len(INP) == 12, (len(MAT), len(INP))


def indent(s, n=4):
    return '\n'.join((' ' * n + l) if l.strip() else '' for l in s.splitlines())


head = ('// LidaAngelToon - Unreal Engine Custom node body. GENERATED from LidaAngelToonCore.hlsl\n'
        '// by core/scripts/make_ue_custom.py. Do not edit by hand: edit the core and regenerate.\n'
        '// SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.1\n'
        '// Copyright (c) 2026 Lida\n')

pins_inp = ', '.join('%s (%s)' % (n, 'float3' if t == 'float3' else 'float1') for t, n in INP)
pins_mat = ', '.join('%s (%s)' % (n, 'float3' if t == 'float3' else 'float1') for t, n in MAT)
shade = head + (
    '// Output type: CMOT Float 3 (linear emissive colour; plug into Emissive Color of an Unlit material).\n'
    '// Inputs (add these pins with exactly these names):\n'
    '//   per pixel : %s\n'
    '//   material  : %s\n'
    '// Directions N, L, V in the same world space. MatCapAdd / MatCapMul are sampled outside with\n'
    '// the UV from AngelToonMatCapUV_UE (view-space normal, V = 0 at the top row).\n') % (pins_inp, pins_mat)
shade += types.strip() + '\n'
shade += 'struct AngelToonFns\n{\n' + indent(funcs.strip()) + '\n};\n'
shade += 'AngelToonFns F;\nAngelToonMaterial m;\n'
for t, n in MAT:
    shade += 'm.%s = %s;\n' % (n, n)
shade += 'AngelToonInput i;\n'
for t, n in INP:
    shade += 'i.%s = %s;\n' % (n, n)
shade += 'return F.AngelToonShade(i, m);\n'

ow = head + (
    '// Output type: CMOT Float 1 = how far to push the outline-hull vertex along its normal, in world units\n'
    '// (Unreal: centimetres). Use it as World Position Offset = VertexNormalWS * result on the outline mesh.\n'
    '// Inputs: WidthWorld (natural width, cm = table mm * 0.1), Depth (view-space depth of the vertex, cm;\n'
    '//   1 for orthographic), ProjM11 (perspective: 1/tan(vertical FOV/2); orthographic: 2/view height in cm),\n'
    '//   ViewHeightPx (render target height in pixels), Gain, MinPx, MaxPx (table outline gain / min_px / max_px).\n')
ow += 'struct AngelToonFns\n{\n' + indent(block('ANGELTOON_FUNCS').replace('ANGELTOON_FUNC ', '').split('// Main shading')[0].strip()) + '\n'
ow += indent(re.search(r'(float AngelToonPixelWorldSize.*?\n\})', funcs, re.S).group(1)) + '\n'
ow += indent(re.search(r'(float AngelToonOutlinePixels.*?\n\})', funcs, re.S).group(1)) + '\n};\n'
ow += ('AngelToonFns F;\n'
       'float pw = F.AngelToonPixelWorldSize(Depth, ProjM11, ViewHeightPx);\n'
       'float px = F.AngelToonOutlinePixels(WidthWorld, pw, Gain, MinPx, MaxPx);\n'
       'return px * pw;\n')

os.makedirs(out_dir, exist_ok=True)
open(os.path.join(out_dir, 'LidaAngelToon_UECustom_Shade.txt'), 'w', encoding='ascii', newline='\n').write(shade)
open(os.path.join(out_dir, 'LidaAngelToon_UECustom_OutlineWidth.txt'), 'w', encoding='ascii', newline='\n').write(ow)

# wrapper like Unreal's generated code (one function per Custom node)
args = ', '.join('%s %s' % (t, n) for t, n in INP + MAT)
chk = '// GENERATED syntax check: the two Unreal Custom-node bodies wrapped in functions.\n'
chk += 'float3 CustomExpression0(%s)\n{\n%s\n}\n' % (args, indent(shade))
chk += ('float CustomExpression1(float WidthWorld, float Depth, float ProjM11, float ViewHeightPx, float Gain, float MinPx, float MaxPx)\n'
        '{\n%s\n}\n') % indent(ow)
call = ', '.join(('v.xyz' if t == 'float3' else 'v.w') for t, n in INP + MAT)
chk += ('float4 PSMain(float4 v : TEXCOORD0) : SV_Target\n{\n'
        '    float3 c = CustomExpression0(%s);\n'
        '    return float4(c, CustomExpression1(v.x, v.y, v.z, 1080.0, 1.5, 1.0, 2.0));\n}\n') % call
os.makedirs(os.path.dirname(chk_file), exist_ok=True)
open(chk_file, 'w', encoding='ascii', newline='\n').write(chk)
print('UE custom bodies written', len(MAT), len(INP))
