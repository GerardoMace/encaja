"""Bloques de Pirámide recoloreados (aprobado por Gerardo, 9-oct-2026, opción B).

El lapislázuli (azul) y el basalto (gris) se perdían sobre el tablero azul marino, así que se sacan dos
versiones nuevas cambiando solo el tono; el dibujo de Gemini queda igual:
  bloque_lapislazuli.png -> bloque_jade.png      (verde)
  bloque_basalto.png     -> bloque_amatista.png  (morado)
Los originales no se tocan. procesar_arte.py lo llama solo; también se puede correr suelto:
  python recolor_bloques.py
"""
import colorsys
import json
from pathlib import Path

import numpy as np
from PIL import Image

ARTE = Path(__file__).resolve().parent.parent / 'arte'
# nuevo: (de, tono 0-1, saturación fija o None para conservarla, cuánto aclarar)
RECETAS = {
    'bloque_jade': ('bloque_lapislazuli', 0.36, None, 0.12),
    'bloque_amatista': ('bloque_basalto', 0.76, 0.55, 0.18),
}


def recolor(im, hue, sat, light):
    a = np.array(im.convert('RGBA')).astype(float) / 255
    rgb = a[..., :3]
    to_hls = np.vectorize(colorsys.rgb_to_hls)
    h, l, s = to_hls(rgb[..., 0], rgb[..., 1], rgb[..., 2])
    h = np.full_like(h, hue)
    l = np.clip(l + light, 0, 1)
    s = np.full_like(s, sat) if sat is not None else s
    s = np.where(l < .25 + light, s * .5, s)   # el contorno oscuro casi no se tiñe
    r, g, b = np.vectorize(colorsys.hls_to_rgb)(h, l, s)
    a[..., 0], a[..., 1], a[..., 2] = r, g, b
    return Image.fromarray((a * 255).round().astype('uint8'), 'RGBA')


def generar(destino, manifiesto):
    for nuevo, (base, hue, sat, light) in RECETAS.items():
        if not (destino / f'{base}.png').exists():
            continue
        out = recolor(Image.open(destino / f'{base}.png'), hue, sat, light)
        out.save(destino / f'{nuevo}.png', optimize=True)
        manifiesto['assets'][nuevo] = {'file': f'{nuevo}.png', 'w': out.width, 'h': out.height}
        print(f'{nuevo}.png ({out.width}×{out.height}) desde {base}.png')


def main():
    man_path = ARTE / 'manifest.json'
    man = json.loads(man_path.read_text(encoding='utf-8'))
    generar(ARTE, man)
    man_path.write_text(json.dumps(man, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
