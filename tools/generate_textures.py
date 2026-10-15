# SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.0
# Copyright (c) 2026 Lida
"""Generate six original procedural textures. No photographs or model inputs."""
import argparse
from pathlib import Path
import numpy as np
from PIL import Image


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def generate(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    n = 512
    y, x = np.mgrid[0:n, 0:n].astype(np.float64)
    nx = (x + 0.5) / n * 2.0 - 1.0
    ny = 1.0 - (y + 0.5) / n * 2.0
    radius = np.sqrt(nx * nx + ny * ny)
    nz = np.sqrt(np.clip(1.0 - radius * radius, 0, 1))

    def blob(cx, cy, sx, sy=None, angle=0.0):
        sy = sx if sy is None else sy
        c, s = np.cos(angle), np.sin(angle)
        dx, dy = nx - cx, ny - cy
        u, v = (c * dx + s * dy) / sx, (-s * dx + c * dy) / sy
        return np.exp(-0.5 * (u * u + v * v))

    def save(name, rgb):
        # Extend the circle edge so linear sampling does not introduce black seams.
        scale = np.where(radius > 0.999, 0.999 / np.maximum(radius, 1e-6), 1.0)
        ex = np.clip((nx * scale + 1) / 2 * n - 0.5, 0, n - 1).astype(int)
        ey = np.clip((1 - ny * scale) / 2 * n - 0.5, 0, n - 1).astype(int)
        rgb = np.clip(rgb[ey, ex], 0, 1)
        rgb = np.where(rgb <= 0.0031308, rgb * 12.92,
                       1.055 * np.power(rgb, 1 / 2.4) - 0.055)
        Image.fromarray((np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)).save(output / name)

    g = 0.26 + 0.22 * smooth(-0.9, 0.9, ny) + 0.06 * nz
    g += 0.42 * blob(-0.36, 0.50, 0.26, 0.16, 0.5) + 0.22 * blob(0.55, 0.18, 0.08, 0.30)
    g -= 0.08 * blob(0, -0.10, 0.9, 0.10)
    g += 0.18 * smooth(0.80, 1.0, radius)
    save('Metal.png', np.stack([g * 0.97, g * 0.98, g * 1.04], -1))

    s = 0.55 * blob(-0.32, 0.42, 0.42, 0.30, 0.5) ** 1.5 + 0.18 * smooth(0.8, 1, radius)
    save('Sheen.png', np.stack([s, s, s * 1.03], -1))

    gm = 0.10 * smooth(-1, 1, ny) + 0.85 * blob(-0.35, 0.45, 0.08)
    gm += 0.55 * blob(0.40, 0.30, 0.05) + 0.35 * blob(0.10, -0.45, 0.06)
    gm += 0.25 * smooth(0.85, 1.0, radius)
    save('Gem.png', np.stack([gm * 0.95, gm, gm * 1.08], -1))

    center = 0.40 + 0.12 * nx * nx
    band = (1 - smooth(0.035, 0.075, np.abs(ny - center))) * smooth(0.97, 0.55, np.abs(nx))
    h = 0.95 * band + 0.08 * blob(-0.25, 0.55, 0.30, 0.20)
    save('HairRing.png', np.stack([h * 0.99, h, h * 1.03], -1))

    dot = 1 - smooth(0.045, 0.075, np.sqrt((nx + 0.30) ** 2 + (ny - 0.36) ** 2))
    dot2 = 1 - smooth(0.020, 0.040, np.sqrt((nx - 0.28) ** 2 + (ny - 0.30) ** 2))
    e = dot + 0.6 * dot2 + 0.22 * blob(0.15, -0.45, 0.22, 0.10)
    save('Eye.png', np.stack([e, e, e * 1.04], -1))

    # Linear grayscale mask, UV V follows the hair strand.
    rng = np.random.default_rng(331)
    size = 2048
    col = np.zeros(size)
    offset = 0
    while offset < size:
        width = int(rng.integers(2, 8))
        col[offset:offset + width] = rng.choice([0, 0.15, 0.4, 0.7, 1], p=[0.3, 0.15, 0.2, 0.2, 0.15])
        offset += width
    col = np.convolve(col, np.ones(3) / 3, mode='same')
    v = np.linspace(0, 1, size)
    segments = np.zeros((size, size))
    for k in range(0, size, 4):
        phase, frequency = rng.random(3) * 6.28, rng.uniform(3, 9, 3)
        s = 0.5 + 0.5 * np.sin(v * frequency[0] * 6.28 + phase[0]) * np.sin(v * frequency[1] * 6.28 + phase[1])
        segments[:, k:k + 4] = smooth(0.35, 0.75, s)[:, None]
    mask = np.clip(col[None, :] * segments, 0, 1)
    Image.fromarray((mask * 255 + 0.5).astype(np.uint8)).save(output / 'HairStreak.png')
    return sorted(p.name for p in output.glob('*.png'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
        default=Path(__file__).resolve().parents[1] / 'blender/lida_angel_toon/assets')
    args = parser.parse_args()
    print('\n'.join(generate(args.output)))
