"""Mapa de partes del gato (cabeza, cuerpo, cola, patas) para pintar pelajes con exactitud.

Cada parte se separa siguiendo las líneas del dibujo de Gemini (watershed sobre la tinta),
y los huecos de las líneas se cierran por su parte más angosta. El juego lee el mapa
y pinta cada parte completa, así el color se detiene justo en el contorno.

Uso: python partes_gato.py [carpeta_arte]   → escribe arte/partes_<imagen>.png y actualiza manifest.json
     python partes_gato.py --ver salida.png → además arma una hoja para revisar los mapas
"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage
from skimage.segmentation import watershed

AQUI = Path(__file__).resolve().parent
ARTE = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else AQUI.parent / 'arte'
CABEZA, CUERPO, COLA, PATA = 1, 2, 3, 4
NOMBRES = {CABEZA: 'cabeza', CUERPO: 'cuerpo', COLA: 'cola', PATA: 'pata'}

# Semillas por pose, en fracciones de la caja del pelaje (igual que en el juego): parte → [(x, y), ...]
# patas_bajo = a partir de esta altura, lo que quede del cuerpo cuenta como pata (patas sin línea que las separe)
POSES = {
    'gato_frente': dict(semillas={CABEZA: [(.5, .3)], CUERPO: [(.5, .66)], COLA: [(.06, .76)], PATA: [(.27, .9), (.81, .9), (.4, .93), (.6, .93)]}, patas_bajo=.83),
    # cortes = líneas que cierran huecos del dibujo donde dos partes se tocan sin contorno
    'gato_sentado_lado': dict(semillas={CABEZA: [(.76, .24)], CUERPO: [(.45, .6), (.05, .8)], COLA: [(.2, .95), (.45, .97)], PATA: [(.78, .85)]}, patas_bajo=None, cortes=[((.124, .85), (.035, .95))]),
    'gato_acostado': dict(semillas={CABEZA: [(.76, .3)], CUERPO: [(.35, .55)], COLA: [(.06, .78), (.25, .95)], PATA: [(.88, .85), (.6, .88)]}, patas_bajo=None),
    'gato_dormido': dict(semillas={CABEZA: [(.3, .55)], CUERPO: [(.72, .38)], COLA: [(.62, .84), (.9, .72)], PATA: [(.19, .93), (.39, .9)]}, patas_bajo=None),
    'gato_colgado': dict(semillas={CABEZA: [(.3, .14)], CUERPO: [(.55, .45)], COLA: [(.82, .88), (.86, .72)], PATA: [(.22, .42), (.5, .48), (.38, .92), (.66, .9)]}, patas_bajo=.78, sin_pintar=.18),
    **{f'gato_caminar_{i}': dict(semillas={CABEZA: [(.86, .27)], CUERPO: [(.5, .45)], COLA: [(.06, .08), (.12, .3)]}, patas_bajo=.66) for i in range(1, 7)},
}
ACCESORIOS = ['cascabel', 'mono', 'usekh', 'luna', 'bufanda']


def es_pelaje(a):
    mx = a[..., :3].max(2); mn = a[..., :3].min(2)
    return (a[..., 3] > 0) & (mx > 140) & ((mx - mn) / np.maximum(mx, 1) < .28)


def mapa(img, conf):
    """Devuelve el mapa de partes (mismo tamaño que img)."""
    a = np.array(img.convert('RGBA')).astype(int)
    h, w = a.shape[:2]
    pel = es_pelaje(a)
    if conf.get('sin_pintar'):
        pel[:int(conf['sin_pintar'] * h)] = False
    ys, xs = np.nonzero(pel)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    fw, fh = max(1, x1 - x0), max(1, y1 - y0)
    corte = np.zeros((h, w), bool)
    for (ua, va), (ub, vb) in conf.get('cortes', []):
        for t in np.linspace(0, 1, 400):
            cx, cy = int(x0 + (ua + (ub - ua) * t) * fw), int(y0 + (va + (vb - va) * t) * fh)
            corte[max(0, cy - 1):cy + 2, max(0, cx - 1):cx + 2] = True
    pel_orig = pel.copy()
    pel = pel & ~corte
    # tinta = qué tan oscuro (las líneas son crestas), distancia = qué tan adentro del pelaje (los cuellos angostos son crestas)
    lum = (.3 * a[..., 0] + .59 * a[..., 1] + .11 * a[..., 2]) / 255
    tinta = np.where(pel, 0, 1 - lum) * (a[..., 3] > 0)
    dist = ndimage.distance_transform_edt(pel)
    relieve = 30 * tinta - dist
    marcas = np.zeros((h, w), int)
    rad = max(2, int(min(fw, fh) * .015))
    for parte, puntos in conf['semillas'].items():
        for (u, v) in puntos:
            x, y = int(x0 + u * fw), int(y0 + v * fh)
            # la semilla va al pixel de pelaje más cercano
            yy, xx = np.ogrid[:h, :w]
            cerca = pel & ((xx - x) ** 2 + (yy - y) ** 2 <= (rad * 4) ** 2)
            if not cerca.any():
                d = ndimage.distance_transform_edt(~pel, return_indices=True)[1]
                y, x = d[0][y, x], d[1][y, x]
                cerca = pel & ((xx - x) ** 2 + (yy - y) ** 2 <= rad ** 2)
            marcas[cerca] = parte
    lab = watershed(relieve, marcas, mask=a[..., 3] > 0)
    # los pixeles del corte toman la parte de su vecino más cercano
    if corte.any():
        idx = ndimage.distance_transform_edt(~pel, return_indices=True)[1]
        lab = np.where(corte & pel_orig, lab[idx[0], idx[1]], lab)
        pel = pel_orig
    lab[~pel] = 0
    if conf.get('patas_bajo'):
        yy = (np.arange(h)[:, None] - y0) / fh
        lab[((lab == CUERPO) | (lab == CABEZA)) & (yy > conf['patas_bajo'])] = PATA
    return lab


def generar(arte, man):
    """Hace los mapas de partes de todas las poses que existan en arte/ y los agrega al manifiesto."""
    hechos = []
    for base, conf in POSES.items():
        for nombre in [base] + [f'{base}_{a}' for a in ACCESORIOS]:
            f = arte / f'{nombre}.png'
            if not f.exists():
                continue
            lab = mapa(Image.open(f), conf)
            out = f'partes_{nombre}.png'
            Image.fromarray((lab * 50).astype(np.uint8), 'L').save(arte / out, optimize=True)
            man['assets'][f'partes_{nombre}'] = {'file': out}
            hechos.append(nombre)
    return hechos


def main():
    man_p = ARTE / 'manifest.json'
    man = json.loads(man_p.read_text(encoding='utf-8'))
    hechos = generar(ARTE, man)
    man_p.write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{len(hechos)} mapas de partes')
    if '--ver' in sys.argv:
        salida = sys.argv[sys.argv.index('--ver') + 1]
        colores = np.array([[40, 40, 40], [240, 120, 120], [120, 160, 240], [250, 200, 60], [120, 210, 120]], np.uint8)
        ims = []
        for base in POSES:
            img = Image.open(ARTE / f'{base}.png').convert('RGBA')
            lab = np.array(Image.open(ARTE / f'partes_{base}.png')) // 50
            col = Image.fromarray(colores[lab])
            mezcla = Image.blend(col, img.convert('RGB'), .35)
            mezcla.thumbnail((300, 300)); ims.append(mezcla)
        W = 300 * 4 + 30; H = 300 * ((len(ims) + 3) // 4) + 30
        hoja = Image.new('RGB', (W, H), (255, 255, 255))
        for i, im in enumerate(ims):
            hoja.paste(im, ((i % 4) * 310, (i // 4) * 310))
        hoja.save(salida)


if __name__ == '__main__':
    main()
