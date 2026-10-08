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
from skimage.morphology import convex_hull_image

AQUI = Path(__file__).resolve().parent
ARTE = Path(sys.argv[1]) if len(sys.argv) > 1 else AQUI.parent / 'arte'
POSES = ['frente', 'sentado_lado', 'acostado', 'dormido', 'colgado'] + [f'caminar_{i}' for i in range(1, 7)]
PELAJES = ['carey']


def colores_cascabel(a):
    """Rojo del collar y dorado del cascabel."""
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx = a[..., :3].max(2); mn = a[..., :3].min(2); sat = (mx - mn) / np.maximum(mx, 1)
    rojo = (r > 120) & (r > g * 1.6) & (r > b * 1.5) & (sat > .45)
    oro = (r > 150) & (g > 100) & (b < 150) & (sat > .3) & (r > b * 1.4)
    return rojo | oro


def redondos(a):
    """Partes redondas del accesorio (el cascabel): se rellenan con su forma completa, también el lado iluminado."""
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx = a[..., :3].max(2); mn = a[..., :3].min(2); sat = (mx - mn) / np.maximum(mx, 1)
    return (r > 150) & (g > 100) & (b < 150) & (sat > .3) & (r > b * 1.4)


def _hsv(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx = a[..., :3].max(2); mn = a[..., :3].min(2)
    return r, g, b, (mx - mn) / np.maximum(mx, 1), mx


def colores_usekh(a):
    """Oro y turquesa del collar egipcio."""
    r, g, b, sat, mx = _hsv(a)
    oro = (r > 150) & (g > 100) & (b < 150) & (sat > .3) & (r > b * 1.4)
    turquesa = (g > 110) & (b > 100) & (r < g * .8) & (sat > .3)
    azul = (b > 90) & (b > r * 1.5) & (sat > .4)
    return oro | turquesa | azul


def colores_luna(a):
    """Oro de la diadema y de la luna."""
    r, g, b, sat, mx = _hsv(a)
    return (r > 150) & (g > 100) & (b < 150) & (sat > .3) & (r > b * 1.4)


def colores_bufanda(a):
    """Azul rey de la bufanda."""
    r, g, b, sat, mx = _hsv(a)
    return (b > 80) & (b > r * 1.4) & (b > g * 1.1) & (sat > .35)


def colores_mono(a):
    """Negro del moño: oscuro y grueso (las líneas finas del dibujo no cuentan)."""
    oscuro = a[..., :3].mean(2) < 95
    return ndimage.binary_opening(oscuro, iterations=2)


# accesorio → (sus colores, si tiene partes redondas que rellenar, diferencia mínima con el gato sin accesorio)
COLORES = {
    'cascabel': (colores_cascabel, redondos, 70),
    'mono': (colores_mono, None, 150),
    'usekh': (colores_usekh, None, 70),
    'luna': (colores_luna, None, 70),
    'bufanda': (colores_bufanda, None, 70),
}


def cargar(f, size=None):
    im = Image.open(f).convert('RGBA')
    if size and im.size != size:
        im = im.resize(size, Image.LANCZOS)
    return np.array(im).astype(int)


def mascara(acc, base, colores, redondo=None, umbral=70):
    """Peso 0-1 de cada pixel del accesorio (1 = accesorio, bordes suaves de 1 pixel)."""
    d = np.abs(acc[..., :3] - base[..., :3]).sum(2)
    nucleo = colores(acc) & (d > umbral)
    lab, k = ndimage.label(nucleo)
    tam = ndimage.sum(nucleo, lab, range(1, k + 1))
    nucleo = np.isin(lab, [i + 1 for i, t in enumerate(tam) if t >= 8])
    # el contorno oscuro del accesorio, pegado a sus colores
    cerca = ndimage.binary_dilation(nucleo, iterations=3)
    m = nucleo | (cerca & (acc[..., :3].mean(2) < 110) & (d > 40))
    m = ndimage.binary_closing(m, iterations=2)
    # partes redondas (cascabel): su forma completa, aunque el lado iluminado sea casi blanco
    oro = redondo(acc) & (d > 40) if redondo else np.zeros_like(m)
    lab, k = ndimage.label(oro)
    for i in range(1, k + 1):
        comp = lab == i
        if comp.sum() < 10:
            continue
        casco = convex_hull_image(comp)
        m |= ndimage.binary_dilation(casco, iterations=1) & (d > 25)
    # rellenar huecos: los brillos blancos del cascabel y las líneas de adentro también son del accesorio
    m = ndimage.binary_fill_holes(m) & (acc[..., 3] > 0)
    lab, k = ndimage.label(m)
    tam = ndimage.sum(m, lab, range(1, k + 1))
    m = np.isin(lab, [i + 1 for i, t in enumerate(tam) if t >= 6])
    # borde suave: el pixel de la orilla se mezcla a la mitad
    borde = m & ~ndimage.binary_erosion(m)
    peso = m.astype(float)
    peso[borde] = .55
    return peso


def alinear(a, p, evitar):
    """Desplazamiento (dy, dx) que mejor encima las líneas del gato con accesorio sobre las del otro pelaje."""
    tinta = lambda x: (x[..., :3].mean(2) < 100) & (x[..., 3] > 0)
    ta, tp = tinta(a) & ~evitar, tinta(p)
    cero = (ta & tp).sum()
    mejor, dmejor = cero, (0, 0)
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            s = (np.roll(np.roll(ta, dy, 0), dx, 1) & tp).sum()
            if s > mejor:
                mejor, dmejor = s, (dy, dx)
    # solo se mueve si encaja claramente mejor (5% más de línea encimada)
    return dmejor if mejor > cero * 1.05 else (0, 0)


def generar(arte, man):
    hechos = []
    for pel in PELAJES:
        for acc, (colores, redondo, umbral) in COLORES.items():
            for pose in POSES:
                fa, fb, fp = arte / f'gato_{pose}_{acc}.png', arte / f'gato_{pose}.png', arte / f'gato_{pose}_{pel}.png'
                if not (fa.exists() and fb.exists() and fp.exists()):
                    continue
                a = cargar(fa); size = (a.shape[1], a.shape[0])
                peso = mascara(a, cargar(fb, size), colores, redondo, umbral)
                p = cargar(fp, size)
                dy, dx = alinear(a, p, ndimage.binary_dilation(peso > 0, iterations=4))
                if dy or dx: print(f'  {pose}: el accesorio se movió {dx}, {dy} px para encajar')
                a = np.roll(np.roll(a, dy, 0), dx, 1); peso = np.roll(np.roll(peso, dy, 0), dx, 1)
                fuera = p[..., 3] < 128          # donde el accesorio sobresale del cuerpo: va completo, sin mezclar con el vacío
                w = np.where(fuera, (peso > 0).astype(float), peso)[..., None]
                p[..., :3] = (p[..., :3] * (1 - w) + a[..., :3] * w).round()
                p[..., 3] = np.where(peso > 0, np.maximum(p[..., 3], a[..., 3]), p[..., 3])
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
