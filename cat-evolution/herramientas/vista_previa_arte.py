"""Vista previa del arte de Gemini: recortes sobre los colores del juego y el gato base
pintado de varios pelajes (solo el pelaje; ojos, rubor y orejas se quedan igual).

Uso: python vista_previa_arte.py [carpeta_recortes] [salida.png]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('G:/Mi unidad/videogame/arte/recortes')
SAL = Path(sys.argv[2]) if len(sys.argv) > 2 else REC / 'vista_previa.png'
PELAJES = [('blanco', '#f6f1e9'), ('naranja', '#f39a4a'), ('gris', '#9aa4b2'), ('crema', '#f1d9ab'), ('café', '#9c6b45'), ('negro', '#4a4452'), ('dorado', '#f2c14e'), ('cósmico', '#7a5cf0')]


def pintar(img, hexa):
    """Multiplica el color sobre el pelaje (zonas claras y poco saturadas)."""
    a = np.array(img.convert('RGBA')).astype(np.float32)
    rgb = a[..., :3]
    mx, mn = rgb.max(axis=2), rgb.min(axis=2)
    sat = (mx - mn) / np.maximum(mx, 1)
    pelaje = (mx > 140) & (sat < 0.28) & (a[..., 3] > 0)
    col = np.array([int(hexa[i:i + 2], 16) for i in (1, 3, 5)], np.float32)
    tinte = rgb * col / 255
    if col.mean() < 110:                      # pelajes oscuros: aclara un poco para que no se pierda el contorno
        tinte = tinte * 0.85 + col * 0.25
    rgb[pelaje] = tinte[pelaje]
    a[..., :3] = rgb
    return Image.fromarray(a.clip(0, 255).astype(np.uint8), 'RGBA')


def fila(imgs, alto, fondo, ancho_total):
    lienzo = Image.new('RGB', (ancho_total, alto + 40), fondo)
    x = 20
    paso = (ancho_total - 40) // max(1, len(imgs))
    for im in imgs:
        esc = min((paso - 16) / im.width, alto / im.height)
        p = im.resize((int(im.width * esc), int(im.height * esc)), Image.LANCZOS)
        lienzo.paste(p, (x + (paso - p.width) // 2, 20 + alto - p.height), p)
        x += paso
    return lienzo


def main():
    est = [Image.open(p) for p in sorted(REC.glob('estilo_*.png'))]
    gat = [Image.open(p) for p in sorted(REC.glob('gatos_*.png'))]
    W = 1600
    filas = []
    if est:
        filas.append(('Hoja de estilo, recortada (sobre el azul del juego)', fila(est, 220, (19, 27, 74), W)))
    if gat:
        filas.append(('Gatos proporcionados, recortados (sobre el piso de la Casa)', fila(gat, 240, (176, 122, 69), W)))
        base = gat[0]
        filas.append(('Mismo gato pintado de distintos pelajes', fila([pintar(base, h) for _, h in PELAJES], 200, (19, 27, 74), W)))
        if len(gat) > 1:
            filas.append(('Caminando, de distintos pelajes', fila([pintar(gat[1], h) for _, h in PELAJES[:6]], 170, (45, 53, 112), W)))
    alto = sum(f.height + 36 for _, f in filas)
    hoja = Image.new('RGB', (W, alto), (14, 20, 56))
    d = ImageDraw.Draw(hoja)
    y = 0
    for titulo, f in filas:
        d.text((20, y + 10), titulo, fill=(240, 230, 210))
        hoja.paste(f, (0, y + 32))
        y += f.height + 36
    hoja.save(SAL)
    print('vista previa:', SAL)


if __name__ == '__main__':
    main()
