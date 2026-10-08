"""Pasa un accesorio dibujado por Gemini al gato de otro pelaje dibujado por Gemini (por ejemplo, el collar al carey).

Compara el gato blanco con accesorio contra el gato blanco sin accesorio: lo que cambió (y tiene los colores
del accesorio) es el accesorio. Esos pixeles, con su contorno, se pegan sobre el gato del otro pelaje,
que salió de la misma hoja y está en el mismo lugar.

Uso: python accesorio_a_pelaje.py [carpeta_arte]  → escribe gato_<pose>_<pelaje>_<accesorio>.png y actualiza manifest.json
"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage

AQUI = Path(__file__).resolve().parent
ARTE = Path(sys.argv[1]) if len(sys.argv) > 1 else AQUI.parent / 'arte'
POSES = ['frente', 'sentado_lado', 'acostado', 'dormido', 'colgado'] + [f'caminar_{i}' for i in range(1, 7)]
PELAJES = ['carey']


def colores_cascabel(a):
    """Rojo del collar y dorado del cascabel."""
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx = a[..., :3].max(2); mn = a[..., :3].min(2); sat = (mx - mn) / np.maximum(mx, 1)
    rojo = (r > 120) & (r > g * 1.6) & (r > b * 1.5) & (sat > .45)
    oro = (r > 150) & (g > 100) & (b < 120) & (sat > .4) & (r > b * 1.6)
    return rojo | oro


# accesorio → función que reconoce sus colores (por ahora, la prueba con el collar de cascabel)
COLORES = {'cascabel': colores_cascabel}


def cargar(f, size=None):
    im = Image.open(f).convert('RGBA')
    if size and im.size != size:
        im = im.resize(size, Image.LANCZOS)
    return np.array(im).astype(int)


def mascara(acc, base, colores):
    d = np.abs(acc[..., :3] - base[..., :3]).sum(2)
    nucleo = colores(acc) & (d > 70)
    lab, k = ndimage.label(nucleo)
    tam = ndimage.sum(nucleo, lab, range(1, k + 1))
    nucleo = np.isin(lab, [i + 1 for i, t in enumerate(tam) if t >= 8])
    # el contorno oscuro del accesorio, pegado a sus colores
    cerca = ndimage.binary_dilation(nucleo, iterations=3)
    m = nucleo | (cerca & (acc[..., :3].mean(2) < 110) & (d > 40))
    m = ndimage.binary_closing(m, iterations=1) & (acc[..., 3] > 0)
    # fuera pixeles sueltos
    lab, k = ndimage.label(m)
    tam = ndimage.sum(m, lab, range(1, k + 1))
    return np.isin(lab, [i + 1 for i, t in enumerate(tam) if t >= 6])


def generar(arte, man):
    hechos = []
    for pel in PELAJES:
        for acc, colores in COLORES.items():
            for pose in POSES:
                fa, fb, fp = arte / f'gato_{pose}_{acc}.png', arte / f'gato_{pose}.png', arte / f'gato_{pose}_{pel}.png'
                if not (fa.exists() and fb.exists() and fp.exists()):
                    continue
                a = cargar(fa); size = (a.shape[1], a.shape[0])
                m = mascara(a, cargar(fb, size), colores)
                p = cargar(fp, size)
                p[m] = a[m]
                nombre = f'gato_{pose}_{pel}_{acc}'
                Image.fromarray(p.astype(np.uint8), 'RGBA').save(arte / f'{nombre}.png', optimize=True)
                man['assets'][nombre] = {'file': f'{nombre}.png', 'w': size[0], 'h': size[1]}
                hechos.append(nombre)
    return hechos


if __name__ == '__main__':
    mp = ARTE / 'manifest.json'
    man = json.loads(mp.read_text(encoding='utf-8'))
    h = generar(ARTE, man)
    mp.write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{len(h)} imágenes de pelaje con accesorio')
